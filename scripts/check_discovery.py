#!/usr/bin/env python3
"""Free discovery and local-vector checks. Never calls /v1/evaluate."""
import base64,hashlib,json,subprocess,sys,urllib.request,shutil,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='https://api.wheelerhubbellpublishing.com'
sys.path.insert(0,str(ROOT/'sdk/python'))
from standing_mark import StandingMark

def main():
    checks=[]
    for path in ['/health','/v1/contract','/.well-known/whp-standing.json','/.well-known/whp-issuer.json','/openapi.json']:
        with urllib.request.urlopen(BASE+path,timeout=30) as r:
            body=r.read();data=json.loads(body)
            assert r.status==200
        checks.append({'check':path,'status':'PASS','sha256':hashlib.sha256(body).hexdigest()})
    client=StandingMark();assert client.contract()['profile'].startswith('WHP-PHP-SERVICE-1.')
    _,kid=client.pinned_key();checks.append({'check':'Python SDK contract and key consistency','status':'PASS','kid':kid})
    test_key='MCowBQYDK2VwAyEA11qYAYKxCrfVS/7TyWQHOg7hcvPapiMlrwIaaPcHURo='
    for runtime,file in [(sys.executable,'verification/verify.py'),('node','verification/verify.js')]:
        if (runtime=='node' and not shutil.which('node')) or (runtime==sys.executable and importlib.util.find_spec('cryptography') is None):
            checks.append({'check':file,'status':'SKIP','reason':'Install Node.js 18+ or the Python cryptography package to run this optional independent signature check.'})
            continue
        r=subprocess.run([runtime,str(ROOT/file),str(ROOT/'verification/sample-test-key-envelope.json'),test_key],text=True,capture_output=True,check=True)
        assert 'VALID' in r.stdout
        checks.append({'check':file+' public test vector (not production)','status':'PASS'})
    messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list'},{'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'standing_contract','arguments':{}}}]
    r=subprocess.run([sys.executable,str(ROOT/'mcp/standing_mark_mcp.py')],input=''.join(json.dumps(m)+'\n' for m in messages),text=True,capture_output=True,check=True)
    out=[json.loads(line) for line in r.stdout.splitlines()];assert len(out)==3
    assert len(out[1]['result']['tools'])==4
    assert json.loads(out[2]['result']['content'][0]['text'])['profile'].startswith('WHP-PHP-SERVICE-1.')
    checks.append({'check':'MCP stdio initialize, tools/list, contract GET','status':'PASS'})
    print(json.dumps({'checks':checks,'examination_requests':0,'paid_examinations':0,'scope':'Live discovery GETs, local RFC test-key signatures and MCP stdio discovery only. No paid retry or adoption is established.'},indent=2))
if __name__=='__main__':main()
