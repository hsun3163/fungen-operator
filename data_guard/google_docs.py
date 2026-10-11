"""Small Google Docs adapter. API tests use recorded, invented documents only."""
import difflib
import json
import re
import subprocess
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError

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
    return request(config, method, url, body)


def request(config, method, url, body=None):
    payload = json.dumps(body).encode() if body is not None else None
    try:
        request = Request(url, data=payload, method=method, headers={
            'Authorization': 'Bearer ' + access_token(config), 'Content-Type': 'application/json'})
        with urlopen(request, timeout=60) as response:
            return json.load(response)
    except m.MaskError:
        raise
    except HTTPError as error:
        # Only enumerated API reasons may reach the caller, never response text.
        reason = ''
        try:
            details = json.load(error).get('error', {}).get('details', [])
            allowed = {'SERVICE_DISABLED', 'ACCESS_TOKEN_SCOPE_INSUFFICIENT', 'RATE_LIMIT_EXCEEDED'}
            reason = next((d['reason'] for d in details if d.get('reason') in allowed), '')
        except Exception:
            pass
        raise m.MaskError('google-http-' + str(error.code) + ('-' + reason if reason else '')) from None
    except Exception:
        raise m.MaskError('google-request') from None


def drive_api(config, method, *, params=None, body=None):
    url = 'https://www.googleapis.com/drive/v3/files'
    if params:
        url += '?' + urlencode(params)
    return request(config, method, url, body)


