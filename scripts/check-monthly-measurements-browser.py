"""Monthly precision and imported future references remain correctly labelled and filtered."""
import os,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from training_test_auth import authenticated_context
BASE=os.environ['TRAINING_URL'];assert ':18081' in BASE
with sync_playwright() as p:
 b=p.chromium.launch();context=authenticated_context(b,BASE,fixture='.local/navigation-qa/monthly-auth.json',viewport={'width':390,'height':900});page=context.new_page();errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)));page.goto(BASE+'/#profil')
 history=page.locator('.measurement-history');expect(history.get_by_text('mars 2026',exact=True)).to_be_visible();expect(history.get_by_text('février 2026',exact=True)).to_be_visible()
 expect(history.get_by_text('Jour non précisé',exact=True)).to_have_count(2)
 expect(history.get_by_text('À venir · hors des courbes jusqu’à cette date',exact=True)).to_be_visible()
 state=context.request.get(BASE+'/api/profile').json();assert state['profile']['data']['weightKg']==75
 records=context.request.get(BASE+'/api/profile/body-measurements').json();assert len(records)==4
 page.get_by_role('button',name='Stats',exact=True).click();page.get_by_role('group',name='Type de statistiques').get_by_role('button',name='Mensurations',exact=True).click()
 page.get_by_label('Inclure les relevés avec une date de référence à venir').uncheck();page.get_by_label('Période',exact=True).select_option('0');page.get_by_label('Mesure à suivre',exact=True).select_option('armUnspecifiedCm')
 panel=page.get_by_role('region',name='Progression des mensurations');expect(panel.locator('.chart-reading')).to_contain_text('mars 2026')
 assert '01/03/2026' not in panel.inner_text()
 page.get_by_label('Mesure à suivre',exact=True).select_option('armFlexedCm');expect(panel.locator('.chart-reading strong')).to_have_text('36 cm')
 page.set_viewport_size({'width':320,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.screenshot(path='.local/navigation-qa/monthly-stats-mobile.png',full_page=True)
 assert not errors,errors;b.close()
print('OK : mois sans faux jour, relevé à venir identifié, courbes sans dates futures, bras distincts et profil préservé sur mobile.')
