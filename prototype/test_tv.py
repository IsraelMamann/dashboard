from pathlib import Path
import http.server,threading,functools
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1920,'height':1080});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/index.html');page.clock.install();page.locator('#launch-tv').click()
 page.locator('#tv-fullscreen').uncheck()
 for box in page.locator('[name=slide]').all():box.uncheck()
 page.get_by_role('button',name='Start slideshow').click();assert page.locator('#tv-config-error').inner_text()=='Choose at least one slide.'
 for box in page.locator('[name=slide]').all():box.check()
 page.locator('#tv-speed').select_option('10');page.get_by_role('button',name='Start slideshow').click()
 assert page.locator('#tv-screen').is_visible();assert page.locator('.tv-counter').inner_text()==f'1 / {page.evaluate("tvTypes.length")}'
 for width,height in [(1920,1080),(1280,720)]:
  page.set_viewport_size({'width':width,'height':height})
  for i in range(page.evaluate('tvTypes.length')):
   page.evaluate(f'tvIndex={i};tvPaint()')
   assert page.locator('#tv-content h1').count()==1
   overflow=page.evaluate('(()=>{let e=document.querySelector("#tv-content");return {vertical:e.scrollHeight>e.clientHeight+2,horizontal:e.scrollWidth>e.clientWidth+2}})()')
   assert not overflow['vertical'] and not overflow['horizontal'],(width,height,i,overflow)
   assert '@example.com' not in page.locator('#tv-screen').inner_text()
 print('All selectable slides including Fun Facts, aggregate-only content, 1920×1080 and 1280×720 fit: passed')
 page.locator('#tv-pause').click();assert page.evaluate('tvPaused && tvTimer===null')
 old=page.evaluate('tvIndex');page.keyboard.press('ArrowRight');assert page.evaluate('tvIndex')==(old+1)%page.evaluate('tvTypes.length')
 page.keyboard.press('ArrowLeft');assert page.evaluate('tvIndex')==old
 page.keyboard.press('Space');assert not page.evaluate('tvPaused')
 page.clock.fast_forward(10001);assert page.evaluate('tvIndex')==(old+1)%page.evaluate('tvTypes.length')
 page.keyboard.press('Escape');assert page.locator('#tv-screen').is_hidden();assert page.evaluate('tvTimer===null && !tvActive')
 print('Autoplay, pause/play, keyboard navigation, Escape exit and timer cleanup: passed')
 page.evaluate('filters.manager="Alex Morgan";render()');page.locator('#launch-tv').click();page.get_by_role('button',name='Start slideshow').click();page.locator('#tv-next').click()
 assert '726' in page.locator('#tv-content').inner_text();assert page.evaluate('filters.manager')=='Alex Morgan'
 page.locator('#tv-exit').click();page.locator('#launch-tv').click();page.locator('#tv-scope').select_option('filtered');page.get_by_role('button',name='Start slideshow').click();page.locator('#tv-next').click()
 expected=page.evaluate('model().now.filter(r=>match(r,model())).length');assert str(expected) in page.locator('#tv-content').inner_text()
 page.locator('#tv-fullscreen-toggle').click();page.wait_for_function('document.fullscreenElement?.id === "tv-screen"');page.locator('#tv-fullscreen-toggle').click();page.wait_for_function('!document.fullscreenElement');assert page.evaluate('tvActive');page.locator('#tv-exit').click();print('Native fullscreen/windowed controls, whole-company default and optional filtered scope preserve dashboard filters: passed')
 # Exercise dated snapshot replacement using small complete CSVs.
 page.evaluate('filters={manager:"",type:"",state:"",carrier:"",search:""};page="admin";render()')
 csv='company_name,employee_email,enrollment_status,total_lives_on_plan,consent_granted_date\nTest,test@example.com,ENROLLED,2,11/04/2026 3:00:00 PM\n'
 def upload(day,name,data):
  page.locator('#snapshot-date').fill(day);page.locator('[data-upload=current]').set_input_files({'name':name,'mimeType':'text/csv','buffer':data.encode()})
 upload('2026-11-03','day1.csv',csv);upload('2026-11-04','day2.csv',csv+ 'Test,second@example.com,PAYMENT_READY,1,11/04/2026 4:00:00 PM\n')
 upload('2026-11-04','replacement.csv',csv)
 assert page.evaluate('history.length')==2
 assert page.evaluate('history[1].n')==1
 page.locator('#use-sample').click();page.locator('[data-page=overview]').click();assert '0 net change' in page.locator('#enrollment-momentum').inner_text()
 assert 'Nov 3, 2026' in page.locator('#enrollment-momentum').inner_text()
 print('Dated snapshot chart, complete-report counts and same-day replacement: passed')
 # Capture a clean fictional TV preview.
 page.reload();page.set_viewport_size({'width':1920,'height':1080});page.locator('#launch-tv').click();page.locator('#tv-fullscreen').uncheck();page.get_by_role('button',name='Start slideshow').click();page.evaluate('tvIndex=2;tvPaused=true;tvPaint();tvSchedule()')
 page.screenshot(path=str(root/'tv-preview.png'),animations='disabled')
 page.locator('#tv-exit').click();assert not errors,errors
 print('No browser errors: passed');b.close()