def ensure_file(config, parent, name, mime, properties=None):
    """Create once; refuse ambiguous names and unrelated existing documents."""
    def escape(value):
        return value.replace('\\', '\\\\').replace("'", "\\'")
    result = drive_api(config, 'GET', params={
        'q': "trashed = false and '" + escape(parent) + "' in parents and name = '" + escape(name) + "'",
        'fields': 'nextPageToken,files(id,mimeType,appProperties)', 'pageSize': 100})
    rows = result.get('files', [])
    if len(rows) > 1 or result.get('nextPageToken'):
        raise m.MaskError('ambiguous-drive-name')
    if rows:
        row = rows[0]
        if row.get('mimeType') != mime or any(row.get('appProperties', {}).get(k) != v for k, v in (properties or {}).items()):
            raise m.MaskError('unrelated-drive-document')
    else:
        row = drive_api(config, 'POST', params={'fields': 'id', 'ignoreDefaultVisibility': 'true'}, body={
            'name': name, 'mimeType': mime, 'parents': [parent], **({'appProperties': properties} if properties else {})})
    identifier = row.get('id', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', identifier):
        raise m.MaskError('google-document-id')
    return identifier


def ensure_folder(config, path):
    parent = 'root'
    parts = path.split('/')
    if not all(part and part not in ('.', '..') for part in parts):
        raise m.MaskError('drive-folder-path')
    for part in parts:
        parent = ensure_file(config, parent, part, 'application/vnd.google-apps.folder')
    return parent


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
            if style.get('weightedFontFamily', {}).get('fontFamily') == 'Roboto Mono':
                run['code'] = True
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
            # A block comment may share its closing line with visible prose.
            visible = re.sub(r'<!--.*?-->', '', block['raw'], flags=re.S)
            if visible.strip():
                if visible == block['raw']:
                    raise m.MaskError('unsupported-google-markup', block['position'])
                result.extend(desired_paragraphs(visible))
            continue
        prefix = block['prefixes'][0]
        bullet = bool(re.fullmatch(r'\s*[-+*] +', prefix))
        if prefix.strip() and not bullet and not block['heading']:
            raise m.MaskError('unsupported-google-markup', block['position'])
        # Masking can escape comment delimiters into ordinary text runs. Filter
        # visible characters here as well as literal blocks, retaining their styles.
        items = m.chars(block['runs'])
        hidden = set()
        for match in re.finditer(r'<!--.*?-->', m.plain(block['runs']), flags=re.S):
            if not any(style.get('code') for _, style in items[match.start():match.end()]):
                hidden.update(range(match.start(), match.end()))
        runs = m.runs_from_chars([item for i, item in enumerate(items) if i not in hidden])
        if m.plain(runs).strip():
            result.append({'runs': runs, 'heading': block['heading'], 'bullet': bullet})
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
            if run.get('code'):
                style['weightedFontFamily'] = {'fontFamily': 'Roboto Mono'}
            requests.append({'updateTextStyle': {'range': range_for(cursor, cursor + length, tab),
                                                 'textStyle': style, 'fields': 'bold,italic,baselineOffset,link,weightedFontFamily'}})
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


def result_settings(path):
    """Results delivery uses its own settings, without a manuscript dictionary."""
    import tomllib
    from pathlib import Path
    try:
        config=tomllib.loads(Path(path).expanduser().read_text())['masking']
        return {key:config[key] for key in ('rclone_remote','results_folder','results_title') if key in config}
    except Exception:
        raise m.MaskError('google-configuration') from None


def send_result(policy, run, raw):
    """Best-effort one running results Doc, using Hao's existing rclone remote."""
    from datetime import datetime, timezone
    from pathlib import Path
    import fcntl, hashlib
    # The byte-exact private result already exists locally before this function.
    try:
        config_path = Path(policy.get('google_config', Path.home()/'sunh14/librarian_agent/codex/config.toml'))
        config = result_settings(config_path)
        folder = policy.get('google_folder', config.get('results_folder', 'Librarian/results'))
        title = policy.get('google_title', config.get('results_title','Librarian results'))
        # Serialize the same document; unrelated requests keep executing concurrently.
        lock = Path(policy.get('google_lock', config_path.parent.parent / 'results-google.lock'))
        with lock.open('a') as fd:
            fcntl.flock(fd,fcntl.LOCK_EX)
            parent=ensure_folder(config,folder)
            identifier=ensure_file(config,parent,title,'application/vnd.google-apps.document',{'librarianResults':'v1'})
            stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
            run_id=Path(run).name
            content=raw.decode('utf-8')
            if len(raw)>32768:
                # rclone handles upload and token refresh; the full table stays local.
                name=run_id+'.tsv'
                target=config['rclone_remote']+':'+folder+'/'+name
                subprocess.run(['rclone','copyto',str(Path(run)/'human.tsv'),target,'--retries','1'],check=True,capture_output=True,timeout=60)
                # Resolve an authenticated Drive URL without creating public permissions.
                files=drive_api(config,'GET',params={'q':"trashed = false and '"+parent+"' in parents and name = '"+name+"'",'fields':'nextPageToken,files(id)','pageSize':2})
                matches=files.get('files',[])
                if len(matches)!=1 or files.get('nextPageToken') or not re.fullmatch(r'[A-Za-z0-9_-]+',matches[0].get('id','')):
                    raise m.MaskError('google-large-table-link')
                link='https://drive.google.com/file/d/'+matches[0]['id']+'/view'
                content='Large table: '+link+'\nSHA256: '+hashlib.sha256(raw).hexdigest()+'\n'
            entry='\nLibrarian result '+stamp+' '+run_id+'\n'+content
            metadata=api(config,'GET',identifier,params={'fields':'documentId,revisionId,body(content(endIndex))'})
            end=max((e.get('endIndex',1) for e in metadata.get('body',{}).get('content',[])),default=2)-1
            api(config,'POST',identifier,body={'writeControl':{'requiredRevisionId':metadata['revisionId']},
                'requests':[{'insertText':{'location':{'index':max(1,end)},'text':entry}}]})
            # Verify the request ID marker without copying document contents into any hosted receipt.
            live=api(config,'GET',identifier)
            text=''.join(e.get('textRun',{}).get('content','') for p in live.get('body',{}).get('content',[]) for e in p.get('paragraph',{}).get('elements',[]))
            if run_id not in text: raise m.MaskError('google-send-verification')
            return dict(status='sent',document='https://docs.google.com/document/d/'+identifier+'/edit')
    except m.MaskError as error:
        return dict(status='local-retained',reason=str(error).split(' at position ')[0])
    except Exception as error:
        return dict(status='local-retained',reason='google-send-'+type(error).__name__)
