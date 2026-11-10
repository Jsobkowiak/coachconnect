"""Macro targets: arithmetic, isolation, validation, version conflicts and PC/mobile persistence."""
import os,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from training_test_auth import authenticated_context
BASE=os.environ['TRAINING_URL'];assert ':18081' in BASE
with sync_playwright() as p:
 browser=p.chromium.launch();a=authenticated_context(browser,BASE,profile=True);page=a.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 token=a.request.get(BASE+'/api/auth/session').json()['csrfToken'];headers={'X-CSRF-TOKEN':token}
 assert a.request.get(BASE+'/api/nutrition/target').json() is None
 before=a.request.get(BASE+'/api/profile').json()
 body={'revision':0,'startDate':'2026-10-31','weightKg':85.6,'maintenanceKcal':2800,'deficitKcal':400,'proteinPerKg':2,'fatPerKg':0.8,'maintenanceSource':'estimated'}
 result=a.request.post(BASE+'/api/nutrition/target/preview',data=body,headers=headers);assert result.ok,result.text();result=result.json()
 assert (result['targetKcal'],result['proteinGrams'],result['fatGrams'],result['carbGrams'])==(2400,171,68,276)
 assert result['targetKcal']==4*result['proteinGrams']+9*result['fatGrams']+4*result['carbGrams']
 assert a.request.get(BASE+'/api/nutrition/target').json() is None
 for patch in [{'deficitKcal':1001},{'proteinPerKg':0},{'fatPerKg':0.1},{'maintenanceKcal':1500,'deficitKcal':500},{'maintenanceSource':'unknown'},{'weightKg':1}]:
  assert a.request.put(BASE+'/api/nutrition/target',data={**body,**patch},headers=headers).status==400
 assert a.request.put(BASE+'/api/nutrition/target',data=body,headers=headers).json()['revision']==1
 assert a.request.put(BASE+'/api/nutrition/target',data=body,headers=headers).status==409
 # Independent registered account sees no target, and cannot overwrite the first account using its revision.
 from training_test_auth import credentials
 other,unused=credentials(BASE);b=browser.new_context();s=b.request.get(BASE+'/api/auth/session').json();assert b.request.post(BASE+'/api/auth/register',data=other,headers={'X-CSRF-TOKEN':s['csrfToken']}).ok
 assert b.request.get(BASE+'/api/nutrition/target').json() is None
 bheaders={'X-CSRF-TOKEN':b.request.get(BASE+'/api/auth/session').json()['csrfToken']}
 assert b.request.put(BASE+'/api/profile',data={'revision':0,'data':before['profile']['data']},headers=bheaders).ok
 assert b.request.put(BASE+'/api/nutrition/target',data={**body,'revision':1},headers=bheaders).status==409
 assert b.request.put(BASE+'/api/nutrition/target',data={**body,'maintenanceKcal':3000},headers=bheaders).ok
 assert a.request.get(BASE+'/api/nutrition/target').json()['targetKcal']==2400
 assert browser.new_context().request.get(BASE+'/api/nutrition/target').status==401
 for width in [1440,390]:
  page.set_viewport_size({'width':width,'height':1000});page.goto(BASE+'/#nutrition');page.reload();panel=page.get_by_role('region',name='Objectif calories et macros');expect(panel.locator('.macro-values')).to_contain_text('2\u202f400')
  expect(panel.get_by_label('Poids utilisé (kg)',exact=True)).to_have_value('85.6');expect(panel.get_by_label('Maintien quotidien (kcal)',exact=True)).to_have_value('2800')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=f'.local/macros-qa/target-{width}.png',full_page=True)
 page.get_by_label('Déficit quotidien (kcal)',exact=True).fill('300');page.get_by_role('button',name='Calculer un aperçu',exact=True).click();expect(panel).to_contain_text('Aperçu · non enregistré')
 assert a.request.get(BASE+'/api/nutrition/target').json()['targetKcal']==2400
 dialogs=[];page.on('dialog',lambda d:(dialogs.append(d.message),d.dismiss()));page.get_by_role('button',name='Suivi',exact=True).click();assert dialogs
 page.get_by_role('button',name='Enregistrer mon objectif',exact=True).click();expect(panel).to_contain_text('Objectif enregistré sur ton compte.');page.reload();expect(page.locator('.macro-values')).to_contain_text('2\u202f500')
 assert a.request.get(BASE+'/api/profile').json()==before
 assert not errors,errors;browser.close()
print('OK : calcul des macros, aperçu sans écriture, compte isolé, conflit de version, brouillon protégé et persistance PC/mobile ; profil inchangé.')
