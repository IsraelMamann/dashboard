"""Create a public Pages commit without switching the working branch or staging private files."""
from pathlib import Path
import subprocess,sys,tempfile,os,json,re,base64
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
workspace='--workspace' in sys.argv

def git(*args,data=None,env=None):
 return subprocess.run(['git','-C',str(REPO),*args],input=data,text=True,check=True,stdout=subprocess.PIPE,env=env).stdout.strip()

def no_real_records(html):
 match=re.search(r'<script id="sample" type="application/json">(.*?)</script>',html,re.S)
 if not match or json.loads(match[1])!=[]:raise RuntimeError('Embedded employee data detected; refusing to publish.')
preview=(ROOT/'public'/'index.html').read_text();no_real_records(preview)
files={'.nojekyll':''}
if workspace:
 html=(ROOT/'workspace'/'index.html').read_text();no_real_records(html)
 config=(ROOT/'workspace'/'config.js').read_text()
 cfg=json.loads(re.search(r'Object.freeze\((\{.*\})\)',config,re.S)[1]);key=cfg['publishableKey']
 if not key.startswith('sb_publishable_'):
  try:claims=json.loads(base64.urlsafe_b64decode(key.split('.')[1]+'==='))
  except Exception:raise RuntimeError('Configure a public Supabase publishable/anon key first.')
  if claims.get('role')!='anon':raise RuntimeError('A privileged key must never be shipped to the browser.')
 files.update({'index.html':html,'cloud.js':(ROOT/'workspace'/'cloud.js').read_text(),'cloud.css':(ROOT/'workspace'/'cloud.css').read_text(),'config.js':config,'demo/index.html':preview.replace('<div class="controls">','<div class="controls"><a href="../">Team sign-in</a>',1)})
else:files['index.html']=preview
setup=ROOT/'setup'/'index.html'
if setup.exists():files['setup/index.html']=setup.read_text()
renewal_setup=ROOT/'renewal-setup'/'index.html'
if renewal_setup.exists():files['renewal-setup/index.html']=renewal_setup.read_text()
with tempfile.TemporaryDirectory(prefix='big-plan-publish-') as temp:
 env={**os.environ,'GIT_INDEX_FILE':str(Path(temp)/'release.index')}
 git('read-tree','--empty',env=env)
 for name,data in sorted(files.items()):
  sha=git('hash-object','-w','--stdin',data=data)
  git('update-index','--add','--cacheinfo',f'100644,{sha},{name}',env=env)
 tree=git('write-tree',env=env)
args=['-c','user.name=Codex','-c','user.email=codex@users.noreply.github.com','commit-tree',tree]
parent=subprocess.run(['git','-C',str(REPO),'rev-parse','--verify','refs/remotes/origin/gh-pages'],text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
if parent.returncode==0:args+=['-p',parent.stdout.strip()]
sha=git(*args,data=('Publish authenticated enrollment workspace' if workspace else 'Update fictional enrollment dashboard preview')+'\n')
(ROOT/'pages-commit.txt').write_text(sha+'\n')
assert git('ls-tree','-r','--name-only',sha).splitlines()==sorted(files)
print('Pages commit prepared:',sha)
print('Included files:',', '.join(sorted(files)))
print('Working branch and private prototype data unchanged.')
