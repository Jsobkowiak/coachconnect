"""Unknown days and non-lateralized measurements preserve the recorded meaning."""
import json,os,urllib.request,urllib.error,uuid
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from training_test_auth import install_http_auth
BASE=os.environ['TRAINING_URL'];assert ':18081' in BASE
install_http_auth(BASE,save_fixture='.local/navigation-qa/monthly-auth.json')
def req(path,method='GET',data=None):
 r=urllib.request.Request(BASE+'/api'+path,json.dumps(data).encode() if data else None,{'Content-Type':'application/json'},method=method)
 try:
  with urllib.request.urlopen(r) as x:return x.status,json.load(x)
 except urllib.error.HTTPError as e:return e.code,json.load(e)
profile={'displayName':'Test mensuel','birthDate':'1990-01-01','weightKg':75,'heightCm':175,'sex':'male','activityLevel':'moderate','goal':'performance','experience':'intermediate','weeklySessions':4,'targetWeightKg':None,'trainingNotes':'','calorieEstimatesEnabled':True}
assert req('/profile','PUT',{'revision':0,'data':profile})[0]==200
body={'id':str(uuid.uuid4()),'measuredOn':'2026-03-01','datePrecision':'month','values':{'armUnspecifiedCm':37,'thighCm':61,'waistCm':85},'notes':'Jour et contraction non précisés','updateProfile':False,'profileRevision':1}
assert req('/profile/body-measurements','POST',body)[0]==200
assert req('/profile/body-measurements','POST',body)[0]==200
bad={**body,'id':str(uuid.uuid4()),'measuredOn':'2026-03-15'};assert req('/profile/body-measurements','POST',bad)[0]==400
bad={**body,'datePrecision':'unknown'};assert req('/profile/body-measurements','POST',bad)[0]==400
now=datetime.now(ZoneInfo('Europe/Paris')).date()
latest={**body,'id':str(uuid.uuid4()),'measuredOn':str(now),'datePrecision':'day','values':{'armFlexedCm':36,'neckCm':37,'calfCm':38},'notes':'Bras contracté, côté non précisé'}
assert req('/profile/body-measurements','POST',latest)[0]==200
future={**latest,'id':str(uuid.uuid4()),'measuredOn':str(now+timedelta(days=1))};assert req('/profile/body-measurements','POST',future)[0]==400
records=req('/profile/body-measurements')[1];assert len(records)==2 and records[1]['datePrecision']=='month'
report=req('/stats?months=0')[1]
find=lambda key:next(s for s in report['measurements'] if s['key']==key)
assert find('armUnspecifiedCm')['points'][0]['datePrecision']=='month'
assert find('armFlexedCm')['points'][0]['value']==36
assert find('armLeftCm')['points']==[] and find('armRightCm')['points']==[]
assert find('armUnspecifiedCm')['recent']['previousCount']==0 and find('armUnspecifiedCm')['recent']['recentCount']==0
assert req('/profile')[1]['profile']['data']['weightKg']==75
print('OK : précision mensuelle sans faux jour, contraction/côtés conservés, cou, idempotence, validation et exclusion des moyennes courtes ; profil inchangé.')
