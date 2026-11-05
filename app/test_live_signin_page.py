import os
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'],proxy={'server':os.environ['HTTPS_PROXY']});page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('https://israelmamann.github.io/dashboard/?check=currency-spacing-v3',wait_until='networkidle',timeout=60000)
 page.locator('#cloud-login-form').wait_for(timeout=15000)
 assert not page.locator('main').is_visible()
 assert page.locator('#cloud-email').is_visible()
 assert page.evaluate('sample.length')==0
 assert page.evaluate('finiteField("$1,234.50")')==1234.5
 assert page.evaluate('finiteField("$ 1,234.50")')==1234.5
 assert page.evaluate('normalize({premium:"$ 800.00",ichra_allotted:"$ 600.00"}).erAllowance')==600
 assert page.evaluate('normalize({premium:"123.50",full_premium:"999",ichra_allotted:"500"}).fullPremium')==123.5
 assert page.evaluate('contributionBasis')=='allowance'
 assert page.evaluate('parentTable(model()).includes("2026 enrolled")')
 assert page.evaluate('parentTable(model()).includes("2027 enrolled")')
 assert page.evaluate('cloudConfig()!==null')
 assert page.evaluate('cloudRedirectURL()')=='https://israelmamann.github.io/dashboard/'
 assert not errors,errors
 print('PASS live HTTPS site renders the real verified-email login, uses the configured Supabase connection, hides private data before sign-in and embeds no real reports. Live cost parsing, requested source columns and year-by-year account headers verified. No verification email was sent.')
 b.close()
