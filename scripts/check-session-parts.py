"""Compound plans keep legacy contracts, validate membership and freeze workout snapshots."""
import copy, importlib.util, unittest
from pathlib import Path
from uuid import uuid4
spec = importlib.util.spec_from_file_location('base_checks', Path(__file__).with_name('check-workouts.py'))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
request = base.request

class SessionPartsAPI(base.WorkoutAPI):
    def compound(self):
        session = self.plan['weeks'][0]['sessions'][0]
        original = session['exercises'][0]
        session['parts'] = [{'id': str(uuid4()), 'title': name, 'format': fmt, 'timeCapMinutes': minutes, 'notes': 'Consigne de test'} for name, fmt, minutes in [('Force','traditional',20),('AMRAP A','amrap',12),('AMRAP B','amrap',8)]]
        session['exercises'] = [dict(copy.deepcopy(original), id=str(uuid4()), partId=p['id']) for p in session['parts']]
        return session

    def test_membership_order_duplicate_and_frozen_snapshot(self):
        planned = self.compound()
        planned['exercises'].reverse()
        cycle = self.create(); session = cycle['weeks'][0]['sessions'][0]
        self.assertEqual([e['partId'] for e in session['exercises']], [p['id'] for p in session['parts']])
        status, duplicate = request('/cycles/'+cycle['id']+'/duplicate', 'POST')
        self.assertEqual(status,201,duplicate); self.created.append(duplicate['id'])
        copied = duplicate['weeks'][0]['sessions'][0]
        self.assertTrue(set(p['id'] for p in session['parts']).isdisjoint(p['id'] for p in copied['parts']))
        self.assertEqual([e['partId'] for e in copied['exercises']], [p['id'] for p in copied['parts']])
        wid = str(uuid4()); self.workouts.append(wid)
        data={'cycleId':cycle['id'],'weekNumber':1,'sessionId':session['id'],'performedOn':'2026-11-05','status':'in_progress','revision':0,'notes':'','exercises':[{'prescriptionId':session['exercises'][0]['id'],'sets':[{'number':1,'reps':8,'loadKg':40,'completed':True}]}]}
        status, workout = request('/workouts/'+wid,'PUT',data); self.assertEqual(status,200,workout)
        frozen = copy.deepcopy(workout['plannedSession'])
        session['parts'][0]['title']='Modified after workout'
        self.assertEqual(request('/cycles/'+cycle['id'],'PUT',cycle)[0],200)
        workout['status']='completed'
        status, saved=request('/workouts/'+wid,'PUT',workout)
        self.assertEqual(status,200,saved); self.assertEqual(saved['plannedSession'],frozen)

    def test_reject_orphan_duplicate_empty_active_parts(self):
        session = self.compound()
        valid = copy.deepcopy(self.plan)
        session['exercises'][0]['partId']=str(uuid4())
        self.assertEqual(request('/cycles','POST',self.plan)[0],400)
        self.plan=copy.deepcopy(valid); self.plan['weeks'][0]['sessions'][0]['parts'][1]['id']=self.plan['weeks'][0]['sessions'][0]['parts'][0]['id']
        self.assertEqual(request('/cycles','POST',self.plan)[0],400)
        self.plan=copy.deepcopy(valid); self.plan['status']='active'; self.plan['weeks'][0]['sessions'][0]['exercises'].pop()
        self.assertEqual(request('/cycles','POST',self.plan)[0],400)
        self.plan=copy.deepcopy(valid); self.plan['weeks'][0]['sessions'][0]['parts'][0]['timeCapMinutes']=-1
        self.assertEqual(request('/cycles','POST',self.plan)[0],400)

if __name__=='__main__': unittest.main()
