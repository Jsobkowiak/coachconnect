"""Measurements workflow on desktop and mobile in a disposable QA database."""
import os,json,urllib.request
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from training_test_auth import authenticated_context
from playwright.sync_api import sync_playwright,expect
BASE=os.environ['MEASUREMENTS_TEST_URL'];assert ':18081' in BASE
OUT=Path('.local/measurements-qa');OUT.mkdir(parents=True,exist_ok=True)
today=datetime.now(ZoneInfo('Europe/Paris')).date()
with sync_playwright() as p:
 b=p.chromium.launch();pc_context=authenticated_context(b,BASE,profile=True,fixture=None,viewport={'width':1440,'height':1050});pc=pc_context.new_page();errors=[]
 pc.on('pageerror',lambda e:errors.append(str(e)));pc.goto(BASE+'/#profil')
 book=pc.get_by_role('region',name='Carnet de mensurations')
 expect(book.get_by_role('heading',name='Carnet de mensurations')).to_be_visible()
 book.get_by_role('button',name='Ajouter une mesure',exact=True).click()
 book.get_by_text('Bien prendre ses mesures',exact=True).click()
 expect(book.get_by_text('NHS England',exact=True)).to_be_visible()
 book.locator('.measurement-field').filter(has=pc.locator('#measure-waistCm')).locator('summary').click()
 expect(book.get_by_text('À mi-distance',exact=False)).to_be_visible()
 pc.locator('#measure-waistCm').fill('82.5');pc.locator('#measure-armLeftCm').fill('35')
 # Refusing a navigation preserves the form.
 pc.once('dialog',lambda d:d.dismiss());pc.get_by_role('button',name='Entraînement',exact=True).click()
 expect(pc.locator('#measure-waistCm')).to_have_value('82.5')
 pc.screenshot(path=str(OUT/'measurement-form-pc.png'),full_page=True)
 with pc.expect_response(lambda r:r.url.endswith('/profile/body-measurements') and r.request.method=='POST') as r:book.get_by_role('button',name='Enregistrer les mesures',exact=True).click()
 assert r.value.status==200,r.value.text()
 expect(book.get_by_role('status')).to_have_text('Mesures enregistrées.')
 pc.reload();book=pc.get_by_role('region',name='Carnet de mensurations')
 expect(book.locator('.measurement-history').get_by_text('82,5 cm',exact=True).first).to_be_visible()
 book.get_by_label('Suivre une mesure').select_option('waistCm');expect(book.locator('.measurement-progress strong')).to_have_text('82,5 cm')
 phone_context=authenticated_context(b,BASE,profile=True,fixture=None,viewport={'width':390,'height':844},is_mobile=True,has_touch=True);phone=phone_context.new_page();phone.on('pageerror',lambda e:errors.append(str(e)))
 phone.goto(BASE+'/#profil');book=phone.get_by_role('region',name='Carnet de mensurations')
 book.get_by_role('button',name='Ajouter une mesure',exact=True).click()
 book.get_by_label('Date de mesure',exact=True).fill(str(today-timedelta(days=7)))
 expect(book.locator('input[type=checkbox]')).to_be_disabled()
 phone.locator('#measure-hipsCm').fill('99.2')
 for width in [390,320]:
  phone.set_viewport_size({'width':width,'height':844})
  assert phone.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
 phone.screenshot(path=str(OUT/'measurement-form-mobile.png'),full_page=True)
 with phone.expect_response(lambda r:r.url.endswith('/profile/body-measurements') and r.request.method=='POST') as r:book.get_by_role('button',name='Enregistrer les mesures',exact=True).click()
 assert r.value.status==200,r.value.text()
 expect(book.locator('.measurement-history').get_by_text('99,2 cm',exact=True)).to_be_visible()
 # Today's weight can explicitly update the profile and the calorie baseline.
 book.get_by_role('button',name='Ajouter une mesure',exact=True).click()
 phone.locator('#measure-weightKg').fill('82.3');book.locator('input[type=checkbox]').check()
 with phone.expect_response(lambda r:r.url.endswith('/api/profile') and r.request.method=='GET') as r:book.get_by_role('button',name='Enregistrer les mesures',exact=True).click()
 assert r.value.json()['profile']['data']['weightKg']==82.3
 expect(phone.locator('.profile-metrics').get_by_text('82,3 kg',exact=True)).to_be_visible()
 phone.reload();expect(phone.locator('.profile-metrics').get_by_text('82,3 kg',exact=True)).to_be_visible()
 assert phone.evaluate('document.documentElement.scrollWidth<=innerWidth')
 phone.screenshot(path=str(OUT/'measurement-history-mobile.png'),full_page=True)
 assert not errors,errors
 b.close()
print('OK : guides, saisie partielle/datée, conservation après refus de navigation, historique persistant, suivi par zone, synchronisation et PC/mobile 320–1440px.')
