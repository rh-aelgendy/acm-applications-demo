"""Generate once inside Kubernetes. Do not rotate a database password on re-sync."""
import json,os,secrets,ssl,urllib.request,urllib.error
from pathlib import Path
root=Path('/var/run/secrets/kubernetes.io/serviceaccount');ns=(root/'namespace').read_text().strip();token=(root/'token').read_text().strip()
base='https://'+os.environ['KUBERNETES_SERVICE_HOST']+':'+os.environ.get('KUBERNETES_SERVICE_PORT_HTTPS','443')+'/api/v1/namespaces/'+ns+'/secrets'
ctx=ssl.create_default_context(cafile=str(root/'ca.crt'))
def call(url,data=None):
    req=urllib.request.Request(url,data=json.dumps(data).encode() if data else None,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    return urllib.request.urlopen(req,context=ctx,timeout=15)
try:
    with call(base+'/orders-db-credentials') as response:
        current=json.load(response)
        if current.get('metadata',{}).get('labels',{}).get('app.kubernetes.io/part-of')!='retail-orders' or not {'username','password','database'}<=set(current.get('data',{})):raise SystemExit('Existing credential Secret is not owned or is incomplete')
    print('Existing database credentials retained')
except urllib.error.HTTPError as e:
    if e.code!=404:raise SystemExit('Credential lookup failed')
    body={'apiVersion':'v1','kind':'Secret','metadata':{'name':'orders-db-credentials','labels':{'app.kubernetes.io/part-of':'retail-orders'}},'type':'Opaque','stringData':{'username':'orders','database':'orders','password':secrets.token_urlsafe(36)}}
    try:
        with call(base,body):pass
    except urllib.error.HTTPError:raise SystemExit('Credential creation failed; rerun sync to check existing state')
    print('Database credentials generated in cluster')
