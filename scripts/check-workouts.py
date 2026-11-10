"""Verify actual performances stay independent from mutable programme prescriptions."""
import copy
import unittest
from uuid import uuid4
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('training_checks', Path(__file__).with_name('check-training.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TrainingAPI, request = module.TrainingAPI, module.request


class WorkoutAPI(TrainingAPI):
    def setUp(self):
        super().setUp()
        self.workouts = []

    def tearDown(self):
        for identifier in self.workouts:
            status, record = request('/workouts/' + identifier)
            if status == 200:
                request('/workouts/' + identifier + '?revision=' + str(record['revision']), 'DELETE')
        super().tearDown()

    def test_workout_history_retry_revision_and_programme_independence(self):
        cycle = self.create()
        planned = cycle['weeks'][0]['sessions'][0]
        workout_id = str(uuid4())
        self.workouts.append(workout_id)
        payload = {'cycleId': cycle['id'], 'weekNumber': 1, 'sessionId': planned['id'],
                   'performedOn': '2026-10-16', 'status': 'in_progress', 'notes': '', 'revision': 0,
                   'exercises': [{'prescriptionId': planned['exercises'][0]['id'], 'sets': [
                       {'number': 1, 'reps': 8, 'loadKg': 42.5, 'durationSeconds': None,
                        'distanceMeters': None, 'rpe': None, 'completed': True}]}]}
        status, saved = request('/workouts/' + workout_id, 'PUT', payload)
        self.assertEqual(status, 200, saved)
        self.assertEqual(saved['revision'], 1)
        # A retry after a lost response must not create a second workout or increment revision.
        self.assertEqual(request('/workouts/' + workout_id, 'PUT', payload)[1]['revision'], 1)
        cycle['weeks'][0]['sessions'][0]['exercises'][0]['sets'] = 5
        self.assertEqual(request('/cycles/' + cycle['id'], 'PUT', cycle)[0], 200)
        saved['revision'] = 1
        saved['status'] = 'completed'
        status, updated = request('/workouts/' + workout_id, 'PUT', saved)
        self.assertEqual(status, 200, updated)
        self.assertEqual(updated['plannedSession']['exercises'][0]['sets'], 3)
        self.assertEqual(request('/workouts/' + workout_id, 'PUT', saved)[0], 409)
        self.assertEqual(request('/workouts/' + workout_id + '?revision=1', 'DELETE')[0], 409)
        status, latest_cycle = request('/cycles/' + cycle['id'])
        self.assertEqual(latest_cycle['weeks'][0]['sessions'][0]['exercises'][0]['loadKg'], 40)
        request('/cycles/' + cycle['id'] + '?revision=' + str(latest_cycle['revision']), 'DELETE')
        self.assertEqual(request('/workouts/' + workout_id)[0], 200)

    def test_invalid_performance_and_false_snapshot(self):
        cycle = self.create()
        session = cycle['weeks'][0]['sessions'][0]
        identifier = str(uuid4())
        self.workouts.append(identifier)
        payload = {'cycleId': cycle['id'], 'weekNumber': 1, 'sessionId': session['id'],
                   'performedOn': '2026-10-16', 'status': 'completed', 'notes': '', 'revision': 0,
                   'exercises': [{'prescriptionId': session['exercises'][0]['id'], 'sets': [
                       {'number': 1, 'reps': None, 'loadKg': 40, 'completed': True}]}],
                   'plannedSession': {'title': 'FORGED'}}
        self.assertEqual(request('/workouts/' + identifier, 'PUT', payload)[0], 400)
        payload['exercises'][0]['sets'][0]['reps'] = -1
        self.assertEqual(request('/workouts/' + identifier, 'PUT', payload)[0], 400)
        payload['exercises'][0]['sets'][0]['reps'] = 8
        status, saved = request('/workouts/' + identifier, 'PUT', payload)
        self.assertEqual(status, 200, saved)
        self.assertEqual(saved['plannedSession']['title'], session['title'])
        invalid = copy.deepcopy(saved)
        invalid['weekNumber'] = 2
        self.assertEqual(request('/workouts/' + identifier, 'PUT', invalid)[0], 400)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(WorkoutAPI(name) for name in (
        'test_workout_history_retry_revision_and_programme_independence',
        'test_invalid_performance_and_false_snapshot'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
