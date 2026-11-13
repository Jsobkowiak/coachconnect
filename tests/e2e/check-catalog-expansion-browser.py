"""Read-only pagination, French search and original-media checks on PC and mobile."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.local/training-qa';OUT.mkdir(parents=True,exist_ok=True)
seed=json.loads((ROOT/'apps/exercise-catalog/src/exercise_catalog/data/catalogue-fr.json').read_text())
names={e['data']['name'] for e in seed['entries']}
with sync_playwright() as p:
 browser=p.chromium.launch()
 for mobile,width,height in [(False,1440,1000),(True,390,844)]:
  page=browser.new_page(viewport={'width':width,'height':height},is_mobile=mobile,has_touch=mobile)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://localhost:8081/#illustrations')
  expect(page.get_by_text(f'{len(names)} exercices · fiches en français',exact=True)).to_be_visible()
  if not mobile:
   seen=[]
   while True:
    seen.extend(page.locator('.exercise-card h3').all_text_contents())
    next_button=page.get_by_role('button',name='Suivant',exact=True)
    if next_button.is_disabled():break
    with page.expect_response(lambda r:'/api/catalog/exercises?' in r.url and r.status==200):next_button.click()
    expect(page.locator('.exercise-card h3').first).not_to_have_text(seen[-20] if len(seen)>=20 else seen[0])
   assert len(seen)==len(names) and set(seen)==names,(len(seen),len(names))
  for query,name in [('SkiErg','SkiErg en double poussée'),('Air bike','Vélo à air avec bras mobiles')]:
   page.get_by_label('Rechercher un exercice',exact=True).fill(query)
   card=page.locator('.exercise-card').filter(has=page.get_by_role('heading',name=name,exact=True))
   expect(card).to_have_count(1)
   card.get_by_role('button',name='Illustrations de '+name,exact=True).click()
   dialog=page.get_by_role('dialog',name=name,exact=True)
   expect(dialog).to_be_visible()
   expect(dialog.locator('.positions img')).to_have_js_property('complete',True)
   assert dialog.locator('.positions img').evaluate('e=>e.naturalWidth>0')
   expect(dialog.get_by_text('Illustration générée par IA',exact=False)).to_be_visible()
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.screenshot(path=str(OUT/(('expansion-mobile-' if mobile else 'expansion-pc-')+query.replace(' ','-')+'.png')))
   dialog.get_by_role('button',name='Fermer',exact=True).click()
  assert not errors,errors
  page.close()
 browser.close()
print(f'OK : {len(names)} exercices accessibles par pagination PC ; recherche française/alias et nouvelles illustrations SkiErg/Air Bike visibles sur PC et mobile.')
