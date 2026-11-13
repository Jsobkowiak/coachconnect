"""Read-only check of generated media on historical programme snapshots."""
import hashlib
import json
import re
from pathlib import Path
import urllib.request
from playwright.sync_api import sync_playwright, expect
BASE='http://localhost:8081'
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.local/training-qa'
OUT.mkdir(parents=True,exist_ok=True)
def fetch(path):
    with urllib.request.urlopen(BASE+'/api'+path,timeout=20) as response:
        return json.load(response)
expected_count=len(json.loads((ROOT/'apps/exercise-catalog/src/exercise_catalog/data/catalogue-fr.json').read_text())['entries'])
items=[]
while len(items)<expected_count:
    batch=fetch('/catalog/exercises?limit=100&offset='+str(len(items)))['items']
    assert batch,'Catalogue incomplet'
    items.extend(batch)
assert len(items)==expected_count
assert len({e['id'] for e in items})==expected_count
expected_media = {}
for exercise in items:
    media=exercise['media'];assert media['license']['ai_generated']
    filename=media['images'][0]['filename']
    assert media['source']=='coachconnect'
    expected_media[exercise['name']]=filename
    with urllib.request.urlopen(BASE+'/api/catalog/media/assets/'+filename) as response:
        payload=response.read();assert response.headers.get_content_type()=='image/png'
    assert hashlib.sha256(payload).hexdigest()==filename[:64]
coverage=fetch('/catalog/media-coverage');assert coverage['illustrated']==coverage['total']==expected_count
cycles=fetch('/cycles')
cycle=next(c for c in cycles if c['name']=='Cycle 1 — Pull / Push — 12 semaines')
before=json.dumps(cycle,sort_keys=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+'/#blocs')
    page.locator('.block-card').filter(has_text=cycle['name']).get_by_role('button',name='Ouvrir le bloc').click()
    for day,name,key in [('Mardi','Développé couché à la barre','bench'),('Mardi','Push press à la barre','push-press'),('Samedi','Pompes en pike','pike')]:
        page.locator('.session-tabs').get_by_role('button',name=re.compile(day)).click()
        button=page.get_by_role('button',name='Illustrations de '+name,exact=True)
        expect(button).to_be_visible()
        expect(button.locator('img')).to_have_attribute('src','/api/catalog/media/assets/'+expected_media[name])
        expect(button.locator('img')).to_have_js_property('complete',True)
        assert button.locator('img').evaluate('image=>image.naturalWidth>0')
        button.click()
        dialog=page.get_by_role('dialog',name=name,exact=True)
        expect(dialog).to_be_visible()
        expect(dialog.get_by_text('Illustration générée par IA',exact=False)).to_be_visible()
        assert dialog.locator('.positions img').bounding_box()['width']>500
        page.screenshot(path=str(OUT/('illustration-'+key+'-pc.png')))
        page.keyboard.press('Escape')
    phone=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    phone.on('pageerror',lambda e:errors.append(str(e)))
    phone.goto(BASE+'/#seance')
    phone.locator('.workout-picker select').nth(0).select_option(cycle['id'])
    phone.locator('.workout-picker select').nth(2).select_option(label='Mardi — Push · pecs / épaules / triceps')
    phone.get_by_role('button',name='Commencer la séance',exact=True).click()
    mobile_image=phone.get_by_role('button',name='Illustrations de Développé couché à la barre',exact=True)
    expect(mobile_image.locator('img')).to_have_attribute('src','/api/catalog/media/assets/'+expected_media['Développé couché à la barre'])
    mobile_image.click()
    expect(phone.get_by_role('dialog',name='Développé couché à la barre',exact=True)).to_be_visible()
    assert phone.evaluate('document.documentElement.scrollWidth<=innerWidth')
    phone.screenshot(path=str(OUT/'illustration-bench-mobile.png'))
    assert not errors,errors
    browser.close()
assert json.dumps(fetch('/cycles/'+cycle['id']),sort_keys=True)==before
print(f'OK : {expected_count}/{expected_count} illustrations originales harmonisées, fichiers PNG intègres via ASP.NET, nouvelles images visibles dans les anciens snapshots sur PC/mobile, agrandissement et crédits IA ; cycle inchangé.')
