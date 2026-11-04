"""Deploy only deployment/public via Vercel's authenticated HTTPS API."""
from pathlib import Path
import json,os,sys,time,urllib.request,urllib.error,urllib.parse
ROOT=Path(__file__).resolve().parent
TOKEN=os.environ.get('VERCEL_TOKEN')
if not TOKEN:
 print('BLOCKED: Configure VERCEL_TOKEN securely in environment settings. No deployment attempted.');sys.exit(2)
team=os.environ.get('VERCEL_TEAM_ID','').strip()
query='?'+urllib.parse.urlencode({'teamId':team}) if team else ''
def request(path,payload=None):
 data=json.dumps(payload).encode() if payload is not None else None
 req=urllib.request.Request('https://api.vercel.com'+path+query,data=data,headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json'},method='POST' if payload is not None else 'GET')
 try:
  with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)
 except urllib.error.HTTPError as error:
  print('Vercel API request failed with HTTP '+str(error.code)+'. Check token permissions and project/team access in environment settings.');sys.exit(3)
 except urllib.error.URLError:
  print('Could not reach the Vercel API through the configured network.');sys.exit(4)
files=[]
for name in ['index.html','vercel.json']:
 path=ROOT/'public'/name
 if not path.is_file():print('Run deployment/prepare_preview.py first.');sys.exit(5)
 files.append({'file':name,'data':path.read_text(),'encoding':'utf-8'})
# Explicit files prevent private prototype data, attachments, archives, and tests from being deployed.
result=request('/v13/deployments',{'name':'the-big-plan-enrollment','target':'production','files':files,'projectSettings':{'framework':None,'buildCommand':None,'outputDirectory':None}})
identifier=result.get('id');url=result.get('url')
if not identifier or not url:print('The API did not return a deployment URL.');sys.exit(6)
(ROOT/'last-deployment.json').write_text(json.dumps({'id':identifier,'url':'https://'+url})+'\n')
print('Deployment created: https://'+url)
for _ in range(20):
 status=request('/v13/deployments/'+urllib.parse.quote(identifier,safe=''))
 state=status.get('readyState')
 if state=='READY':print('Ready: https://'+url);sys.exit(0)
 if state in ['ERROR','CANCELED']:print('Deployment '+state.lower()+'. Inspect the build in Vercel.');sys.exit(7)
 time.sleep(2)
print('Deployment is still building; readiness is not yet confirmed.')
