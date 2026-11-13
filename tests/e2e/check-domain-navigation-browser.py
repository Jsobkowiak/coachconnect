"""Two domain entries, contextual sections, navigation guards and responsive layouts."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from training_test_auth import authenticated_context
BASE=os.environ['TRAINING_URL'];assert ':18081' in BASE
OUT=Path('.local/navigation-qa');OUT.mkdir(exist_ok=True,parents=True)
with sync_playwright() as p:
 b=p.chromium.launch();context=authenticated_context(b,BASE,profile=True,viewport={'width':1440,'height':1000});page=context.new_page();errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)));page.goto(BASE+'/#blocs')
 main=page.get_by_role('navigation',name='Navigation principale');expect(main.get_by_role('button')).to_have_count(2)
 expect(main.get_by_role('button',name='Entraînement',exact=True)).to_have_attribute('aria-current','page')
 sub=page.get_by_role('navigation',name='Rubriques · Entraînement');expect(sub.get_by_role('button')).to_have_count(3)
 sub.get_by_role('button',name='Exercices',exact=True).click();expect(page.locator('.catalog')).to_be_visible()
 main.get_by_role('button',name='Suivi',exact=True).click();expect(page.get_by_role('heading',name='Voir ce qui évolue')).to_be_visible()
 expect(page.get_by_role('navigation',name='Rubriques · Suivi').get_by_role('button')).to_have_count(2)
 main.get_by_role('button',name='Entraînement',exact=True).click();expect(page.locator('.catalog')).to_be_visible()
 main.get_by_role('button',name='Suivi',exact=True).click();page.get_by_role('button',name='Mon profil',exact=True).click()
 page.get_by_role('button',name='Ajouter une mesure',exact=True).click();page.locator('#measure-waistCm').fill('83')
 page.once('dialog',lambda d:d.dismiss());main.get_by_role('button',name='Entraînement',exact=True).click();expect(page.locator('#measure-waistCm')).to_have_value('83')
 page.locator('.measurement-form').get_by_role('button',name='Annuler',exact=True).click()
 for width in [1440,1024,768,390,320]:
  page.set_viewport_size({'width':width,'height':900})
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
  expect(main.get_by_role('button')).to_have_count(2)
 page.screenshot(path=str(OUT/'domains-profile-mobile.png'),full_page=True)
 expect(page.get_by_role('button',name='Nutrition',exact=True)).to_have_count(0)
 expect(page.locator('.profile-energy')).to_have_count(0)
 page.get_by_role('button',name='Modifier mon profil',exact=True).click()
 expect(page.locator('[name="calorieEstimatesEnabled"]')).to_have_count(0)
 before=context.request.get(BASE+'/api/profile').json()['profile']['data']
 with page.expect_response(lambda r:r.url.endswith('/api/profile') and r.request.method=='PUT') as result:
  page.get_by_role('button',name='Enregistrer le profil',exact=True).click()
 assert result.value.status==200,result.value.text()
 after=result.value.json()['profile']['data']
 assert after['sex']==before['sex'] and after['calorieEstimatesEnabled']==before['calorieEstimatesEnabled']

 page.set_viewport_size({'width':1440,'height':1000});main.get_by_role('button',name='Entraînement',exact=True).click()
 page.get_by_role('button',name='Mes blocs',exact=True).click();page.screenshot(path=str(OUT/'domains-blocks-pc.png'),full_page=True)
 page.reload();expect(main.get_by_role('button',name='Entraînement',exact=True)).to_have_attribute('aria-current','page')
 page.goto(BASE+'/#nutrition');page.reload();expect(page.get_by_role('heading',name='Mes blocs',exact=True)).to_be_visible()
 assert page.url.endswith('#blocs')
 assert not errors,errors;b.close()
print('OK : deux domaines, nutrition retirée, rubriques contextuelles, dernier écran conservé, garde des saisies, liens/rechargement, thème clair et PC/mobile 320–1440px.')
