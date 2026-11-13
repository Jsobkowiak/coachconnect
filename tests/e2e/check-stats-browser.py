"""Exercise/measurement charts and responsive navigation, read-only on QA data."""
import os,json,urllib.request
from pathlib import Path
from training_test_auth import authenticated_context,install_http_auth
from playwright.sync_api import sync_playwright,expect
BASE=os.environ['STATS_TEST_URL'];assert ':18081' in BASE
fixture=json.loads(Path('.local/stats-qa/auth.json').read_text());os.environ['TRAINING_TEST_EMAIL']=fixture['email'];os.environ['TRAINING_TEST_PASSWORD']=fixture['password'];install_http_auth(BASE)
OUT=Path('.local/stats-qa');OUT.mkdir(parents=True,exist_ok=True)
def get(path):
 with urllib.request.urlopen(BASE+'/api'+path) as r:return json.load(r)
paths=['/profile','/cycles','/workouts','/profile/body-measurements','/profile/measurements'];before={k:get(k) for k in paths}
r=get('/stats?months=3');main=next(e for e in r['exercises'] if e['mode']=='time')['id']
with sync_playwright() as p:
 b=p.chromium.launch();context=authenticated_context(b,BASE,fixture='.local/stats-qa/auth.json',viewport={'width':1440,'height':1000});pc=context.new_page();errors=[]
 pc.on('pageerror',lambda e:errors.append(str(e)));pc.goto(BASE+'/#stats')
 expect(pc.get_by_role('heading',name='Voir ce qui évolue')).to_be_visible()
 expect(pc.get_by_role('navigation').get_by_role('button',name='Stats',exact=True)).to_have_attribute('aria-current','page')
 panel=pc.get_by_role('region',name='Progression par exercice')
 panel.get_by_label('Exercice',exact=True).select_option(main+':reps')
 panel.get_by_label('Comparer les séries de',exact=True).select_option('6-10')
 expect(panel.locator('.chart-reading strong')).to_have_text('70 kg')
 expect(panel.locator('.stats-comparison')).to_contain_text('+6 kg')
 explorer=panel.get_by_label('Explorer Charge maximale',exact=True)
 explorer.fill('0');expect(panel.locator('.chart-reading strong')).to_have_text('60 kg')
 explorer.press('End');expect(panel.locator('.chart-reading strong')).to_have_text('70 kg')
 panel.locator('.chart-data summary').click();expect(panel.locator('.stats-table tbody tr')).to_have_count(6)
 panel.get_by_label('Indicateur',exact=True).select_option('volume')
 expect(panel.locator('.chart-data summary')).to_contain_text('(5)')
 panel.get_by_label('Indicateur',exact=True).select_option('load')
 pc.screenshot(path=str(OUT/'stats-exercise-pc.png'),full_page=True)
 tabs=pc.get_by_role('group',name='Type de statistiques')
 tabs.get_by_role('button',name='Mensurations',exact=True).click()
 body=pc.get_by_role('region',name='Progression des mensurations')
 body.get_by_label('Mesure à suivre',exact=True).select_option('weightKg')
 expect(body.locator('.chart-reading strong')).to_have_text('83 kg')
 expect(body.locator('.stats-comparison')).to_contain_text('+2 kg')
 expect(body.locator('.chart-reading')).to_contain_text('Correction du relevé du jour')
 pc.get_by_label('Période',exact=True).select_option('6')
 expect(body.locator('.chart-data summary')).to_contain_text('(7)')
 body.get_by_label('Mesure à suivre',exact=True).select_option('armRightCm')
 expect(body.get_by_text('Pas encore de données pour cette courbe',exact=True)).to_be_visible()
 body.get_by_label('Mesure à suivre',exact=True).select_option('weightKg')
 for width in [1440,1024,768,390,320]:
  pc.set_viewport_size({'width':width,'height':900})
  expect(body.locator('svg')).to_be_visible()
  pc.wait_for_function("Math.abs(document.querySelector('.progress-chart svg').viewBox.baseVal.width-document.querySelector('.progress-chart svg').getBoundingClientRect().width)<3")
  assert pc.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
 pc.screenshot(path=str(OUT/'stats-body-mobile.png'),full_page=True)
 # The SVG uses the actual viewport width: text remains legible on a small phone.
 assert pc.locator('.progress-chart svg').evaluate('(svg)=>svg.viewBox.baseVal.width<350')
 pc.get_by_label('Période',exact=True).select_option('1')
 expect(body.locator('.stats-comparison')).to_contain_text('Comparaison à compléter')
 tabs.get_by_role('button',name='Régularité',exact=True).click()
 attendance=pc.get_by_role('region',name='Régularité des entraînements')
 expect(attendance.get_by_role('img')).to_be_visible()
 assert attendance.locator('.chart-bar').count()>0
 pc.get_by_label('Période',exact=True).select_option('0')
 expect(attendance.locator('.chart-bar')).to_have_count(len(get('/stats?months=0')['attendance']))
 pc.screenshot(path=str(OUT/'stats-attendance-mobile.png'),full_page=True)
 pc.reload();expect(pc.get_by_role('heading',name='Voir ce qui évolue')).to_be_visible()
 # A failed refresh hides old curves and offers recovery.
 pc.route('**/api/stats?*',lambda route:route.fulfill(status=503,content_type='application/json',body='{"message":"Serveur de test indisponible"}'))
 pc.get_by_role('button',name='Actualiser',exact=True).click()
 expect(pc.get_by_role('alert')).to_contain_text('Serveur de test indisponible')
 expect(pc.locator('.progress-chart')).to_have_count(0)
 pc.unroute('**/api/stats?*');pc.get_by_role('button',name='Réessayer',exact=True).click()
 expect(pc.get_by_role('region',name='Progression par exercice')).to_be_visible()
 assert not errors,errors
 b.close()
assert {k:get(k) for k in paths}==before,'Browser statistics must not write data'
print('OK : navigation Stats, courbes et détails, filtres/périodes, comparaison 28 jours, curseur clavier, données absentes, reprise après erreur, PC/mobile 320–1440px et aucune mutation.')
