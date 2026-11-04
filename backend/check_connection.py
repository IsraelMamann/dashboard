from pathlib import Path
import json,re,urllib.request,urllib.error
s=(Path(__file__).resolve().parent.parent/'app'/'config.js').read_text()
c=json.loads(re.search(r'Object.freeze\((\{.*\})\)',s,re.S)[1])
def request(path,body=None):
 headers={'apikey':c['publishableKey'],'Content-Type':'application/json'}
 r=urllib.request.Request(c['supabaseUrl']+path,headers=headers,data=json.dumps(body).encode() if body is not None else None)
 try:
  with urllib.request.urlopen(r,timeout=25) as f:return f.status,json.load(f)
 except urllib.error.HTTPError as e:
  try:data=json.load(e)
  except:data={}
  return e.code,data
status,data=request('/auth/v1/settings');print('Auth API:',status)
if status==200:print('Email provider:',data.get('external',{}).get('email'),'automatic email confirmation:',data.get('mailer_autoconfirm'))
status,data=request('/rest/v1/rpc/dashboard_revision',{});print('Anonymous dashboard RPC:',status,'code:',data.get('code') if isinstance(data,dict) else None)
status,data=request('/rest/v1/report_snapshots?select=id&limit=1');print('Anonymous report table:',status,'code:',data.get('code') if isinstance(data,dict) else None)
