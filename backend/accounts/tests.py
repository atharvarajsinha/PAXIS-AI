from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import LearnerProfile

User = get_user_model()


class RegistrationTests(TestCase):
    def test_register_returns_a_token_and_creates_a_profile(self):
        response = APIClient().post(
            '/api/auth/register/',
            {'email': 'New.Learner@Example.com', 'password': 'Str0ngPass!42', 'full_name': 'New Learner'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['email'], 'new.learner@example.com')
        user = User.objects.get(email='new.learner@example.com')
        self.assertEqual(user.username, 'new.learner@example.com')
        self.assertTrue(user.check_password('Str0ngPass!42'))
        self.assertEqual(user.learner_profile.full_name, 'New Learner')

    def test_duplicate_email_is_rejected_regardless_of_case(self):
        User.objects.create_user(username='taken@example.com', email='taken@example.com', password='Str0ngPass!42')

        response = APIClient().post(
            '/api/auth/register/', {'email': 'TAKEN@example.com', 'password': 'Str0ngPass!99'}, format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(email__iexact='taken@example.com').count(), 1)

    def test_weak_passwords_are_rejected(self):
        for password in ['12345678', 'password', 'short']:
            with self.subTest(password=password):
                response = APIClient().post(
                    '/api/auth/register/', {'email': f'{password}@example.com', 'password': password}, format='json'
                )
                self.assertEqual(response.status_code, 400)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='learner@example.com', email='learner@example.com', password='Str0ngPass!42'
        )

    def test_login_with_correct_credentials_returns_a_token(self):
        response = APIClient().post(
            '/api/auth/login/', {'email': 'Learner@Example.com', 'password': 'Str0ngPass!42'}, format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['token'], Token.objects.get(user=self.user).key)

    def test_wrong_password_and_unknown_email_are_indistinguishable(self):
        wrong = APIClient().post(
            '/api/auth/login/', {'email': 'learner@example.com', 'password': 'nope'}, format='json'
        )
        unknown = APIClient().post(
            '/api/auth/login/', {'email': 'ghost@example.com', 'password': 'nope'}, format='json'
        )

        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(wrong.data, unknown.data)

    def test_inactive_account_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()

        response = APIClient().post(
            '/api/auth/login/', {'email': 'learner@example.com', 'password': 'Str0ngPass!42'}, format='json'
        )

        self.assertEqual(response.status_code, 400)

    def test_logout_invalidates_the_token(self):
        token = Token.objects.create(user=self.user).key
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        self.assertEqual(client.post('/api/auth/logout/').status_code, 204)
        self.assertEqual(client.get('/api/auth/me/').status_code, 401)

    def test_password_change_rotates_the_token(self):
        old_token = Token.objects.create(user=self.user).key
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {old_token}')

        response = client.post(
            '/api/auth/password/',
            {'current_password': 'Str0ngPass!42', 'new_password': 'Even5tronger!'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data['token'], old_token)
        stale = APIClient()
        stale.credentials(HTTP_AUTHORIZATION=f'Token {old_token}')
        self.assertEqual(stale.get('/api/auth/me/').status_code, 401)

    def test_password_change_requires_the_current_password(self):
        client = APIClient()
        client.force_authenticate(self.user)

        response = client.post(
            '/api/auth/password/',
            {'current_password': 'wrong', 'new_password': 'Even5tronger!'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)


class LearnerProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='learner@example.com', email='learner@example.com', password='Str0ngPass!42'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_profile_requires_authentication(self):
        self.assertEqual(APIClient().get('/api/profile/').status_code, 401)

    def test_profile_round_trips_and_deduplicates_list_fields(self):
        response = self.client.put(
            '/api/profile/',
            {
                'full_name': 'Learner One',
                'headline': 'CS undergrad',
                'experience_level': 'intermediate',
                'weekly_hours': 12,
                'interests': ['Machine Learning', ' Python ', 'Machine Learning', ''],
                'objectives': ['Land an ML internship'],
                'completed_courses': ['CS50x'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['interests'], ['Machine Learning', 'Python'])
        self.assertEqual(response.data['completeness'], 100)

    def test_invalid_profile_values_are_rejected(self):
        cases = [
            {'weekly_hours': 500},
            {'interests': 'not a list'},
            {'objectives': [1, 2, 3]},
            {'experience_level': 'wizard'},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.patch('/api/profile/', payload, format='json').status_code, 400)

    def test_completeness_grows_as_fields_are_filled(self):
        profile = self.user.learner_profile
        self.assertLess(profile.completeness(), 100)

        profile.full_name = 'Learner One'
        profile.interests = ['Python']
        profile.objectives = ['Get a job']
        profile.completed_courses = ['CS50x']
        profile.save()

        self.assertEqual(profile.completeness(), 100)

    def test_prompt_context_summarises_the_profile(self):
        profile = self.user.learner_profile
        profile.experience_level = 'advanced'
        profile.weekly_hours = 20
        profile.interests = ['Rust']
        profile.completed_courses = ['CS50x']
        profile.save()

        context = profile.as_prompt_context()

        self.assertIn('Experience level: Advanced', context)
        self.assertIn('20 hours per week', context)
        self.assertIn('Interests: Rust', context)
        self.assertIn('Already completed: CS50x', context)

    def test_a_profile_is_created_for_every_new_user(self):
        user = User.objects.create_user(username='auto@example.com', email='auto@example.com', password='Str0ngPass!42')

        self.assertTrue(LearnerProfile.objects.filter(user=user).exists())

    def test_learners_cannot_read_each_others_profiles(self):
        other = User.objects.create_user(username='other@example.com', email='other@example.com', password='Str0ngPass!99')
        other.learner_profile.full_name = 'Someone Else'
        other.learner_profile.save()

        self.assertNotEqual(self.client.get('/api/profile/').data['full_name'], 'Someone Else')
