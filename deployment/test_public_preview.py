from pathlib import Path
import json,re,http.server,threading,functools
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
html=(ROOT/'public'/'index.html').read_text()
pattern=r'<script id="sample" type="application/json">(.*?)</script>'
assert json.loads(re.search(pattern,html,re.S)[1])==[]
private_source=ROOT.parent/'prototype'/'index.html'
private=json.loads(re.search(pattern,private_source.read_text(),re.S)[1]) if private_source.exists() else []
private_emails={r['email'] for r in private if r['email']}
assert not any(email in html for email in private_emails)
assert 'israelmamann@gmail.com' not in html
config=json.loads((ROOT/'public'/'vercel.json').read_text())
headers={h['key']:h['value'] for h in config['headers'][0]['headers']}
class Handler(http.server.SimpleHTTPRequestHandler):
 def end_headers(self):
  for k,v in headers.items():self.send_header(k,v)
  super().end_headers()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT/'public')))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/index.html')
 page.get_by_role('heading',name='Enrollment pulse').wait_for()
 assert 'PUBLIC PROTOTYPE' in page.locator('.banner').first.inner_text()
 assert page.locator('#mode option[value=sample]').count()==0
 assert page.evaluate('sample.length')==0
 assert page.evaluate('model().now.length')==726
 page.locator('[data-page=managers]').click();page.locator('#renewal-employer-lives').wait_for()
 page.locator('[data-page=insights]').click();page.get_by_role('heading',name='Fun Facts',exact=True).wait_for()
 assert page.locator('[data-fact]').count()==4
 page.locator('#launch-tv').click();page.locator('#tv-fullscreen').uncheck();page.get_by_role('button',name='Start slideshow').click();assert page.locator('#tv-screen').is_visible();page.locator('#tv-exit').click()
 assert not errors,errors
 b.close()
print('PASS: no embedded private records or employee emails; public-preview branding, security headers, metrics, Fun Facts and slideshow work.')
