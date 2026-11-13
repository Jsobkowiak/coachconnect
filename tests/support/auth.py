"""Authentication helpers for disposable HTTP/browser tests; never disable server security."""
import json,os,secrets,http.cookiejar,urllib.request
from pathlib import Path
_cached={}
def credentials(base,fixture=None):
 if os.environ.get('TRAINING_TEST_EMAIL'):
  return {'email':os.environ['TRAINING_TEST_EMAIL'],'password':os.environ['TRAINING_TEST_PASSWORD']},False
 if fixture and Path(fixture).exists():return json.loads(Path(fixture).read_text()),False
 assert ':18081' in base,'Set TRAINING_TEST_EMAIL/PASSWORD for an authenticated test account'
 return {'email':'qa-'+secrets.token_hex(12)+'@example.test','password':'QA-private-passphrase-'+secrets.token_hex(20)},True

def install_http_auth(base,save_fixture=None):
 creds,new=credentials(base)
 jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
 def auth(path,method='GET',data=None,token=None):
  headers={'Content-Type':'application/json'}
  if token:headers['X-CSRF-TOKEN']=token
  req=urllib.request.Request(base+'/api'+path,json.dumps(data).encode() if data is not None else None,headers,method=method)
  with opener.open(req) as r:
   raw=r.read();return json.loads(raw) if raw else None
 initial=auth('/auth/session');auth('/auth/register' if new else '/auth/login','POST',creds,initial['csrfToken']);session=auth('/auth/session')
 original=urllib.request.urlopen
 def secured(req,*args,**kwargs):
  url=req.full_url if isinstance(req,urllib.request.Request) else str(req)
  if not url.startswith(base+'/api/'):return original(req,*args,**kwargs)
  if not isinstance(req,urllib.request.Request):req=urllib.request.Request(req)
  req.add_header('X-Training-User',session['user']['id'])
  if req.get_method() not in ('GET','HEAD'):req.add_header('X-CSRF-TOKEN',session['csrfToken'])
  return opener.open(req,*args,**kwargs)
 urllib.request.urlopen=secured
 if save_fixture:
  path=Path(save_fixture);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(creds));os.chmod(path,0o600)
 return creds

def authenticated_context(browser,base,profile=False,fixture=None,**kwargs):
 if fixture:creds,new=credentials(base,fixture)
 elif base in _cached:creds,new=_cached[base],False
 else:creds,new=credentials(base);_cached[base]=creds
 context=browser.new_context(**kwargs)
 state=context.request.get(base+'/api/auth/session').json()
 response=context.request.post(base+'/api/auth/'+('register' if new else 'login'),data=creds,headers={'X-CSRF-TOKEN':state['csrfToken']});assert response.ok,(response.status,response.text())
 if profile:
  session=context.request.get(base+'/api/auth/session').json();existing=context.request.get(base+'/api/profile').json()
  if existing['profile'] is None:
   assert ':18081' in base,'Refusing to populate a real profile'
   data={'displayName':'Profil de test','birthDate':'1990-01-01','weightKg':75,'heightCm':175,'sex':'male','activityLevel':'moderate','goal':'muscle_gain','experience':'intermediate','weeklySessions':4,'targetWeightKg':None,'trainingNotes':'','calorieEstimatesEnabled':True}
   response=context.request.put(base+'/api/profile',data={'revision':0,'data':data},headers={'X-CSRF-TOKEN':session['csrfToken']});assert response.ok,response.text()
 return context
