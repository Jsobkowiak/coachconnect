"""Block-wide and per-week calorie settings, across desktop and mobile, in QA only."""
import os,json,re
from pathlib import Path
from training_test_auth import authenticated_context
from playwright.sync_api import sync_playwright,expect
BASE=os.environ['NUTRITION_TEST_URL'];assert ':18081' in BASE
OUT=Path(__file__).resolve().parent.parent/'.local/training-qa';OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch()
 pc_context=authenticated_context(browser,BASE,profile=False,fixture='.local/nutrition-qa/auth.json',viewport={'width':1440,'height':1050});pc=pc_context.new_page()
 errors=[];pc.on('pageerror',lambda e:errors.append(str(e)))
 pc.goto(BASE+'/#nutrition')
 expect(pc.get_by_role('heading',name='Adapter tes repères à ton programme')).to_be_visible()
 expect(pc.locator('.nutrition-weeks button')).to_have_count(12)
 expect(pc.get_by_text('12 séance(s) à préciser dans le bloc.',exact=False)).to_be_visible()
 before=pc.request.get(BASE+'/api/cycles').json()[0]
 profile=pc.request.get(BASE+'/api/profile').json()
 pc.screenshot(path=str(OUT/'nutrition-incomplete-pc.png'),full_page=True)
 wod=pc.locator('.nutrition-session-settings fieldset').filter(has=pc.locator('legend').filter(has_text='WOD à préciser'))
 expect(wod).to_have_count(1)
 wod.locator('select').select_option('circuit');wod.locator('input').fill('20')
 with pc.expect_response(lambda r:r.url.endswith('/nutrition') and r.request.method=='PUT') as response:pc.get_by_role('button',name='Enregistrer et recalculer',exact=True).click()
 result=response.value.json();assert response.value.status==200 and result['complete'],result
 expect(pc.get_by_text('Réglages enregistrés et besoins recalculés.',exact=True)).to_be_visible()
 assert all(w['days'][2]['sessions'][0]['durationMinutes']==20 for w in result['weeks'])
 pc.get_by_role('button',name=re.compile('Semaine 12')).click()
 expect(pc.locator('.nutrition-calendar h2')).to_have_text('Semaine 12')
 expect(pc.locator('.nutrition-days article')).to_have_count(7)
 pc.get_by_label('Appliquer les réglages à',exact=False).select_option('week')
 force=pc.locator('.nutrition-session-settings fieldset').filter(has=pc.locator('legend').filter(has_text='Force A'))
 force.locator('input').fill('15')
 with pc.expect_response(lambda r:r.url.endswith('/nutrition') and r.request.method=='PUT') as response:pc.get_by_role('button',name='Enregistrer et recalculer',exact=True).click()
 result=response.value.json();assert response.value.status==200,result
 assert result['weeks'][0]['days'][0]['sessions'][0]['durationMinutes']==60
 assert result['weeks'][11]['days'][0]['sessions'][0]['durationMinutes']==15
 pc.screenshot(path=str(OUT/'nutrition-complete-pc.png'),full_page=True)
 pc.reload();expect(pc.locator('.nutrition-weeks button')).to_have_count(12)
 expect(pc.get_by_text('12 séance(s) à préciser dans le bloc.',exact=False)).to_have_count(0)
 phone_context=authenticated_context(browser,BASE,profile=False,fixture='.local/nutrition-qa/auth.json',viewport={'width':390,'height':844},is_mobile=True,has_touch=True);phone=phone_context.new_page()
 phone.on('pageerror',lambda e:errors.append(str(e)));phone.goto(BASE+'/#nutrition')
 expect(phone.locator('.nutrition-weeks button')).to_have_count(12)
 phone.get_by_role('button',name=re.compile('Semaine 2(?: |$)')).click()
 expect(phone.locator('.nutrition-calendar h2')).to_have_text('Semaine 2 · allégée')
 assert phone.evaluate('document.documentElement.scrollWidth<=innerWidth')
 phone.screenshot(path=str(OUT/'nutrition-mobile.png'),full_page=True)
 phone.set_viewport_size({'width':320,'height':740});assert phone.evaluate('document.documentElement.scrollWidth<=innerWidth')
 ys=phone.locator('.main-navigation button').evaluate_all('a=>a.map(b=>b.getBoundingClientRect().y)');assert max(ys)-min(ys)<1
 phone.get_by_label('Activité hors entraînement',exact=False).select_option('moderate')
 phone.once('dialog',lambda d:d.dismiss());phone.get_by_role('button',name='Entraînement',exact=True).click()
 expect(phone.get_by_role('heading',name='Adapter tes repères à ton programme')).to_be_visible()
 assert pc.request.get(BASE+'/api/cycles/'+before['id']).json()==before
 assert pc.request.get(BASE+'/api/profile').json()==profile
 assert pc.request.get(BASE+'/api/workouts').json()==[]
 assert not errors,errors
 browser.close()
print('OK : bloc 12 semaines, séances identiques groupées, recalcul, réglages par semaine, persistance PC/mobile, protection des modifications et affichage 320–1440px ; aucune modification des programmes/perfs/profil.')
