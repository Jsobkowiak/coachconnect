"""Integrated accounts, CSRF, data isolation and legacy recovery. Disposable server only."""
import json,os,urllib.request,urllib.error,http.cookiejar,copy,subprocess
from pathlib import Path
from uuid import uuid4
from datetime import date
BASE=os.environ['ACCOUNTS_TEST_URL'];assert ':18081' in BASE
OUT=Path('.local/accounts-qa');runtime=json.loads((OUT/'runtime.json').read_text());assert runtime['db'].startswith('coachconnect_accounts_test_')
class Client:
 def __init__(self):
  self.jar=http.cookiejar.CookieJar();self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar));self.token=None;self.user=None;self.last_headers=None
 def req(self,path,method='GET',data=None,csrf=True,expected=True):
  headers={'Content-Type':'application/json'}
  if csrf and self.token and method!='GET':headers['X-CSRF-TOKEN']=self.token
  if expected and self.user:headers['X-Training-User']=self.user['id']
  request=urllib.request.Request(BASE+'/api'+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
  try:
   with self.opener.open(request) as r:
    self.last_headers=r.headers;raw=r.read();return r.status,json.loads(raw) if raw else None
  except urllib.error.HTTPError as e:
   raw=e.read();return e.code,json.loads(raw) if raw else None
 def session(self):
  status,data=self.req('/auth/session',expected=False);assert status==200,data
  self.token=data['csrfToken'];self.user=data['user'];return data
 def good(self,path,method='GET',data=None):
  status,data=self.req(path,method,data);assert status in (200,201,204),(path,status,data)
  return data
 def clone(self):
  c=Client()
  for cookie in self.jar:c.jar.set_cookie(copy.deepcopy(cookie))
  c.token=self.token;c.user=copy.deepcopy(self.user);return c
anon=Client();assert anon.req('/health')[0]==200
for p in ['/cycles','/workouts','/profile','/profile/measurements','/profile/body-measurements','/stats','/catalog/exercises']:
 assert anon.req(p)[0]==401,p
assert anon.session()['user'] is None
assert anon.req('/auth/register','POST',{'email':'bad','password':'Strong long phrase 12'},csrf=False)[0]==403
assert anon.req('/auth/register','POST',{'email':'bad','password':'Strong long phrase 12'})[0]==400
assert anon.req('/auth/register','POST',{'email':'qa@example.test','password':'short'})[0]==400
password='QA-private-passphrase-'+uuid4().hex
email='owner-'+uuid4().hex+'@example.test'
a=Client();a.session();a.good('/auth/register','POST',{'email':email,'password':password,'rememberMe':True});a.session();assert a.user
assert any(c.name=='COACHCONNECT_TRAINING_SESSION' and c.expires and (c.has_nonstandard_attr('HttpOnly') or c.has_nonstandard_attr('httponly')) for c in a.jar)
assert a.req('/profile','PUT',{'revision':0,'data':{}},csrf=False)[0]==403
assert a.req('/stats',expected=False)[0]==200
# Browser requests assert the expected identity so a different account in another tab cannot receive stale operations.
oldid=a.user['id'];a.user={**a.user,'id':str(uuid4())};assert a.req('/cycles')[0]==401;a.user['id']=oldid
profile={'displayName':'Compte de test','birthDate':'1990-01-01','weightKg':77,'heightCm':180,'sex':'male','activityLevel':'moderate','goal':'muscle_gain','experience':'intermediate','weeklySessions':4,'targetWeightKg':None,'trainingNotes':'QA','calorieEstimatesEnabled':True}
a.good('/profile','PUT',{'revision':0,'data':profile})
ex=a.good('/catalog/exercises?q=squat&limit=1')['items'][0];pid=str(uuid4());sid=str(uuid4())
plan={'name':'Bloc compte propriétaire','goal':'','notes':'','discipline':'strength','status':'draft','startDate':None,'durationWeeks':1,'weeks':[{'number':1,'focus':'','notes':'','deload':False,'sessions':[{'id':sid,'title':'Salle','day':0,'format':'traditional','durationMinutes':60,'exercises':[{'id':pid,'exerciseId':ex['id'],'snapshot':{},'mode':'reps','sets':3,'repsMin':6,'repsMax':10,'restSeconds':90,'loadKg':40}]}]}]}
cycle=a.good('/cycles','POST',plan);cid=cycle['id']
w=a.good('/workouts/'+str(uuid4()),'PUT',{'revision':0,'cycleId':cid,'weekNumber':1,'sessionId':sid,'performedOn':str(date.today()),'status':'completed','notes':'','exercises':[{'prescriptionId':pid,'sets':[{'number':1,'reps':8,'loadKg':45,'completed':True}]}]})
measurement=a.good('/profile/body-measurements','POST',{'id':str(uuid4()),'measuredOn':str(date.today()),'values':{'waistCm':83},'notes':'QA','updateProfile':False,'profileRevision':1})
a.good('/cycles/'+cid+'/nutrition','PUT',{'revision':0,'cycleRevision':1,'dailyActivity':'low','sessions':[]})
paths=['/profile','/cycles','/workouts','/profile/measurements','/profile/body-measurements','/stats','/cycles/'+cid+'/nutrition'];before={p:a.good(p) for p in paths}
def normalized(data):
 data=copy.deepcopy(data)
 for path,value in data.items():
  if path.endswith('/nutrition'):value.pop('calculatedAt',None)
 return data
# Simulate pre-existing local rows; only the disposable test DB is touched.
sql=';'.join('UPDATE '+t+' SET owner_id=NULL' for t in ['training_profiles','training_cycles','training_workouts','training_nutrition_settings'])
subprocess.run(['docker','compose','--profile','catalog','--profile','training','exec','-T','training-db','psql','-U','training','-d',runtime['db'],'-c',sql],check=True,capture_output=True)
assert a.good('/profile')['profile'] is None and a.good('/cycles')==[]
b=Client();b.session();bemail='second-'+uuid4().hex+'@example.test';b.good('/auth/register','POST',{'email':bemail,'password':password});b.session()
assert b.good('/profile')['profile'] is None and b.good('/cycles')==[] and b.good('/workouts')==[]
assert b.req('/auth/claim','POST',{'token':'wrong-code'})[0]==403
code=(OUT/'owner-token').read_text().strip();a.good('/auth/claim','POST',{'token':code});a.session();assert a.user['ownsLegacyData']
after={p:a.good(p) for p in paths}
(OUT/'claim-before.json').write_text(json.dumps(before));(OUT/'claim-after.json').write_text(json.dumps(after))
assert normalized(after)==normalized(before), 'Recovery changed: '+str([p for p in paths if after[p]!=before[p]])
a.good('/auth/claim','POST',{'token':code})
assert b.req('/auth/claim','POST',{'token':code})[0]==409
for p in ['/cycles/'+cid,'/workouts/'+w['id'],'/cycles/'+cid+'/nutrition']:
 assert b.req(p)[0]==404,p
for p,method,data in [('/cycles/'+cid,'PUT',cycle),('/cycles/'+cid+'?revision=1','DELETE',None),('/cycles/'+cid+'/duplicate','POST',{}),('/workouts/'+w['id'],'PUT',w),('/workouts/'+w['id']+'?revision=1','DELETE',None),('/cycles/'+cid+'/nutrition','PUT',{'revision':1,'cycleRevision':1,'dailyActivity':'low','sessions':[]})]:
 assert b.req(p,method,data)[0]==404,(p,method)
assert b.good('/profile/measurements')==[] and b.good('/profile/body-measurements')==[]
assert b.good('/stats')['completedWorkouts']==0
b.good('/profile','PUT',{'revision':0,'data':{**profile,'displayName':'Second compte','weightKg':90}})
assert a.good('/profile')['profile']['data']['weightKg']==77
assert b.req('/profile/body-measurements','POST',{'id':measurement['id'],'measuredOn':str(date.today()),'values':{'waistCm':99},'updateProfile':False,'profileRevision':1})[0]==409
assert a.good('/profile/body-measurements')[0]['values']['waistCm']==83
assert b.req('/auth/register','POST',{'email':email.upper(),'password':password})[0]==400
# Logout revokes the server-side session, even if an old cookie is replayed.
replay=a.clone();a.good('/auth/logout','POST');assert replay.req('/profile')[0]==401
assert a.req('/profile')[0]==401;a.session()
assert a.req('/auth/login','POST',{'email':email,'password':'wrong-password'})[0]==401
a.good('/auth/login','POST',{'email':email,'password':password});a.session()
second_session=Client();second_session.session();second_session.good('/auth/login','POST',{'email':email,'password':password});second_session.session()
assert a.req('/auth/password','POST',{'currentPassword':'wrong','newPassword':'Another strong test passphrase'})[0]==400
new_password='New-private-phrase-'+uuid4().hex
a.good('/auth/password','POST',{'currentPassword':password,'newPassword':new_password})
assert second_session.req('/profile')[0]==401
a.session();assert a.req('/auth/login','POST',{'email':email,'password':password})[0]==401
a.good('/auth/login','POST',{'email':email,'password':new_password,'rememberMe':True});a.session()
assert a.good('/cycles')[0]['id']==cid
# Failed logins lock the account instead of allowing endless guesses.
for _ in range(5):assert anon.req('/auth/login','POST',{'email':bemail,'password':'wrong-password'})[0]==401
assert anon.req('/auth/login','POST',{'email':bemail,'password':password})[0]==401
assert normalized({p:a.good(p) for p in paths})==normalized(before)
(OUT/'owner.json').write_text(json.dumps({'email':email,'password':new_password,'userId':a.user['id']}))
jar=http.cookiejar.LWPCookieJar(str(OUT/'owner.cookies'))
for cookie in a.jar:jar.set_cookie(cookie)
jar.save(ignore_discard=True,ignore_expires=True)
print('OK : comptes intégrés, cookies HttpOnly, CSRF, verrouillage, séparation de toutes les données, récupération locale inchangée, conflits intercomptes, révocation logout/mot de passe et sessions indépendantes.')
