"""Prepare the authenticated static frontend. Only public project settings may enter this build."""
from pathlib import Path
import re,shutil,json,hashlib
ROOT=Path(__file__).resolve().parent
APP=ROOT.parent/'app'
OUT=ROOT/'workspace'
OUT.mkdir(exist_ok=True)
html=(ROOT/'public'/'index.html').read_text()
assert re.search(r'<script id="sample" type="application/json">(.*?)</script>',html,re.S)[1]=='[]'
html=html.replace('<title>The Big Plan · Public dashboard preview</title>','<title>The Big Plan · Team enrollment workspace</title>')
icon=APP/'assets'/'favicon.ico'
icon_version=hashlib.sha256(icon.read_bytes()).hexdigest()[:12]
html=html.replace('</head>',f'<link rel="icon" type="image/x-icon" href="./favicon.ico?v={icon_version}"><link rel="stylesheet" href="./cloud.css"><script src="./config.js"></script></head>',1)
shutil.copyfile(icon,OUT/'favicon.ico')
html=html.replace('<body>','<body><section id="auth-gate"><div class="auth-box"><h1>Private workspace</h1><p>Connecting secure sign-in…</p><noscript>Enable JavaScript to sign in.</noscript></div></section>',1)
html=html.replace('</body>','<script src="./cloud.js"></script></body>',1)
html=html.replace('YOUR UPLOADS · Session-only report data; replacing the baseline recalculates all comparisons.','SHARED REPORTS · Verified workspace data. Replacing the baseline recalculates comparisons for the team.')
html=html.replace('Report uploads and edits stay in this browser session.','Reports and assignments are saved in the shared workspace.')
html=html.replace('Public preview uses fictional data. Local uploads and edits stay in your browser session; no report is sent to a server.','Private team workspace · verified email access · shared report storage · role-checked exports.')
html=html.replace('Prototype only · Role switch simulates permissions; authentication and invitations are not connected.','The Big Plan · Shared enrollment workspace.')
html=html.replace('Interactive prototype','Shared workspace')
html=html.replace('Switch the prototype role to Admin to explore these controls.','Only admins can manage reports, assignments, and access.')
html=html.replace('History is retained for this browser session.','History is saved in the shared workspace.').replace('Snapshot history is kept for this browser session.','Snapshot history is saved in the shared workspace.')
html=html.replace('This public prototype processes uploads in this browser only; uploads do not create a shared company workspace. ','')
for name in ['cloud.js','cloud.css','config.js']:
 asset=APP/name if (APP/name).exists() else APP/'config.example.js'
 version=hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
 html=html.replace('./'+name+'"','./'+name+'?v='+version+'"')
(OUT/'index.html').write_text(html)
for name in ['cloud.js','cloud.css']:shutil.copyfile(APP/name,OUT/name)
config=APP/'config.js'
shutil.copyfile(config if config.exists() else APP/'config.example.js',OUT/'config.js')
print('Authenticated frontend prepared. A live Supabase connection is still required before it can be used.')
