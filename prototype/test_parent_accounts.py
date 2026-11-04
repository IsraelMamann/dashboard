from pathlib import Path
import http.server,threading,functools,csv,io
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/index.html')
 page.evaluate('''()=>{
 const base=Array.from({length:27},(_,i)=>({group:i===0?'Recover Care, "Central"':'Recover Care Location '+String(i+1).padStart(2,'0'),email:'employee'+i+'@example.com',name:'Example '+i,phone:'202-555-0100',status:'ENROLLED',lives:2,state:'NY',carrier:'Aetna',effective:'01/01/2026',termination:'',consent:'11/01/2025 1:00:00 PM'}));
 uploads.base=base;uploads.current=base.slice(0,20).map(r=>({...r,effective:'01/01/2027',consent:'11/01/2026 1:00:00 PM'}));uploads.current.push({...uploads.current[0],email:'new@example.com',name:'New Employee',lives:5});
 assignment={};parents={};mode='uploads';page='admin';filters={manager:'',type:'',state:'',carrier:'',search:''};render();
 }''')
 with page.expect_download() as d:page.locator('#download-assignments').click()
 d.value.save_as('/tmp/account-template.csv');rows=list(csv.DictReader(open('/tmp/account-template.csv',newline='')))
 assert len(rows)==27
 assert list(rows[0])==['employer_account','account_manager','parent_account']
 assert any(r['employer_account']=='Recover Care, "Central"' for r in rows)
 for r in rows:r['account_manager']='Israel';r['parent_account']='Recover Care'
 out=io.StringIO();w=csv.DictWriter(out,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 page.locator('#upload-assignments').set_input_files({'name':'completed.csv','mimeType':'text/csv','buffer':out.getvalue().encode()})
 page.get_by_text('Imported 27 employer assignments',exact=False).wait_for()
 assert page.evaluate('Object.values(parents).filter(x=>x==="Recover Care").length')==27
 assert page.evaluate('Object.values(assignment).filter(x=>x==="Israel").length')==27
 print('Baseline employer template download, quoted employer names, manager/parent CSV import: passed')
 page.locator('[data-page=groups]').click();page.locator('[data-parent="Recover Care"]').wait_for()
 assert page.locator('#app tbody tr').count()==1
 assert '27 locations' in page.locator('[data-parent="Recover Care"]').inner_text()
 assert page.locator('[data-parent="Recover Care"] td').all_inner_texts()[2:6]==['20','40','21','45']
 assert page.evaluate('parentRollups(model())[0].cur.length')==21
 assert page.evaluate('lives(parentRollups(model())[0].cur)')==45
 assert page.evaluate('managerStats(model()).denominator')==40
 page.locator('[data-parent="Recover Care"]').click()
 assert page.locator('.dialog tbody tr').count()==27
 assert '20 / 27' in page.locator('.dialog').inner_text()
 page.locator('.dialog [data-group="Recover Care Location 27"]').click()
 assert page.locator('.dialog tbody tr').count()==1
 assert 'employee26@example.com' in page.locator('.dialog').inner_text()
 page.locator('#back-parent').click();assert page.locator('.dialog tbody tr').count()==27
 page.locator('#close').click();page.locator('#account-view').select_option('child');assert page.locator('#app tbody tr').count()==20
 page.locator('[data-tab=missing]').click();assert page.locator('#app tbody tr').count()==7
 print('27-location parent rollup, exact employee/life totals, parent → child → employee drill-down, back navigation and missing locations: passed')
 page.locator('[data-filter=parent]').select_option('Recover Care');assert page.evaluate('model().now.filter(r=>match(r,model())).length')==21
 page.locator('[data-page=admin]').click();bad='employer_account,account_manager,parent_account\nUnknown employer,Wrong Manager,Wrong Parent\n'
 page.locator('#upload-assignments').set_input_files({'name':'bad.csv','mimeType':'text/csv','buffer':bad.encode()})
 page.get_by_text('Unknown employer on row',exact=False).wait_for()
 assert page.evaluate('Object.values(assignment).every(x=>x==="Israel")')
 duplicate=out.getvalue()+out.getvalue().splitlines()[1]+'\n'
 page.locator('#upload-assignments').set_input_files({'name':'duplicates.csv','mimeType':'text/csv','buffer':duplicate.encode()})
 page.get_by_text('Duplicate employer on row',exact=False).wait_for()
 assert page.evaluate('Object.values(parents).every(x=>x==="Recover Care")')
 partial='employer_account,account_manager,parent_account\nRecover Care Location 27,New Manager,\n'
 page.locator('#upload-assignments').set_input_files({'name':'partial.csv','mimeType':'text/csv','buffer':partial.encode()})
 page.get_by_text('Imported 1 employer assignments',exact=False).wait_for()
 assert page.evaluate('assignment["Recover Care Location 27"]')=='New Manager'
 assert page.evaluate('parents["Recover Care Location 27"]')==''
 assert page.evaluate('parents["Recover Care Location 26"]')=='Recover Care'
 print('Unknown/duplicate row rejection is atomic; partial imports preserve other employers and allow clearing a parent: passed')
 page.locator('#role').select_option('Viewer');assert page.locator('#download-assignments').count()==0;assert page.locator('#upload-assignments').count()==0
 page.reload();page.locator('#mode').select_option('sample');page.locator('[data-page=admin]').click()
 assert page.evaluate('assignmentTemplate(model()).length')==465
 page.set_viewport_size({'width':390,'height':844});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 print('Admin-only template controls, all 465 sample employers and responsive assignment editor: passed')
 assert not errors,errors;b.close()
