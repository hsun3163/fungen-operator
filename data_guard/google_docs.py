"""Small Google Docs adapter. API tests use recorded, invented documents only."""
import difflib
import json
import re
import subprocess
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

import masking as m


def utf16(text):
    return len(text.encode('utf-16-le')) // 2


def access_token(config):
    """Use the existing rclone account; no extra credential store or login flow."""
    remote = config.get('rclone_remote', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', remote):
        raise m.MaskError('google-configuration')
    try:
        # Rclone refreshes its token through its normal configuration path.
        subprocess.run(['rclone', 'about', remote + ':', '--json', '--retries', '1'],
                       capture_output=True, check=True, timeout=60)
        dump = subprocess.run(['rclone', 'config', 'dump'], capture_output=True, check=True, text=True, timeout=60)
        return json.loads(json.loads(dump.stdout)[remote]['token'])['access_token']
    except Exception:
        raise m.MaskError('google-authentication') from None


def api(config, method, document_id, *, params=None, body=None):
    """Private HTTP bodies and credentials stay in memory; errors have no body text."""
    if not re.fullmatch(r'[A-Za-z0-9_-]+', document_id):
        raise m.MaskError('google-document-id')
    url = 'https://docs.googleapis.com/v1/documents/' + quote(document_id, safe='')
    if method == 'POST':
        url += ':batchUpdate'
    if params:
        url += '?' + urlencode(params)
    payload = json.dumps(body).encode() if body is not None else None
    try:
        request = Request(url, data=payload, method=method, headers={
            'Authorization': 'Bearer ' + access_token(config), 'Content-Type': 'application/json'})
        with urlopen(request, timeout=60) as response:
            return json.load(response)
    except m.MaskError:
        raise
    except Exception:
        raise m.MaskError('google-request') from None


def tabs(document):
    result = []
    def visit(rows):
        for tab in rows:
            result.append((tab['tabProperties']['tabId'], tab['documentTab']))
            visit(tab.get('childTabs', []))
    visit(document.get('tabs', []))
    return result or [(None, document)]


def selected_tab(document, source):
    available = tabs(document)
    requested = source.get('tab')
    if requested is None and len(available) != 1:
        raise m.MaskError('select-google-tab')
    for identifier, tab in available:
        if requested is None or identifier == requested:
            return identifier, tab
    raise m.MaskError('unknown-google-tab')


def read_document(source, config):
    document = api(config, 'GET', source['id'], params={
        'includeTabsContent': 'true', 'suggestionsViewMode': 'SUGGESTIONS_INLINE'})
    if not document.get('revisionId'):
        raise m.MaskError('missing-google-revision')
    selected_tab(document, source)
    return document, document['revisionId']


def paragraphs(document, source):
    tab_id, tab = selected_tab(document, source)
    result = []
    for element in tab.get('body', {}).get('content', []):
        if 'sectionBreak' in element:
            continue
        if 'paragraph' not in element:
            # Preserve complex topology by refusing a lossy export.
            raise m.MaskError('unsupported-google-structure', element.get('startIndex', 0))
        paragraph = element['paragraph']
        heading_name = paragraph.get('paragraphStyle', {}).get('namedStyleType', 'NORMAL_TEXT')
        heading = int(heading_name[-1]) if re.fullmatch(r'HEADING_[1-6]', heading_name) else (1 if heading_name in ('TITLE', 'SUBTITLE') else 0)
        runs = []
        guarded = bool(paragraph.get('suggestedParagraphStyleChanges') or paragraph.get('suggestedBulletChanges'))
        for part in paragraph.get('elements', []):
            text_run = part.get('textRun')
            if text_run is None:
                # A visible object marker preserves the place of a citation/field.
                # Import leaves this paragraph alone unless its text is edited.
                runs.append({'text': '\ufffc'})
                guarded = True
                continue
            style = text_run.get('textStyle', {})
            run = {'text': text_run.get('content', '')}
            for name in ('bold', 'italic'):
                if style.get(name):
                    run[name] = True
            baseline = style.get('baselineOffset')
            if baseline == 'SUPERSCRIPT':
                run['superscript'] = True
            elif baseline == 'SUBSCRIPT':
                run['subscript'] = True
            if style.get('link', {}).get('url'):
                run['link'] = style['link']['url']
            runs.append(run)
            guarded |= any(text_run.get(name) for name in ('suggestedInsertionIds', 'suggestedDeletionIds', 'suggestedTextStyleChanges'))
        items = m.chars(runs)
        if items and items[-1][0] == '\n':
            items.pop()
        runs = m.runs_from_chars(items)
        if not m.plain(runs):
            # Unchanged blank paragraphs remain in Google; edits use original indexes.
            continue
        result.append({'start': element['startIndex'], 'end': element['endIndex'],
                       'runs': runs, 'heading': heading, 'guarded': guarded,
                       'heading_name': heading_name, 'bullet': bool(paragraph.get('bullet')), 'tab': tab_id})
    return result


def export_document(dictionary, document, live, source):
    blocks = paragraphs(live, source)
    for block in blocks:
        m.mask_runs(dictionary, document, block['runs'], bool(block['heading']))
    output = []
    for block in blocks:
        runs = m.mask_runs(dictionary, document, block['runs'], bool(block['heading']))
        prefix = '#'*block['heading'] + ' ' if block['heading'] else '- ' if block['bullet'] else ''
        output.append(prefix + m.render_runs(runs))
    return '\n\n'.join(output) + '\n'


def desired_paragraphs(markdown):
    result = []
    for block in m.markdown_blocks(markdown):
        if block['literal']:
            if block['raw'].strip():
                raise m.MaskError('unsupported-google-markup', block['position'])
            continue
        prefix = block['prefixes'][0]
        bullet = bool(re.fullmatch(r'\s*[-+*] +', prefix))
        if prefix.strip() and not bullet and not block['heading']:
            raise m.MaskError('unsupported-google-markup', block['position'])
        result.append({'runs': block['runs'], 'heading': block['heading'], 'bullet': bullet})
    return result


def signature(block):
    # Normalize fragmentation from API text runs and Markdown style delimiters.
    return json.dumps([block['heading'], block['bullet'], m.runs_from_chars(m.chars(block['runs']))], sort_keys=True)


def range_for(start, end, tab):
    return {'startIndex': start, 'endIndex': end, **({'tabId': tab} if tab else {})}


def styled_insert(blocks, start, tab, final):
    requests, text, cursor = [], '', start
    for i, block in enumerate(blocks):
        value = m.plain(block['runs'])
        if '\n' in value:
            raise m.MaskError('paragraph-linebreak', start)
        text += value
        paragraph_end = cursor + utf16(value)
        if value:
            requests.append({'updateParagraphStyle': {
                'range': range_for(cursor, paragraph_end, tab),
                'paragraphStyle': {'namedStyleType': 'HEADING_' + str(block['heading']) if block['heading'] else 'NORMAL_TEXT'},
                'fields': 'namedStyleType'}})
            requests.append({'deleteParagraphBullets': {'range': range_for(cursor, paragraph_end, tab)}})
            if block['bullet']:
                requests.append({'createParagraphBullets': {'range': range_for(cursor, paragraph_end, tab), 'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'}})
        for run in block['runs']:
            length = utf16(run['text'])
            if not length:
                continue
            style = {'bold': bool(run.get('bold')), 'italic': bool(run.get('italic')),
                     'baselineOffset': 'SUPERSCRIPT' if run.get('superscript') else 'SUBSCRIPT' if run.get('subscript') else 'NONE'}
            if run.get('link'):
                style['link'] = {'url': run['link']}
            requests.append({'updateTextStyle': {'range': range_for(cursor, cursor + length, tab),
                                                 'textStyle': style, 'fields': 'bold,italic,baselineOffset,link'}})
            cursor += length
        if i < len(blocks)-1 or not final:
            text += '\n'
            cursor += 1
    return text, requests


def update_requests(live, markdown, source):
    old, new = paragraphs(live, source), desired_paragraphs(markdown)
    tab_id, tab = selected_tab(live, source)
    body_end = max((e.get('endIndex', 1) for e in tab.get('body', {}).get('content', [])), default=2)
    matcher = difflib.SequenceMatcher(a=[signature(b) for b in old], b=[signature(b) for b in new], autojunk=False)
    requests = []
    for tag, a, b, c, d in reversed(matcher.get_opcodes()):
        if tag == 'equal':
            continue
        if any(block['guarded'] for block in old[a:b]):
            raise m.MaskError('changed-field-or-suggestion-paragraph', old[a]['start'])
        start = old[a]['start'] if a < len(old) else body_end - 1
        end = old[b-1]['end'] if a < b else start
        final = b == len(old)
        if b - a == 1 and d - c == 1:
            # Keep the existing paragraph boundary, so adjacent comments,
            # fields, suggestions and paragraph properties retain their anchors.
            end -= 1
            final = True
        if final:
            end = min(end, body_end - 1)  # Google requires its final newline.
        inserted, styles = styled_insert(new[c:d], start, tab_id, final)
        if a == len(old) and old and inserted:
            inserted = '\n' + inserted
            for request in styles:
                value = next(iter(request.values()))
                value['range']['startIndex'] += 1
                value['range']['endIndex'] += 1
        if end > start:
            requests.append({'deleteContentRange': {'range': range_for(start, end, tab_id)}})
        if inserted:
            requests.append({'insertText': {'location': {'index': start, **({'tabId': tab_id} if tab_id else {})}, 'text': inserted}})
            requests.extend(styles)
    return requests


def write_document(source, live, markdown, revision, config):
    if live['revisionId'] != revision:
        raise m.MaskError('source-revision-changed')
    requests = update_requests(live, markdown, source)
    if not requests:
        return revision
    response = api(config, 'POST', source['id'], body={
        'writeControl': {'requiredRevisionId': revision}, 'requests': requests})
    updated = response.get('writeControl', {}).get('requiredRevisionId')
    if not updated:
        raise m.MaskError('missing-google-revision')
    return updated


def readable_dictionary(dictionary):
    lines = ['Private manuscript dictionary', '']
    for identifier, entry in dictionary['entries'].items():
        lines.extend([identifier, 'Type: ' + entry['type'],
                      'Status: ' + entry.get('status', 'resolved'),
                      'Value: ' + (entry['value'] if entry['value'] is not None else '(pending)'),
                      'Formatting: ' + json.dumps(entry['runs'], ensure_ascii=False),
                      'Context: ' + entry['context'],
                      'Documents: ' + ', '.join(entry['documents'])])
        if entry['value'] is None:
            lines.append('Description: ' + entry['description'])
        lines.append('')
    for name, record in dictionary['documents'].items():
        lines.extend(['Document: ' + name, 'Source: ' + json.dumps(record['source'], ensure_ascii=False),
                      'Last export revision/hash: ' + record['revision'], ''])
    return '\n'.join(lines) + '\n'


def sync_dictionary(dictionary, config):
    identifier = config.get('dictionary_doc', '')
    if not identifier:
        raise m.MaskError('dictionary-doc-configuration')
    # Read layout/revision metadata only, never text or dictionary entries from Google.
    metadata = api(config, 'GET', identifier, params={
        'fields': 'documentId,revisionId,body(content(endIndex))'})
    revision = metadata.get('revisionId')
    if not revision:
        raise m.MaskError('missing-google-revision')
    end = max((p.get('endIndex', 1) for p in metadata.get('body', {}).get('content', [])), default=2) - 1
    requests = []
    if end > 1:
        requests.append({'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': end}}})
    requests.append({'insertText': {'location': {'index': 1}, 'text': readable_dictionary(dictionary).rstrip('\n')}})
    api(config, 'POST', identifier, body={'writeControl': {'requiredRevisionId': revision}, 'requests': requests})
