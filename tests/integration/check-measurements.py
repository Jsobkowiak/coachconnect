"""Dated measurements: partial entries, transactions, retries and profile isolation."""
import copy,json,os,uuid,urllib.request,urllib.error,concurrent.futures
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
BASE=os.environ['MEASUREMENTS_TEST_URL'];assert ':18081' in BASE
from pathlib import Path
from training_test_auth import install_http_auth
if not os.environ.get('TRAINING_TEST_EMAIL'):
 fixture=json.loads(Path('.local/profile-qa/auth.json').read_text());os.environ['TRAINING_TEST_EMAIL']=fixture['email'];os.environ['TRAINING_TEST_PASSWORD']=fixture['password']
install_http_auth(BASE)

def req(path,method='GET',body=None):
 r=urllib.request.Request(BASE+'/api'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'},method=method)
 try:
  with urllib.request.urlopen(r) as x:return x.status,json.load(x)
 except urllib.error.HTTPError as e:return e.code,json.load(e)

def get(path):
 status,data=req(path);assert status==200,data
 return data

today=datetime.now(ZoneInfo('Europe/Paris')).date();path='/profile/body-measurements'
profile=get('/profile');assert profile['profile']
original=copy.deepcopy(profile)
cycles=get('/cycles');workouts=get('/workouts')
nutrition_before={c['id']:get('/cycles/'+c['id']+'/nutrition') for c in cycles}
legacy=get('/profile/measurements');initial=get(path)
def entry(values,**kw):return dict(id=str(uuid.uuid4()),measuredOn=str(today),values=values,notes='',updateProfile=False,profileRevision=profile['profile']['revision'],**kw)
first=entry({'waistCm':83.5,'armLeftCm':34,'armRightCm':34.2});status,saved=req(path,'POST',first);assert status==200,saved
assert get('/profile')==original and get('/profile/measurements')==legacy
assert req(path,'POST',first)==(200,saved)
assert req(path,'POST',{**first,'values':{'waistCm':84}})[0]==409
for patch in [{'values':{}},{'values':None},{'values':{'waistCm':0}},{'values':{'unknown':5}},{'values':{'armLeftCm':25.111}},{'measuredOn':str(today+timedelta(days=1))},{'notes':'x'*1001},{'updateProfile':True,'values':{'waistCm':84}}]:
 assert req(path,'POST',{**entry({'weightKg':80}),**patch})[0]==400,patch
old=entry({'weightKg':70});old['measuredOn']=str(today-timedelta(days=20));old['updateProfile']=True
assert req(path,'POST',old)[0]==400
old['updateProfile']=False;assert req(path,'POST',old)[0]==200
assert get('/profile')==original
current_weight=profile['profile']['data']['weightKg'];update=entry({'weightKg':current_weight+1,'heightCm':180});update['updateProfile']=True
with concurrent.futures.ThreadPoolExecutor() as pool:outcomes=list(pool.map(lambda _:req(path,'POST',update),range(2)))
assert all(s==200 for s,_ in outcomes) and outcomes[0][1]==outcomes[1][1],outcomes
updated=get('/profile');assert updated['profile']['revision']==profile['profile']['revision']+1
assert updated['profile']['data']['weightKg']==current_weight+1
assert len(get('/profile/measurements'))==len(legacy)+1
assert updated['estimates']!=profile['estimates']
stale=entry({'weightKg':current_weight+2});stale['updateProfile']=True
assert req(path,'POST',stale)[0]==409
assert len(get(path))==len(initial)+3
for cycle_id,before in nutrition_before.items():
 after=get('/cycles/'+cycle_id+'/nutrition')
 assert after['profileRevision']==updated['profile']['revision']
 assert after['baseline']!=before['baseline'], 'Les kcal doivent utiliser le profil actualisé'
assert get('/cycles')==cycles and get('/workouts')==workouts
assert get(path)[-1]['id']==old['id']
print('OK : mensurations partielles/dates, validation, historique, ancien contrat, rejeu concurrent, synchronisation atomique et conflit ; blocs et performances inchangés.')
