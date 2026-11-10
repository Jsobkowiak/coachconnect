"""Nutrition forecast invariants, against a disposable server only."""
import json,os,copy,urllib.request,urllib.error,concurrent.futures
from uuid import uuid4
BASE=os.environ['NUTRITION_TEST_URL'];assert ':18081' in BASE,'Only a disposable QA server is allowed'
from training_test_auth import install_http_auth
install_http_auth(BASE,save_fixture='.local/nutrition-qa/auth.json')
def req(path,method='GET',body=None):
 r=urllib.request.Request(BASE+'/api'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'},method=method)
 try:
  with urllib.request.urlopen(r) as x:return x.status,json.load(x)
 except urllib.error.HTTPError as e:return e.code,json.load(e)
exercise=req('/catalog/exercises?q=Squat%20arri%C3%A8re&limit=1')[1]['items'][0]
def session(title,day,minutes,empty=False):
 return {'id':str(uuid4()),'title':title,'day':day,'format':'amrap' if empty else 'traditional','durationMinutes':minutes,'timeCapMinutes':10,'exercises':[] if empty else [{'id':str(uuid4()),'exerciseId':exercise['id'],'snapshot':{},'mode':'reps','sets':3,'repsMin':8,'repsMax':12,'restSeconds':90,'loadKg':40}]}
plan={'name':'QA Nutrition — 12 semaines','goal':'','notes':'','discipline':'mixed','status':'draft','startDate':'2026-10-26','durationWeeks':12,'weeks':[{'number':i,'focus':'Progression','notes':'','deload':i==2,'sessions':[session('Force A',0,60),session('WOD à préciser',2,60,True),session('Force B',5,30)]} for i in range(1,13)]}
status,cycle=req('/cycles','POST',plan);assert status==201,cycle
id=cycle['id'];path=f'/cycles/{id}/nutrition'
assert req(path)[0]==409
profile={'displayName':'Test','birthDate':'1990-01-01','weightKg':75,'heightCm':175,'sex':'male','activityLevel':'very_active','goal':'maintenance','experience':'intermediate','weeklySessions':3,'targetWeightKg':None,'trainingNotes':'','calorieEstimatesEnabled':True}
status,p=req('/profile','PUT',{'revision':0,'data':profile});assert status==200
profile_before=copy.deepcopy(p);cycle_before=copy.deepcopy(cycle)
status,r=req(path);assert status==200,r
assert r['durationWeeks']==12 and len(r['weeks'])==12 and all(len(w['days'])==7 for w in r['weeks'])
assert r['missingSessions']==12 and not r['complete'] and r['dailyAverage'] is None
base=p['estimates']['restingKcal']['min']*1.4
assert abs(r['baseline']['min']-base)<0.001,'Global activity factor must not be added again'
day=r['weeks'][0]['days'][0];assert day['sessions'][0]['activity']=='strength'
assert abs(day['maintenance']['min']-(base*(1-1/24)+3.5*75))<0.001
assert day['sessions'][0]['durationMinutes']==60,'Time cap is not total duration'
assert r['weeks'][0]['days'][1]['status']=='rest' and r['weeks'][0]['days'][1]['maintenance']['min']==base
assert r['weeks'][0]['days'][2]['status']=='incomplete' and r['weeks'][0]['days'][2]['maintenance'] is None
assert r['weeks'][0]['days'][0]['maintenance']==r['weeks'][1]['days'][0]['maintenance'],'Deload flag alone cannot invent lower intensity'
settings={'revision':0,'cycleRevision':cycle['revision'],'dailyActivity':'low','sessions':[{'sessionId':w['sessions'][1]['id'],'activity':'circuit','durationMinutes':20} for w in cycle['weeks']]}
status,r=req(path,'PUT',settings);assert status==200 and r['complete'] and r['settingsRevision']==1
assert r['missingSessions']==0 and abs(r['blockMaintenance']['min']-sum(w['weeklyMaintenance']['min'] for w in r['weeks']))<0.0001
assert abs(r['dailyAverage']['min']-r['blockMaintenance']['min']/84)<0.001
assert req(path)[1]['settingsRevision']==1
assert req(path,'PUT',settings)[0]==409
for sessions in [[{'sessionId':str(uuid4()),'activity':'strength','durationMinutes':60}],[{**settings['sessions'][0],'durationMinutes':0}],[{**settings['sessions'][0],'activity':'magic'}],[settings['sessions'][0],settings['sessions'][0]]]:
 assert req(path,'PUT',{**settings,'revision':1,'sessions':sessions})[0]==400
assert req(path,'PUT',{**settings,'revision':1,'cycleRevision':99})[0]==409
# Per-week override changes only the selected week.
short={'sessionId':cycle['weeks'][1]['sessions'][0]['id'],'activity':'strength','durationMinutes':15}
status,r=req(path,'PUT',{**settings,'revision':1,'sessions':settings['sessions']+[short]});assert status==200
assert r['weeks'][1]['dailyAverage']['min']<r['weeks'][0]['dailyAverage']['min']
assert req('/cycles/'+id)[1]==cycle_before and req('/profile')[1]==profile_before and req('/workouts')[1]==[]
# Race: one settings update wins, the other receives 409.
with concurrent.futures.ThreadPoolExecutor() as pool:
 results=list(pool.map(lambda activity:req(path,'PUT',{**settings,'revision':2,'dailyActivity':activity}),['low','moderate']))
assert sorted(x[0] for x in results)==[200,409]
# Unknown physiological coefficient returns ordered ranges, including the net training increment.
status,p=req('/profile','PUT',{'revision':p['profile']['revision'],'data':{**profile,'sex':'unspecified'}});assert status==200
r=req(path)[1];assert r['profileRevision']==p['profile']['revision']
for w in r['weeks']:
 for d in w['days']:
  assert d['maintenance']['min']<=d['maintenance']['max']
  assert d['trainingExtra']['min']<=d['trainingExtra']['max']
# Profile changes recalculate; editing a block marks saved hypotheses for review.
newcycle=copy.deepcopy(cycle);newcycle['weeks'][0]['sessions'].append(session('Deuxième séance',0,30))
status,newcycle=req('/cycles/'+id,'PUT',newcycle);assert status==200
r=req(path)[1];assert r['needsReview'] and r['cycleRevision']==newcycle['revision']
assert len(r['weeks'][0]['days'][0]['sessions'])==2
assert r['weeks'][0]['days'][0]['maintenance']['min']>r['weeks'][1]['days'][0]['maintenance']['min']
assert req(path,'PUT',{**settings,'revision':3})[0]==409
# Return to a simple 12-week fixture, with one unknown slot per week for UI configuration.
status,fixture=req('/cycles/'+id,'PUT',{**cycle_before,'revision':newcycle['revision']});assert status==200
status,r=req(path,'PUT',{'revision':3,'cycleRevision':fixture['revision'],'dailyActivity':'low','sessions':[]});assert status==200 and r['missingSessions']==12
assert req('/workouts')[1]==[]
print('OK : 12 semaines/84 jours, repos, incomplets, MET et time caps, absence de double comptage, totaux, deload explicite, persistance, révisions, concurrence et profil actualisé ; programmes/perfs préservés.')
