"""Statistics against real HTTP APIs, exclusively on a disposable QA server."""
import json,os,urllib.request,urllib.error,copy
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4
BASE=os.environ['STATS_TEST_URL'];assert ':18081' in BASE,'Disposable server required'
from training_test_auth import install_http_auth
install_http_auth(BASE,save_fixture='.local/stats-qa/auth.json')
today=datetime.now(ZoneInfo('Europe/Paris')).date()
def req(path,method='GET',body=None):
 r=urllib.request.Request(BASE+'/api'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'},method=method)
 try:
  with urllib.request.urlopen(r) as x:
   data=x.read();return x.status,json.loads(data) if data else None
 except urllib.error.HTTPError as e:
  data=e.read();return e.code,json.loads(data) if data else None
def get(path):
 status,data=req(path);assert status==200,(status,data)
 return data
def post(path,body,method='POST'):
 status,data=req(path,method,body);assert status in (200,201),(status,data)
 return data
def day(offset):return str(today+timedelta(days=offset))
empty=get('/stats');assert empty['completedWorkouts']==0 and empty['exercises']==[]
assert all(not s['points'] for s in empty['measurements'])
profile=post('/profile',{'revision':0,'data':{'displayName':'Stats test','birthDate':'1990-01-01','weightKg':77,'heightCm':180,'sex':'male','activityLevel':'moderate','goal':'muscle_gain','experience':'intermediate','weeklySessions':4,'targetWeightKg':None,'trainingNotes':'','calorieEstimatesEnabled':True}},'PUT')
items=get('/catalog/exercises?q=squat&limit=2')['items'];assert len(items)>=2
exercise,variant=items[:2]
def prescription(exercise_id,mode):return {'id':str(uuid4()),'exerciseId':exercise_id,'snapshot':{},'mode':mode,'sets':3,'repsMin':6,'repsMax':10,'durationSeconds':60,'distanceMeters':1000,'restSeconds':90,'loadKg':40,'rpe':None,'rir':2}
rows=[prescription(exercise['id'],mode) for mode in ['reps','reps','time','distance']]+[prescription(variant['id'],'reps')]
session={'id':str(uuid4()),'title':'Stats fixture','day':0,'format':'traditional','durationMinutes':60,'exercises':rows}
cycle=post('/cycles',{'name':'QA progression','goal':'','notes':'','discipline':'strength','status':'draft','startDate':None,'durationWeeks':1,'weeks':[{'number':1,'focus':'','notes':'','deload':False,'sessions':[session]}]})
def series_set(number,reps=None,load=None,seconds=None,meters=None,done=True):return {'number':number,'reps':reps,'loadKg':load,'durationSeconds':seconds,'distanceMeters':meters,'completed':done}
def workout(offset,load,status='completed'):
 sets=[{'prescriptionId':rows[0]['id'],'sets':[series_set(1,8,load),series_set(2,10,None if offset==-10 else load-10),series_set(3,50,999,done=False)]},
       {'prescriptionId':rows[1]['id'],'sets':[series_set(1,4,90)]},
       {'prescriptionId':rows[2]['id'],'sets':[series_set(1,seconds=60+load)]},
       {'prescriptionId':rows[3]['id'],'sets':[series_set(1,meters=1000+load)]},
       {'prescriptionId':rows[4]['id'],'sets':[series_set(1,8,200)]}]
 return post('/workouts/'+str(uuid4()),{'cycleId':cycle['id'],'weekNumber':1,'sessionId':session['id'],'performedOn':day(offset),'status':status,'notes':'','revision':0,'exercises':sets},'PUT')
for offset,load in [(-210,40),(-120,50),(-40,60),(-35,62),(-30,64),(-20,66),(-10,68),(0,70)]:workout(offset,load)
workout(0,400,'in_progress');workout(5,500)
def measure(offset,values,notes=''):
 return post('/profile/body-measurements',{'id':str(uuid4()),'measuredOn':day(offset),'values':values,'notes':notes,'updateProfile':False,'profileRevision':profile['profile']['revision']})
for offset,weight in [(-210,75),(-120,76),(-40,80),(-35,79.9),(-30,80.1),(-20,81),(-10,82),(0,84)]:measure(offset,{'weightKg':weight,'waistCm':85})
measure(0,{'weightKg':83},'Correction du relevé du jour')
measure(0,{'armLeftCm':35})
sources=['/profile','/cycles','/workouts','/profile/body-measurements','/profile/measurements'];before={s:get(s) for s in sources}
r=get('/stats?months=3');assert r['completedWorkouts']==6 and r['excludedInProgress']==1
assert sum(p['value'] for p in r['attendance'])==6
assert all(p['value']==0 for p in r['attendance'] if p['date']<day(-49))
assert r['measurementDays']==6
assert len(r['exercises'])==4
body=lambda key:next(s for s in r['measurements'] if s['key']==key)
assert body('weightKg')['points'][-1]['value']==83
assert len(body('weightKg')['points'])==6 and body('weightKg')['recent']['change']==2
assert body('weightKg')['recent']['previousMean']==80 and body('weightKg')['recent']['recentMean']==82
assert body('heightCm')['points'][-1]['value']==180
assert body('armRightCm')['points']==[] and body('armLeftCm')['recent']['change'] is None
main=next(e for e in r['exercises'] if e['id']==exercise['id'] and e['mode']=='reps')
metric=lambda e,key:next(s for s in e['series'] if s['key']==key)
assert metric(main,'load')['points'][-1]['value']==90
assert metric(main,'totalReps')['points'][-1]['value']==22
assert metric(main,'sets')['points'][-1]['value']==3
assert metric(main,'volume')['points'][-1]['value']==1520
assert len(metric(main,'volume')['points'])==5,'Missing load must not become zero'
filtered=get('/stats?months=3&minReps=6&maxReps=10')
mainf=next(e for e in filtered['exercises'] if e['id']==exercise['id'] and e['mode']=='reps')
loads=metric(mainf,'load');assert [p['value'] for p in loads['points']]==[60,62,64,66,68,70]
assert loads['recent']['previousMean']==62 and loads['recent']['recentMean']==68 and loads['recent']['change']==6
assert all('8 répétitions' in p['detail'] for p in loads['points'])
assert metric(next(e for e in r['exercises'] if e['mode']=='time'),'duration')['points'][-1]['value']==130
assert metric(next(e for e in r['exercises'] if e['mode']=='distance'),'distance')['points'][-1]['value']==1070
one_month=get('/stats?months=1')
assert one_month['completedWorkouts']==sum(day(d)>=one_month['from'] for d in [-210,-120,-40,-35,-30,-20,-10,0])
assert get('/stats?months=6')['completedWorkouts']==7
assert get('/stats?months=12')['completedWorkouts']==8
assert get('/stats?months=0')['completedWorkouts']==8
for query in ['months=2','minReps=0','minReps=11&maxReps=5','months=abc']:
 assert req('/stats?'+query)[0]==400,query
assert {s:get(s) for s in sources}==before,'Statistics must be read-only'
# Multiple workouts on the same date are combined; plans never change recorded performance.
extra=workout(0,72)
combined=get('/stats?months=3&minReps=6&maxReps=10');combined_main=next(e for e in combined['exercises'] if e['id']==exercise['id'] and e['mode']=='reps')
assert metric(combined_main,'load')['points'][-1]['value']==72
assert metric(combined_main,'totalReps')['points'][-1]['value']==36
assert metric(combined_main,'sets')['points'][-1]['value']==4
req('/workouts/'+extra['id']+'?revision=1','DELETE')
changed=copy.deepcopy(cycle);changed['weeks'][0]['sessions'][0]['exercises'][0]['loadKg']=950
post('/cycles/'+cycle['id'],changed,'PUT')
assert get('/stats?months=3')==r
latest=get('/cycles/'+cycle['id']);assert req('/cycles/'+cycle['id']+'?revision='+str(latest['revision']),'DELETE')[0]==204
assert get('/stats?months=3')==r,'Deleted plan must not erase stats'
print('OK : périodes 1/3/6/12/tout, séries validées/terminées, variantes et modes distincts, charge/reps/volume, filtre de reps, dates regroupées, mesures historiques, comparaison 28 jours et lecture seule ; modification/suppression des blocs sans effet.')
