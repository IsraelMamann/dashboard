from pathlib import Path
import http.server,threading,functools
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/index.html');page.locator('[data-filter=type]').select_option('New')
 assert 'cannot identify which groups were new in 2026' in page.locator('#app').inner_text()
 rows=page.locator('.annual-comparison tbody tr');assert rows.count()==2
 for row in rows.all():
  cells=row.locator('td').all_inner_texts();assert cells[1]=='Not available';assert cells[-2:] == ['—','—']
 assert 'Unavailable' in page.locator('#pace-comparison').inner_text()
 assert page.evaluate('paceStats(model()).baseline.available') is False
 assert page.evaluate('model().now.filter(r=>match(r,model())).length')==96
 page.locator('[data-page=insights]').click();assert page.locator('[data-fact=er]').get_by_text('Unavailable',exact=True).count()==1
 assert '2026 · new-group history unavailable' in page.locator('#plan-tier-panel').inner_text()
 page.locator('#launch-tv').click();page.locator('#tv-fullscreen').uncheck();page.locator('#tv-scope').select_option('filtered');page.get_by_role('button',name='Start slideshow').click()
 page.evaluate('tvIndex=1;tvPaint()');assert 'no year-over-year growth is calculated' in page.locator('#tv-content').inner_text()
 page.locator('#tv-exit').click();page.locator('[data-filter=type]').select_option('Renewal');page.locator('[data-page=overview]').click();assert page.locator('.annual-comparison tbody tr').first.locator('td').nth(1).inner_text()=='763'
 assert not errors,errors;print('PASS new-group history is unavailable, not zero; no invented year-over-year change; current new-group counts and renewal comparisons remain valid.');b.close()
