"""Progress report cohort/date math, scoped opportunities, permissions and PDF rendering."""
from pathlib import Path
import functools,http.server,threading,json
import fitz
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]/'app'
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)));threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/core.html')
 page.evaluate('''()=>{
 const row=(group,email,lives,consent,status='ENROLLED')=>({group,email,name:'PRIVATE EMPLOYEE',phone:'PRIVATE PHONE',lives,consent,status,carrier:'Aetna',state:'NY',effective:'01/01/2026'});
 uploads.base=[row('Employer A','a@example.test',2,''),row('Employer A','deleteb@example.test',3,''),row('Employer A','c@example.test',1,''),row('Employer B','d@example.test',4,''),row('Employer B','e@example.test',2,''),row('Not Started','f@example.test',3,''),row('Leaving','g@example.test',9,''),{...row('Employer A','terminated@example.test',8,'','TERMINATED'),termination:'08/01/2026'}];
 uploads.current=[row('Employer A','a@example.test',2,'11/10/2026','APPLICATION_READY'),row('Employer A','new@example.test',5,'2026-11-16T15:00:00Z','STUCK'),row('Employer A','outside@example.test',1,'11/09/2026'),row('Employer B','d@example.test',4,'11/17/2026'),row('Employer B','invalid@example.test',2,'02/30/2026'),row('New Group','b@example.test',3,'11/12/2026','PAYMENT_READY'),row('Leaving','g@example.test',9,'11/13/2026'),row('Employer A','ignored@example.test',10,'11/12/2026','TERMINATED')].map(r=>({...r,effective:'01/01/2027'}));
 assignment={'Employer A':'Jordan','Employer B':'Taylor','Not Started':'Jordan','New Group':'Taylor','Leaving':'Jordan'};parents={'Employer A':'Parent Account'};nonRenewals={'Leaving':true};mode='uploads';role='Admin';filters={manager:'WRONG FILTER',state:'TX',type:'New'};progressPrefs={start:'2026-11-10',end:'2026-11-16',manager:''};page='reports';render();
 }''')
 report=page.evaluate('progressReportData(model())');assert report['totals']=={'employees':4,'lives':19,'groups':3,'renewalEmployees':3,'renewalLives':16,'newEmployees':1,'newLives':3,'missingDates':1},report
 assert report['coverage']=={'employees':7,'lives':26,'returned':3,'outstanding':3,'portfolio':6,'returnRate':'50.0%','notStarted':1,'renewalGroups':3},report['coverage']
 assert report['excluded']==1;assert report['growth']=={'deltaLives':2,'own':'16.7%','weighted':'16.67%','startingLives':12,'companyStartingLives':12,'groups':2}
 assert [r['group'] for r in report['opportunities']]==['Employer A','Employer B','Not Started'];assert [r['outstanding'] for r in report['opportunities']]==[1,1,1]
 assert 'PRIVATE' not in json.dumps(report) and '@example.test' not in json.dumps(report)
 assert page.locator('[data-progress-card]').count()==8;assert page.locator('[data-progress-card=period-employees] .num').inner_text()=='4'
 assert page.locator('[data-progress-card=season-employees] .num').inner_text()=='7';assert page.locator('#progress-opportunities tbody tr').count()==3
 # Both date boundaries included, invalid/future dates do not enter the selected period.
 same=page.evaluate("progressReportData(model(),{start:'2026-11-16',end:'2026-11-16',manager:''})");assert same['totals']['employees']==1 and same['totals']['lives']==5
 page.locator('#progress-manager').select_option('Jordan');report=page.evaluate('progressReportData(model())');assert report['totals']['employees']==3 and report['totals']['lives']==16;assert report['coverage']['outstanding']==2 and report['coverage']['returned']==2;assert report['growth']['weighted']=='16.67%' and report['growth']['own']=='33.3%';assert report['growth']['companyStartingLives']==12
 assert [r['group'] for r in report['opportunities']]==['Employer A','Not Started'];assert all(r['manager']=='Jordan' for r in report['opportunities'])
 # Range errors block download. Date defaults stay independent from same-date dashboard cutoffs.
 page.locator('#progress-start').fill('2026-11-18');page.locator('#progress-start').press('Tab');assert page.locator('#progress-export').is_disabled();assert 'start date must be' in page.locator('[role=alert]').inner_text()
 page.locator('#progress-start').fill('2026-11-10');page.locator('#progress-start').press('Tab');page.locator('#progress-end').fill('2099-01-01');page.locator('#progress-end').press('Tab');assert page.locator('#progress-export').is_disabled()
 page.locator('[data-progress-days="7"]').click();selection=page.evaluate('progressSelection()');assert selection['end']==page.evaluate('todayNY()');assert page.evaluate('paceStats(model()).cutoff')==selection['end'];assert selection['manager']=='Jordan'
 # Explicit export, standard PDF validation and full-resolution rendering.
 page.evaluate("progressPrefs={start:'2026-11-10',end:'2026-11-16',manager:'Jordan'};render()")
 with page.expect_download() as d:page.locator('#progress-export').click()
 d.value.save_as('/tmp/big-plan-manager-progress.pdf');assert d.value.suggested_filename=='big-plan-manager-jordan-2026-11-10-to-2026-11-16.pdf'
 doc=fitz.open('/tmp/big-plan-manager-progress.pdf');assert len(doc)==2
 for i,pdfpage in enumerate(doc):
  assert pdfpage.rect.width==612 and pdfpage.rect.height==792;assert len(pdfpage.get_images())==1;pix=pdfpage.get_pixmap(matrix=fitz.Matrix(1.7,1.7));pix.save('/tmp/progress-pdf-page-'+str(i+1)+'.png')
 assert Path('/tmp/big-plan-manager-progress.pdf').stat().st_size>50000
 # Missing reports are not presented as zero progress; viewer exports denied even via direct call.
 page.locator('#role').select_option('Viewer');assert page.locator('#progress-export').is_disabled();result=page.evaluate("downloadProgressReport().then(()=>null,e=>e.message)");assert 'requires account manager' in result
 page.locator('#role').select_option('Account manager');assert page.locator('#progress-export').is_enabled()
 page.evaluate("uploads.current=null;render()");assert page.locator('#progress-export').is_disabled();assert page.locator('#progress-preview').count()==0
 page.evaluate("mode='demo';progressPrefs={...progressRange(),manager:''};render()")
 # Long portfolios paginate, and all report content stays inside the page.
 page.evaluate('''()=>{const row=i=>({group:'Long Employer Account Name '+i+' LLC',email:'employee'+i+'@example.test',status:'ENROLLED',lives:2,state:'NY',effective:'01/01/2026'});uploads.base=Array.from({length:30},(_,i)=>row(i));uploads.current=[{...row(0),effective:'01/01/2027',consent:todayNY()}];mode='uploads';assignment={};parents={};nonRenewals={};progressPrefs={...progressRange(),manager:''};render()}''')
 assert page.locator('#progress-opportunities tbody tr').count()==10
 with page.expect_download() as d:page.locator('#progress-export').click()
 d.value.save_as('/tmp/big-plan-company-progress.pdf');doc=fitz.open('/tmp/big-plan-company-progress.pdf');assert len(doc)==3;doc[1].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save('/tmp/progress-pdf-top-ten.png');doc[2].get_pixmap().save('/tmp/progress-pdf-notes.png')
 page.screenshot(path='/tmp/progress-report-preview.png',full_page=True);page.set_viewport_size({'width':390,'height':844});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');assert page.locator('#progress-export').is_visible()
 assert not errors,errors;b.close()
server.shutdown()
print('PASS inclusive date ranges, actual consent dates, current statuses, transferred employees, excluded nonrenewals, manager scope, weighted renewal growth, missing dates/reports, role restrictions, true PDF downloads, pagination and mobile layout.')
