"""Exercise the real API with isolated records, deleting only IDs created by this run."""
import copy
import json
import os
import unittest
import urllib.request
import urllib.error
from uuid import uuid4

BASE = os.environ.get('TRAINING_URL', 'http://localhost:8081')
from training_test_auth import install_http_auth
install_http_auth(BASE)


def request(path, method='GET', data=None):
    payload = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + '/api' + path, payload,
                                 {'Content-Type': 'application/json'} if payload else {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


class TrainingAPI(unittest.TestCase):
    def setUp(self):
        self.created = []
        status, catalog = request('/catalog/exercises?q=squat&limit=1')
        self.assertEqual(status, 200)
        self.exercise = catalog['items'][0]
        self.plan = {
            'name': 'Verification ' + uuid4().hex[:8], 'goal': '', 'notes': '',
            'discipline': 'strength', 'status': 'draft', 'startDate': '2026-10-14',
            'durationWeeks': 1, 'weeks': [{'number': 1, 'focus': '', 'notes': '', 'deload': False,
                'sessions': [{'id': str(uuid4()), 'title': 'Séance A', 'day': 0,
                    'format': 'traditional', 'durationMinutes': 60, 'timeCapMinutes': None,
                    'exercises': [{'id': str(uuid4()), 'exerciseId': self.exercise['id'],
                        'snapshot': {'name': 'FAUSSE FICHE'}, 'mode': 'reps', 'sets': 3,
                        'repsMin': 8, 'repsMax': 12, 'restSeconds': 90, 'loadKg': 40,
                        'rpe': None, 'rir': 2}]}]}]}

    def tearDown(self):
        for identifier in self.created:
            status, latest = request('/cycles/' + identifier)
            if status == 200:
                request('/cycles/' + identifier + '?revision=' + str(latest['revision']), 'DELETE')

    def create(self):
        status, cycle = request('/cycles', 'POST', self.plan)
        self.assertEqual(status, 201, cycle)
        self.created.append(cycle['id'])
        return cycle

    def test_save_snapshot_dates_conflict_and_duplicate(self):
        cycle = self.create()
        self.assertEqual(cycle['endDate'], '2026-10-20')
        row = cycle['weeks'][0]['sessions'][0]['exercises'][0]
        self.assertEqual(row['snapshot']['name'], self.exercise['name'])
        self.assertEqual(row['snapshot']['provenance'], self.exercise['provenance'])
        stale = copy.deepcopy(cycle)
        cycle['status'] = 'active'
        status, updated = request('/cycles/' + cycle['id'], 'PUT', cycle)
        self.assertEqual(status, 200, updated)
        self.assertEqual(updated['revision'], 2)
        self.assertEqual(request('/cycles/' + cycle['id'], 'PUT', stale)[0], 409)
        self.assertEqual(request('/cycles/' + cycle['id'] + '?revision=1', 'DELETE')[0], 409)
        status, duplicate = request('/cycles/' + cycle['id'] + '/duplicate', 'POST')
        self.assertEqual(status, 201, duplicate)
        self.created.append(duplicate['id'])
        self.assertEqual(duplicate['status'], 'draft')
        self.assertIsNone(duplicate['startDate'])
        self.assertNotEqual(duplicate['weeks'][0]['sessions'][0]['id'], cycle['weeks'][0]['sessions'][0]['id'])
        self.assertNotEqual(duplicate['weeks'][0]['sessions'][0]['exercises'][0]['id'], row['id'])
        updated['weeks'][0]['sessions'][0]['exercises'][0]['snapshot']['name'] = 'FAUSSE MODIFICATION'
        status, persisted = request('/cycles/' + cycle['id'], 'PUT', updated)
        self.assertEqual(status, 200)
        self.assertEqual(persisted['weeks'][0]['sessions'][0]['exercises'][0]['snapshot']['name'], self.exercise['name'])

    def test_validation_catalog_missing_and_empty_active(self):
        self.plan['weeks'][0]['sessions'][0]['exercises'][0]['repsMax'] = 1
        self.assertEqual(request('/cycles', 'POST', self.plan)[0], 400)
        self.plan['weeks'][0]['sessions'][0]['exercises'][0]['repsMax'] = 12
        self.plan['weeks'][0]['sessions'][0]['exercises'][0]['exerciseId'] = str(uuid4())
        self.assertEqual(request('/cycles', 'POST', self.plan)[0], 400)
        self.plan['weeks'][0]['sessions'] = []
        self.plan['status'] = 'active'
        self.assertEqual(request('/cycles', 'POST', self.plan)[0], 400)
        self.assertEqual(request('/cycles/not-an-id')[0], 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)
