"""Exercise every Groups header, paired metrics, filter persistence and drilldowns."""
from pathlib import Path
import functools,http.server,threading,re
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]/'app'
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()

def values(table,button):
 index=button.evaluate('(b)=>b.closest("th").cellIndex');kind=button.get_attribute('data-sort-kind');result=[]
 for row in table.locator('tbody tr').all():
  cell=row.locator('td').nth(index)
  if kind=='name':value=cell.locator('b').inner_text()
  elif kind=='manager':value=cell.locator('.sub').inner_text()
  else:value=cell.inner_text().strip()
  if kind in ['enrolled','lives']:value=value.split('/')[kind=='lives'].strip() if '/' in value else value
  if not value or value=='—':value=None
  elif kind in ['number','enrolled','lives']:
   found=re.search(r'[-+]?\d+(?:\.\d+)?',value.replace(',',''));value=float(found[0]) if found else None
  result.append(value)
 return result

def check_all_headers(table):
 buttons=table.locator('thead button[data-group-sort]');assert buttons.count()>0
 assert table.locator('thead th').count()==table.locator('thead th:has(button[data-group-sort])').count()
 for button in buttons.all():
  for _ in range(2):
   button.click();direction=button.locator('xpath=..').get_attribute('aria-sort');assert direction in ['ascending','descending']
   observed=values(table,button);valid=[v for v in observed if v is not None]
   # Natural ordering of names such as Group 2 before Group 10.
   def natural(v):return [int(p) if p.isdigit() else p.casefold() for p in re.split(r'(\d+)',v)] if isinstance(v,str) else v
   expected=sorted(valid,key=natural,reverse=direction=='descending')+[None]*(len(observed)-len(valid))
   assert observed==expected,(button.get_attribute('data-sort-label'),direction,observed,expected)
   assert table.locator('thead th:not([aria-sort=none])').count()==1

with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1600,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/core.html')
 page.evaluate('''()=>{
 const row=(group,i,lives=1)=>({group,email:group+i+'@example.test',name:i%2?'Zara Example':'Amy Example',phone:i%2?'202-555-0199':'202-555-0100',status:'ENROLLED',lives,state:'NY',carrier:'Aetna',effective:'01/01/2026'});
 uploads.base=[...Array.from({length:2},(_,i)=>row('Alpha',i,10)),...Array.from({length:10},(_,i)=>row('Bravo',i)),row('Group 2',0,2),...Array.from({length:3},(_,i)=>row('Missing',i))];
 uploads.current=[row('Alpha',0),row('Alpha',20),row('Alpha',21),...Array.from({length:4},(_,i)=>row('Bravo',i)),row('Group 2',0,15),row('Group 10',0),row('Group 10',1)].map(r=>({...r,effective:'01/01/2027'}));
 parents={'Alpha':'Shared Parent','Group 2':'Shared Parent'};assignment={'Alpha':'Zoe','Group 2':'Amy','Bravo':'Maya','Group 10':'Alex'};mode='uploads';page='groups';filters={};accountView='parent';render();
 }''')
 table=page.locator('#app [data-group-sort-table=parent]');footer=table.locator('tfoot').inner_text();check_all_headers(table);assert table.locator('tfoot').inner_text()==footer
 page.locator('#account-view').select_option('child');table=page.locator('#app [data-group-sort-table=child]');footer=table.locator('tfoot').inner_text();check_all_headers(table);assert table.locator('tfoot').inner_text()==footer
 # Paired cells sort independently, numeric counts don't use formatted text order.
 table.locator('[data-group-sort=oldEmployees]').click();assert table.locator('tbody td:first-child b').all_inner_texts()==['Bravo','Alpha','Group 2','Group 10']
 table.locator('[data-group-sort=oldLives]').click();assert table.locator('tbody td:first-child b').all_inner_texts()==['Alpha','Bravo','Group 2','Group 10']
 # Sorting survives a filter rerender, view changes and not-started tab changes.
 page.locator('#group-search').fill('Group');assert table.locator('[data-group-sort=oldLives]').locator('xpath=..').get_attribute('aria-sort')=='descending'
 assert table.locator('tbody td:first-child b').all_inner_texts()==['Group 2','Group 10'];page.locator('#group-search').fill('')
 page.locator('[data-tab=missing]').click();assert table.locator('tbody td:first-child b').all_inner_texts()==['Missing'];check_all_headers(table)
 page.locator('[data-tab=active]').click();page.locator('#account-view').select_option('parent');table=page.locator('#app [data-group-sort-table=parent]')
 page.locator('[data-parent="Shared Parent"]').click();locations=page.locator('#modal [data-group-sort-table=locations]');footer=locations.locator('tfoot').inner_text();check_all_headers(locations);assert locations.locator('tfoot').inner_text()==footer
 locations.locator('[data-group="Alpha"]').click();page.locator('[data-detail="New enrollee"]').click();employees=page.locator('#modal [data-group-sort-table=employees]');assert employees.locator('tbody tr').count()==2;check_all_headers(employees)
 button=employees.locator('[data-group-sort=email]');button.focus();page.keyboard.press('Enter');assert button.evaluate('(b)=>document.activeElement===b');assert button.locator('xpath=..').get_attribute('aria-sort')=='ascending'
 page.locator('#back-parent').click();assert page.locator('#modal [data-group-sort-table=locations]').count()==1;page.locator('#close').click()
 page.set_viewport_size({'width':390,'height':844});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');page.locator('#account-view').select_option('child');page.locator('#app [data-group-sort=addedLives]').click()
 assert page.locator('#app [data-group-sort=addedLives]').locator('xpath=..').get_attribute('aria-sort')=='descending'
 page.set_viewport_size({'width':1600,'height':1100});page.screenshot(path='/tmp/groups-sorting.png',full_page=True)
 # No current report: missing values stay at bottom and sort controls still work.
 page.evaluate('uploads.current=null;render()');check_all_headers(page.locator('#app [data-group-sort-table=child]'))
 assert not errors,errors;b.close()
server.shutdown()
print('PASS all parent, employer, location and employee headers in both directions; separate employee/life metrics; numeric growth; missing values; filters; totals; keyboard; mobile; baseline-only mode.')
