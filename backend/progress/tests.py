from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from chat.models import Conversation

from .models import LearningPlan, SkillProgress
from .services import create_plan_from_roadmap

User = get_user_model()

ROADMAP = {
    'goal': 'ML Engineer',
    'duration': '6 months',
    'starting_level': 'Intermediate',
    'steps': [
        {'title': 'Python foundations', 'duration': '3 weeks', 'description': 'Core Python', 'topics': ['Python', 'NumPy']},
        {'title': 'Math for ML', 'duration': '4 weeks', 'description': 'Linear algebra', 'topics': ['Linear Algebra']},
        {'title': 'Classical ML', 'duration': '6 weeks', 'description': 'Sklearn', 'topics': ['Regression', 'Python']},
        {'title': 'Deep learning', 'duration': '8 weeks', 'description': 'PyTorch', 'topics': ['Neural Networks']},
    ],
    'projects': ['Build a churn predictor'],
    'milestones': ['Finish the basics', 'Train a first model'],
    'next_action': 'Install Python and set up a virtualenv',
}


class PlanCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='learner@example.com', email='learner@example.com', password='Str0ngPass!42'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_roadmap_becomes_a_tracked_plan(self):
        response = self.client.post('/api/plans/', {'roadmap': ROADMAP}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['goal'], 'ML Engineer')
        self.assertEqual(len(response.data['steps']), 4)
        self.assertEqual(len(response.data['milestones']), 2)
        self.assertEqual(response.data['percent_complete'], 0)
        self.assertEqual(response.data['steps'][0]['topics'], ['Python', 'NumPy'])

    def test_study_material_is_carried_onto_the_saved_step(self):
        roadmap = dict(ROADMAP)
        roadmap['steps'] = [
            {
                'title': 'Python foundations',
                'topics': ['Python'],
                'topic_materials': [
                    {'topic': 'Python', 'study_material': {'website': {'name': 'Docs', 'url': 'https://docs.python.org'}}}
                ],
            }
        ]

        response = self.client.post('/api/plans/', {'roadmap': roadmap}, format='json')

        material = response.data['steps'][0]['study_material']
        self.assertEqual(material['by_topic']['Python']['website']['url'], 'https://docs.python.org')

    def test_a_roadmap_without_steps_is_rejected(self):
        for roadmap in [{'goal': 'x'}, {'goal': 'x', 'steps': []}, {'goal': 'x', 'steps': 'nope'}]:
            with self.subTest(roadmap=roadmap):
                self.assertEqual(
                    self.client.post('/api/plans/', {'roadmap': roadmap}, format='json').status_code, 400
                )

    def test_a_plan_cannot_be_attached_to_someone_elses_conversation(self):
        other = User.objects.create_user(username='other@example.com', email='other@example.com', password='Str0ngPass!99')
        theirs = Conversation.objects.create(user=other)

        response = self.client.post(
            '/api/plans/', {'roadmap': ROADMAP, 'conversation_id': theirs.id}, format='json'
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(LearningPlan.objects.exists())

    def test_plans_require_authentication(self):
        self.assertEqual(APIClient().get('/api/plans/').status_code, 401)

    def test_tracking_the_same_roadmap_twice_is_refused(self):
        conversation = Conversation.objects.create(user=self.user)
        first = self.client.post(
            '/api/plans/', {'roadmap': ROADMAP, 'conversation_id': conversation.id}, format='json'
        )
        self.assertEqual(first.status_code, 201)

        again = self.client.post(
            '/api/plans/', {'roadmap': ROADMAP, 'conversation_id': conversation.id}, format='json'
        )

        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.data['plan']['id'], first.data['id'])
        self.assertEqual(LearningPlan.objects.count(), 1)

    def test_the_duplicate_guard_ignores_the_conversation_it_came_from(self):
        self.client.post('/api/plans/', {'roadmap': ROADMAP}, format='json')

        again = self.client.post('/api/plans/', {'roadmap': ROADMAP}, format='json')

        self.assertEqual(again.status_code, 409)
        self.assertEqual(LearningPlan.objects.count(), 1)

    def test_a_revised_roadmap_can_still_be_tracked(self):
        self.client.post('/api/plans/', {'roadmap': ROADMAP}, format='json')
        revised = dict(ROADMAP, steps=ROADMAP['steps'] + [{'title': 'Serving at scale', 'topics': ['Kubernetes']}])

        response = self.client.post('/api/plans/', {'roadmap': revised}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(LearningPlan.objects.count(), 2)

    def test_a_different_goal_is_not_a_duplicate(self):
        self.client.post('/api/plans/', {'roadmap': ROADMAP}, format='json')

        response = self.client.post('/api/plans/', {'roadmap': dict(ROADMAP, goal='Data Analyst')}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(LearningPlan.objects.count(), 2)

    def test_another_learner_tracking_the_same_roadmap_is_not_blocked(self):
        self.client.post('/api/plans/', {'roadmap': ROADMAP}, format='json')
        other = User.objects.create_user(username='other@example.com', email='other@example.com', password='Str0ngPass!99')
        theirs = APIClient()
        theirs.force_authenticate(other)

        self.assertEqual(theirs.post('/api/plans/', {'roadmap': ROADMAP}, format='json').status_code, 201)


class ProgressTrackingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='learner@example.com', email='learner@example.com', password='Str0ngPass!42'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.plan = create_plan_from_roadmap(self.user, ROADMAP)
        self.steps = list(self.plan.steps.all())

    def complete(self, step, done=True):
        return self.client.patch(f'/api/steps/{step.id}/', {'is_completed': done}, format='json')

    def test_completing_steps_moves_the_percentage(self):
        self.assertEqual(self.complete(self.steps[0]).data['percent_complete'], 25)
        self.assertEqual(self.complete(self.steps[1]).data['percent_complete'], 50)
        self.assertEqual(self.complete(self.steps[0], False).data['percent_complete'], 25)

    def test_milestones_tick_at_their_share_of_the_plan(self):
        self.assertFalse(self.complete(self.steps[0]).data['milestones'][0]['is_completed'])

        response = self.complete(self.steps[1])
        self.assertTrue(response.data['milestones'][0]['is_completed'])
        self.assertFalse(response.data['milestones'][1]['is_completed'])

        self.complete(self.steps[2])
        response = self.complete(self.steps[3])
        self.assertTrue(all(m['is_completed'] for m in response.data['milestones']))

    def test_reopening_a_step_rolls_its_milestone_back(self):
        self.complete(self.steps[0])
        self.complete(self.steps[1])

        response = self.complete(self.steps[1], False)

        self.assertFalse(response.data['milestones'][0]['is_completed'])
        self.assertIsNone(response.data['milestones'][0]['completed_at'])

    def test_a_milestone_can_be_ticked_by_hand(self):
        milestone = self.plan.milestones.first()

        response = self.client.patch(f'/api/milestones/{milestone.id}/', {'is_completed': True}, format='json')

        self.assertTrue(response.data['milestones'][0]['is_completed'])

    def test_skill_mastery_reflects_completed_coverage(self):
        # "Python" appears in two steps; finishing one puts it at half mastery.
        self.complete(self.steps[0])

        skills = {s.name: s.mastery for s in SkillProgress.objects.filter(user=self.user)}
        self.assertEqual(skills['Python'], 50)
        self.assertEqual(skills['NumPy'], 100)
        self.assertEqual(skills['Neural Networks'], 0)

    def test_deleting_a_plan_clears_its_skills(self):
        self.complete(self.steps[0])

        self.assertEqual(self.client.delete(f'/api/plans/{self.plan.id}/').status_code, 204)
        self.assertFalse(SkillProgress.objects.filter(user=self.user).exists())

    def test_another_learner_cannot_touch_these_steps(self):
        other = User.objects.create_user(username='other@example.com', email='other@example.com', password='Str0ngPass!99')
        intruder = APIClient()
        intruder.force_authenticate(other)

        self.assertEqual(
            intruder.patch(f'/api/steps/{self.steps[0].id}/', {'is_completed': True}, format='json').status_code, 404
        )
        self.assertEqual(intruder.get(f'/api/plans/{self.plan.id}/').status_code, 404)
        self.assertEqual(intruder.delete(f'/api/plans/{self.plan.id}/').status_code, 404)


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='learner@example.com', email='learner@example.com', password='Str0ngPass!42'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_dashboard_requires_authentication(self):
        self.assertEqual(APIClient().get('/api/dashboard/').status_code, 401)

    def test_empty_dashboard_nudges_the_learner_to_chat(self):
        response = self.client.get('/api/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['summary']['total_steps'], 0)
        self.assertEqual(response.data['summary']['percent_complete'], 0)
        self.assertEqual(response.data['next_actions'][0]['kind'], 'chat')

    def test_dashboard_aggregates_progress_skills_and_milestones(self):
        plan = create_plan_from_roadmap(self.user, ROADMAP)
        steps = list(plan.steps.all())
        self.client.patch(f'/api/steps/{steps[0].id}/', {'is_completed': True}, format='json')
        self.client.patch(f'/api/steps/{steps[1].id}/', {'is_completed': True}, format='json')

        data = self.client.get('/api/dashboard/').data

        self.assertEqual(data['summary']['percent_complete'], 50)
        self.assertEqual(data['summary']['completed_steps'], 2)
        self.assertEqual(data['summary']['milestones_completed'], 1)
        self.assertEqual(data['summary']['day_streak'], 1)
        self.assertEqual(len(data['weekly_activity']), 8)
        self.assertEqual(data['weekly_activity'][-1]['completed'], 2)
        self.assertEqual({s['name'] for s in data['skills']} & {'Python', 'NumPy'}, {'Python', 'NumPy'})

    def test_next_action_points_at_the_first_unfinished_step(self):
        plan = create_plan_from_roadmap(self.user, ROADMAP)
        first_step = plan.steps.first()
        self.client.patch(f'/api/steps/{first_step.id}/', {'is_completed': True}, format='json')

        data = self.client.get('/api/dashboard/').data

        self.assertEqual(data['next_actions'][0]['kind'], 'step')
        self.assertEqual(data['next_actions'][0]['title'], 'Math for ML')

    def test_an_archived_plan_stops_producing_next_actions(self):
        plan = create_plan_from_roadmap(self.user, ROADMAP)

        self.client.patch(f'/api/plans/{plan.id}/', {'is_active': False}, format='json')
        data = self.client.get('/api/dashboard/').data

        self.assertEqual(data['summary']['active_plans'], 0)
        self.assertNotIn('step', [action['kind'] for action in data['next_actions']])

    def test_dashboards_do_not_leak_between_learners(self):
        other = User.objects.create_user(username='other@example.com', email='other@example.com', password='Str0ngPass!99')
        create_plan_from_roadmap(other, ROADMAP)

        data = self.client.get('/api/dashboard/').data

        self.assertEqual(data['summary']['total_plans'], 0)
        self.assertEqual(data['skills'], [])
