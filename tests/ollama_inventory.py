"""Endpoint fixtures with real pinned registry identities, without model bytes."""
import hashlib
import json
from pathlib import Path
from fungen_operator import bootstrap as b


def inventory_model(name, context=32768, store=None):
    identity=json.loads((Path(b.__file__).with_name('resources')/'ollama-models.json').read_text())['models'][name.removesuffix('-256k')]
    doc=json.loads(identity['raw_manifest'])
    digest=identity['manifest_digest'].removeprefix('sha256:')
    if name.endswith('-256k'):
        # The real create path adds a num_ctx layer; its manifest has its own hash.
        params=b'{"num_ctx":262144}'
        doc['layers'].append({'mediaType':'application/vnd.ollama.image.params',
                              'digest':'sha256:'+hashlib.sha256(params).hexdigest(),'size':len(params)})
        raw=json.dumps(doc,separators=(',',':')).encode()
        digest=hashlib.sha256(raw).hexdigest()
        assert store is not None
        folder=Path(store)/'blobs';folder.mkdir(parents=True,exist_ok=True)
        (folder/('sha256-'+digest)).write_bytes(raw)
    row={'name':name,'model':name,'digest':digest,
         'size':doc['config']['size']+sum(layer['size'] for layer in doc['layers']),
         'context_length':context}
    show={'modelfile':'FROM /models/blobs/'+identity['model_layer']['digest'].replace(':','-')+'\n',
          'details':{'quantization_level':'Q8_0' if name.startswith('laguna-s-2.1:') or ':q8_0' in name else 'Q4_K_M'},
          'parameters':f'num_ctx {context}',
          'model_info':{'general.architecture':'laguna','laguna.context_length':262144},
          'capabilities':['completion','tools']}
    return row,show
