"""Profile contract/transaction checks. Requires a separate, disposable QA server."""
import copy,json,os,urllib.request,urllib.error,concurrent.futures
from datetime import date
from zoneinfo import ZoneInfo
from datetime import datetime
BASE=os.environ['PROFILE_TEST_URL']
from training_test_auth import install_http_auth
install_http_auth(BASE,save_fixture='.local/profile-qa/auth.json')
assert ':18081' in BASE,'Refusing to write a profile on the real application'
def request(method='GET',body=None,path='/profile'):
 req=urllib.request.Request(BASE+'/api'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'},method=method)
 try:
  with urllib.request.urlopen(req) as r:return r.status,json.load(r)
 except urllib.error.HTTPError as e:return e.code,json.load(e)
today=datetime.now(ZoneInfo('Europe/Paris')).date()
def save(data,revision):return request('PUT',{'revision':revision,'data':data})
assert request()[1]['profile'] is None
base={'displayName':'Profil de test','birthDate':'1990-01-01','weightKg':75,'heightCm':175,'sex':'male','activityLevel':'moderate','goal':'muscle_gain','experience':'intermediate','weeklySessions':4,'targetWeightKg':78,'trainingNotes':'Préférences de test','calorieEstimatesEnabled':True}
status,s=save(base,0);assert status==200,s
revision=s['profile']['revision'];assert revision==1 and s['ageYears']==today.year-1990
expected=10*75+6.25*175-5*s['ageYears']+5
rounded=lambda x:int((x+5)//10)*10
assert s['estimates']['restingKcal']=={'min':rounded(expected),'max':rounded(expected)}
assert s['estimates']['maintenanceKcal']=={'min':rounded(expected*1.6),'max':rounded(expected*1.6)}
assert save(base,0)[1]['profile']['revision']==1
assert len(request(path='/profile/measurements')[1])==1
for patch in [{'weightKg':-1},{'heightCm':0},{'birthDate':'2999-01-01'},{'weightKg':75.001},{'sex':'bad'},{'activityLevel':None},{'goal':'bad'},{'weeklySessions':15}]:
 assert save({**base,**patch},1)[0]==400,patch
assert request('PUT',{'revision':1,'data':None})[0]==400
assert request()[1]['profile']['revision']==1
changed={**base,'weightKg':76,'sex':'unspecified'}
status,s=save(changed,1);assert status==200 and s['estimates']['restingKcal']['min']<s['estimates']['restingKcal']['max']
assert save(base,1)[0]==409
history=request(path='/profile/measurements')[1];assert len(history)==2 and history[1]['weightKg']==75
status,s=save({**changed,'goal':'performance'},2);assert status==200
assert len(request(path='/profile/measurements')[1])==2
with concurrent.futures.ThreadPoolExecutor() as pool:
 outcomes=list(pool.map(lambda w:save({**changed,'weightKg':w},3),[77,78]))
assert sorted(r[0] for r in outcomes)==[200,409]
assert len(request(path='/profile/measurements')[1])==3
current=request()[1];d=current['profile']['data'];rev=current['profile']['revision']
status,s=save({**d,'birthDate':f'{today.year-16}-01-01'},rev);assert status==200 and s['estimates'] is None
status,s=save({**base,'calorieEstimatesEnabled':False},s['profile']['revision']);assert status==200 and s['estimates'] is None
status,s=save({**base,'birthDate':'2000-02-29'},s['profile']['revision']);assert status==200
birth=date(2000,2,29);assert s['ageYears']==today.year-birth.year-((today.month,today.day)<(birth.month,birth.day))
assert request(path='/profile/estimates')[1]['estimates']==s['estimates']
assert request(path='/cycles')[1]==[] and request(path='/workouts')[1]==[]
print('OK : création/rejeu, calculs, âge, coefficients, validation, désactivation/mineurs, mesures atomiques et concurrence ; aucun bloc ni performance modifié.')
