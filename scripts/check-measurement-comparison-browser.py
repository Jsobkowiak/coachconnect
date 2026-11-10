"""Recorded reference dates can be analysed explicitly without changing diary data."""
import json,os,subprocess,uuid
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright,expect
from training_test_auth import authenticated_context
BASE=os.environ['TRAINING_URL'];assert ':18081' in BASE
runtime=json.loads(Path('.local/navigation-qa/runtime.json').read_text());assert runtime['container'].startswith('coachconnect-navigation-qa-')
creds=json.loads(Path('.local/navigation-qa/monthly-auth.json').read_text())
future=str(datetime.now(ZoneInfo('Europe/Paris')).date()+timedelta(days=2))
entries=[{'id':str(uuid.uuid4()),'measuredOn':'2026-03-01','datePrecision':'month','values':{'hipsCm':96,'chestCm':104},'updateProfile':False,'profileRevision':0}, {'id':str(uuid.uuid4()),'measuredOn':future,'values':{'hipsCm':97,'chestCm':99},'updateProfile':False,'profileRevision':0}]
result=subprocess.run(['docker','exec','-i',runtime['container'],'dotnet','CoachConnect.Training.dll','--import-measurements',creds['email']],input=json.dumps(entries),text=True,capture_output=True);assert result.returncode==0,'QA fixture import failed'
with sync_playwright() as p:
 browser=p.chromium.launch();context=authenticated_context(browser,BASE,fixture='.local/navigation-qa/monthly-auth.json');page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 before=context.request.get(BASE+'/api/profile/body-measurements').json()
 for query,expected in [('',[96]),('&includeReferenceMeasurements=true',[96,97])]:
  report=context.request.get(BASE+'/api/stats?months=0'+query).json();series={s['key']:s for s in report['measurements']}
  assert [p['value'] for p in series['hipsCm']['points']]==expected
  assert series['hipsCm']['recent']['recentCount']==0
 assert context.request.get(BASE+'/api/stats?months=3&includeReferenceMeasurements=true').json()['measurements'][3]['points'][0]['value']==97
 for width in (1440,390):
  page.set_viewport_size({'width':width,'height':1000});page.goto(BASE+'/#stats');page.reload();page.get_by_role('group',name='Type de statistiques').get_by_role('button',name='Mensurations',exact=True).click()
  expect(page.get_by_label('Période',exact=True)).to_have_value('0')
  for key,values in [('hipsCm',['96','97']),('chestCm',['104','99'])]:
   page.get_by_label('Mesure à suivre',exact=True).select_option(key)
   graph=page.locator('.progress-chart');expect(graph.locator('svg')).to_have_attribute('aria-label',__import__('re').compile('2 relevés'))
   graph.locator('summary').click();expect(graph.locator('tbody td:nth-child(2)')).to_have_text(values)
  page.get_by_label('Inclure les relevés avec une date de référence à venir').uncheck();expect(page.locator('.progress-chart svg')).to_have_attribute('aria-label',__import__('re').compile('1 relevés'))
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=f'.local/navigation-qa/comparison-{width}.png',full_page=True)
 assert before==context.request.get(BASE+'/api/profile/body-measurements').json()
 assert not errors,errors;browser.close()
print('OK : courbes hanches et poitrine à deux valeurs, période complète, références identifiées et optionnelles, mobile/PC et carnet inchangé.')
