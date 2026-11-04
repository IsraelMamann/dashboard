"""Build a public preview from the private prototype without shipping uploaded data."""
from pathlib import Path
import json,re,zipfile
ROOT=Path(__file__).resolve().parent
private_source=ROOT.parent/'prototype'/'index.html'
source=private_source if private_source.exists() else ROOT.parent/'app'/'core.html'
html=source.read_text()
pattern=r'(<script id="sample" type="application/json">)(.*?)(</script>)'
match=re.search(pattern,html,re.S)
if not match: raise RuntimeError('Expected sample data boundary is missing; refusing to build.')
html=html[:match.start(2)]+'[]'+html[match.end(2):]
html=html.replace('<option value="sample">Uploaded 2026 sample</option>','')
html=html.replace('<button id="use-sample">Use provided 2026 sample as baseline</button>','')
html=html.replace('Report uploads and edits stay in this browser session. No report is sent to a server.','Public preview uses fictional data. Local uploads and edits stay in your browser session; no report is sent to a server.')
html=html.replace('FICTIONAL DEMO · All people, assignments, and comparison figures in this mode are illustrative.','PUBLIC PROTOTYPE · Fictional data. Sign-in and roles are simulated. Reports are not shared or saved online.')
html=html.replace('<title>The Big Plan · Enrollment pulse</title>','<title>The Big Plan · Public dashboard preview</title>')
html=html.replace('Only the fields used by this dashboard are retained.','This public prototype processes uploads in this browser only; uploads do not create a shared company workspace. Only the fields used by this dashboard are retained.')
html=html.replace('israelmamann@gmail.com','owner@example.com')
(ROOT/'public').mkdir(parents=True,exist_ok=True)
(ROOT/'public'/'index.html').write_text(html)
(ROOT.parent/'app'/'core.html').write_text(html)
config={
 'buildCommand':None,'outputDirectory':'.',
 'headers':[{'source':'/(.*)','headers':[
  {'key':'X-Content-Type-Options','value':'nosniff'},
  {'key':'X-Frame-Options','value':'DENY'},
  {'key':'Referrer-Policy','value':'no-referrer'},
  {'key':'Cache-Control','value':'no-store'},
  {'key':'Content-Security-Policy','value':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"}
 ]}]
}
(ROOT/'public'/'vercel.json').write_text(json.dumps(config,indent=2)+'\n')
with zipfile.ZipFile(ROOT/'public-preview-deploy.zip','w',zipfile.ZIP_DEFLATED) as z:
 z.write(ROOT/'public'/'index.html','index.html');z.write(ROOT/'public'/'vercel.json','vercel.json')
assert re.search(pattern,html,re.S)[2]=='[]'
print('Public preview prepared with no embedded employee records.')
