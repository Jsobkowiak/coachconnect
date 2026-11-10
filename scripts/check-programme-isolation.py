"""Auth/CSRF and account isolation for existing cycle save/duplicate used by programme copy."""
import os,json,urllib.request,urllib.error,http.cookiejar
from uuid import uuid4
BASE=os.environ.get('TRAINING_URL','http://localhost:18081'); assert ':18081' in BASE
class Client:
    def __init__(self):
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())); self.token=None
    def req(self,path,method='GET',data=None,csrf=True):
        headers={'Content-Type':'application/json'}
        if csrf and self.token: headers['X-CSRF-TOKEN']=self.token
        req=urllib.request.Request(BASE+'/api'+path,json.dumps(data).encode() if data is not None else None,headers,method=method)
        try:
            with self.opener.open(req) as r:
                raw=r.read(); return r.status,json.loads(raw) if raw else None
        except urllib.error.HTTPError as e: return e.code,None
    def register(self):
        self.token=self.req('/auth/session')[1]['csrfToken']
        assert self.req('/auth/register','POST',{'email':uuid4().hex+'@example.test','password':'Strong-private-phrase-'+uuid4().hex})[0] in (200,201,204)
        self.token=self.req('/auth/session')[1]['csrfToken']
a=Client(); assert a.req('/cycles')[0]==401; a.register()
plan={'name':'Owned programme','goal':'','notes':'','discipline':'mixed','status':'draft','durationWeeks':1,'startDate':None,'weeks':[{'number':1,'focus':'','notes':'','deload':False,'sessions':[]}]}
assert a.req('/cycles','POST',plan,csrf=False)[0]==403
status,cycle=a.req('/cycles','POST',plan); assert status==201
b=Client();b.register()
assert b.req('/cycles')[1]==[]
assert b.req('/cycles/'+cycle['id'])[0]==404
assert b.req('/cycles/'+cycle['id'],'PUT',cycle)[0]==404
assert b.req('/cycles/'+cycle['id']+'/duplicate','POST')[0]==404
assert a.req('/cycles/'+cycle['id'])[1]['revision']==1
print('OK : authentification, CSRF, lecture/copie/modification isolées par compte.')
