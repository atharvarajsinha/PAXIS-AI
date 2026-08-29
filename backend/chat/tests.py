import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from .models import ChatMessage, Conversation
from .services import build_system_prompt, generate_learning_response

User = get_user_model()


def drain(generator):
    """Collapse the streaming generator into the final (response, roadmap) pair."""
    response, roadmap = None, None
    for chunk in generator:
        if 'response' in chunk:
            response = chunk['response']
        if 'roadmap' in chunk:
            roadmap = chunk['roadmap']
    return response, roadmap


def read_stream(http_response):
    """Collapse an SSE StreamingHttpResponse into the merged payload it sent."""
    payload = {}
    body = b''.join(http_response.streaming_content).decode('utf-8')
    for block in body.split('\n\n'):
        for line in block.splitlines():
            if line.startswith('data: '):
                raw = line[len('data: '):].strip()
                if raw:
                    payload.update(json.loads(raw))
    return payload


@override_settings(
    GEMINI_API_KEY='gemini-test-key',
    GEMINI_MODEL='gemini-test-model',
    GROQ_API_KEY='groq-test-key',
    GROQ_MODEL='groq-test-model',
    SERPER_API_KEY='',
    DEBUG=False,
)
class ProviderFallbackTests(SimpleTestCase):
    gemini_payload = '{"response":"Gemini response","roadmap":null}'
    groq_payload = '{"response":"Groq response","roadmap":{"goal":"Python"}}'

    def make_gemini_client(self, response_text=None, error=None):
        client = Mock()
        if error:
            client.models.generate_content.side_effect = error
        else:
            client.models.generate_content.return_value = SimpleNamespace(text=response_text)
        return client

    def make_groq_client(self, response_text=None, error=None):
        client = Mock()
        if error:
            client.chat.completions.create.side_effect = error
        else:
            client.chat.completions.create.return_value = SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=response_text))]
            )
        return client

    @patch('chat.services.Groq')
    @patch('chat.services.genai.Client')
    def test_gemini_success_does_not_call_groq(self, gemini_client, groq_client):
        gemini_client.return_value = self.make_gemini_client(self.gemini_payload)

        self.assertEqual(drain(generate_learning_response('Create a roadmap.')), ('Gemini response', None))
        gemini_client.assert_called_once()
        groq_client.assert_not_called()

    @patch('chat.services.Groq')
    @patch('chat.services.genai.Client')
    def test_rate_limit_uses_groq_fallback_with_history(self, gemini_client, groq_client):
        error = RuntimeError('rate limited')
        error.status_code = 429
        gemini_client.return_value = self.make_gemini_client(error=error)
        groq_client.return_value = self.make_groq_client(self.groq_payload)
        history = [SimpleNamespace(role='user', message='I want to become a Java developer.')]

        result = drain(generate_learning_response('Current exp 0', history))

        self.assertEqual(result, ('Groq response', {'goal': 'Python'}))
        groq_client.assert_called_once()
        groq_messages = groq_client.return_value.chat.completions.create.call_args.kwargs['messages']
        self.assertEqual(groq_messages[1]['content'], 'I want to become a Java developer.')
        self.assertEqual(groq_messages[-1]['content'], 'Current exp 0')

    @patch('chat.services.Groq')
    @patch('chat.services.genai.Client')
    def test_server_error_uses_groq_fallback(self, gemini_client, groq_client):
        error = RuntimeError('server error')
        error.status_code = 503
        gemini_client.return_value = self.make_gemini_client(error=error)
        groq_client.return_value = self.make_groq_client(self.groq_payload)

        self.assertEqual(drain(generate_learning_response('Create a roadmap.'))[0], 'Groq response')
        groq_client.assert_called_once()

    @patch('chat.services.Groq')
    @patch('chat.services.genai.Client')
    def test_timeout_uses_groq_fallback(self, gemini_client, groq_client):
        gemini_client.return_value = self.make_gemini_client(error=TimeoutError())
        groq_client.return_value = self.make_groq_client(self.groq_payload)

        self.assertEqual(drain(generate_learning_response('Create a roadmap.'))[0], 'Groq response')
        groq_client.assert_called_once()

    @patch('chat.services.genai.Client')
    def test_multi_turn_history_is_sent_to_gemini(self, gemini_client):
        gemini_client.return_value = self.make_gemini_client(self.gemini_payload)
        history = [
            SimpleNamespace(role='user', message='I want to become a Java developer.'),
            SimpleNamespace(role='assistant', message='What is your current experience?'),
        ]

        drain(generate_learning_response('Current exp 0', history))

        contents = gemini_client.return_value.models.generate_content.call_args.kwargs['contents']
        self.assertEqual(contents[0]['parts'][0]['text'], 'I want to become a Java developer.')
        self.assertEqual(contents[1]['role'], 'model')
        self.assertEqual(contents[-1]['parts'][0]['text'], 'Current exp 0')

    @patch('chat.services.genai.Client')
    def test_separate_conversation_history_is_not_mixed(self, gemini_client):
        gemini_client.return_value = self.make_gemini_client(self.gemini_payload)

        drain(generate_learning_response('Current exp 0', [SimpleNamespace(role='user', message='Java developer')]))
        drain(generate_learning_response('Current exp 0', [SimpleNamespace(role='user', message='Data analyst')]))

        calls = gemini_client.return_value.models.generate_content.call_args_list
        self.assertEqual(calls[0].kwargs['contents'][0]['parts'][0]['text'], 'Java developer')
        self.assertEqual(calls[1].kwargs['contents'][0]['parts'][0]['text'], 'Data analyst')
        self.assertNotIn('Java developer', str(calls[1].kwargs['contents']))

    @patch('chat.services.genai.Client')
    def test_learner_profile_is_added_to_the_system_instruction(self, gemini_client):
        gemini_client.return_value = self.make_gemini_client(self.gemini_payload)

        drain(generate_learning_response(
            'Create a roadmap.',
            profile_context='Experience level: Advanced\nAlready completed: CS50x',
        ))

        instruction = gemini_client.return_value.models.generate_content.call_args.kwargs['config'].system_instruction
        self.assertIn('Already completed: CS50x', instruction)
        self.assertIn('PAXIS AI', instruction)

    def test_system_prompt_is_unchanged_without_a_profile(self):
        from .services import SYSTEM_PROMPT

        self.assertEqual(build_system_prompt(''), SYSTEM_PROMPT)
        self.assertEqual(build_system_prompt(None), SYSTEM_PROMPT)

    @patch('chat.services.requests.post')
    @patch('chat.services.genai.Client')
    def test_serper_results_are_evaluated_by_gemini(self, gemini_client, serper_post):
        client = Mock()
        client.models.generate_content.side_effect = [
            SimpleNamespace(text='{"response":"Roadmap ready","roadmap":{"steps":[{"title":"Java syntax","topics":["Keywords"]}]}}'),
            SimpleNamespace(text='{"topics":[{"topic":"Keywords","study_material":{"website":{"name":"Java tutorial","url":"https://example.com/java-syntax","reason":"Covers Java syntax with examples."},"youtube":{"title":"Java Syntax Tutorial","channel":"Learning Channel","url":"https://www.youtube.com/watch?v=abc123","reason":"Explains syntax for beginners."}}}]}'),
        ]
        gemini_client.return_value = client
        serper_post.side_effect = [
            Mock(status_code=200, json=lambda: {'organic': [{'title': 'Java syntax', 'link': 'https://example.com/java-syntax', 'snippet': 'Java syntax tutorial'}]}),
            Mock(status_code=200, json=lambda: {'videos': [{'title': 'Java Syntax Tutorial', 'link': 'https://www.youtube.com/watch?v=abc123', 'channel': 'Learning Channel', 'snippet': 'Java syntax tutorial'}]}),
        ]

        with patch('chat.services.settings.SERPER_API_KEY', 'serper-test-key'):
            response, roadmap = drain(generate_learning_response('Create a Java roadmap.'))

        self.assertEqual(response, 'Roadmap ready')
        material = roadmap['steps'][0]['topic_materials'][0]['study_material']
        self.assertEqual(material['website']['url'], 'https://example.com/java-syntax')
        self.assertEqual(material['youtube']['url'], 'https://www.youtube.com/watch?v=abc123')
        selection_prompt = client.models.generate_content.call_args_list[1].kwargs['contents']
        self.assertIn('https://example.com/java-syntax', selection_prompt)
        self.assertIn('https://www.youtube.com/watch?v=abc123', selection_prompt)

    @patch('chat.services.requests.post')
    @patch('chat.services.genai.Client')
    def test_serper_failure_returns_original_roadmap(self, gemini_client, serper_post):
        client = Mock()
        client.models.generate_content.side_effect = [
            SimpleNamespace(text='{"response":"Roadmap ready","roadmap":{"steps":[{"title":"Java syntax"}]}}'),
        ]
        gemini_client.return_value = client
        serper_post.side_effect = RuntimeError('search unavailable')

        with patch('chat.services.settings.SERPER_API_KEY', 'serper-test-key'):
            response, roadmap = drain(generate_learning_response('Create a Java roadmap.'))

        self.assertEqual(response, 'Roadmap ready')
        self.assertEqual(roadmap, {'steps': [{'title': 'Java syntax'}]})

    @patch('chat.services.Groq')
    @patch('chat.services.genai.Client')
    def test_non_temporary_gemini_error_does_not_use_groq(self, gemini_client, groq_client):
        gemini_client.return_value = self.make_gemini_client(error=ValueError('invalid request'))

        with self.assertRaises(ValueError):
            drain(generate_learning_response('Create a roadmap.'))

        groq_client.assert_not_called()


@override_settings(
    GEMINI_API_KEY='gemini-test-key',
    GEMINI_MODEL='gemini-test-model',
    GROQ_API_KEY='groq-test-key',
    GROQ_MODEL='groq-test-model',
    SERPER_API_KEY='',
    DEBUG=False,
)
class ChatApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='learner@example.com', email='learner@example.com', password='Str0ngPass!42'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_chat_requires_authentication(self):
        self.assertEqual(APIClient().post('/api/chat/', {'message': 'Hi'}, format='json').status_code, 401)

    @patch('chat.views.generate_learning_response')
    def test_conversation_id_preserves_and_isolates_history(self, generate_response):
        generate_response.side_effect = [
            iter([{'response': 'Java response'}]),
            iter([{'response': 'Java follow-up'}]),
            iter([{'response': 'Python response'}]),
        ]

        first = read_stream(self.client.post('/api/chat/', {'message': 'I want Java.'}, format='json'))
        conversation_id = first['conversation_id']
        self.assertIsNotNone(conversation_id)

        read_stream(self.client.post(
            '/api/chat/',
            {'message': 'Current experience 0.', 'conversation_id': conversation_id},
            format='json',
        ))
        read_stream(self.client.post('/api/chat/', {'message': 'I want Python.'}, format='json'))

        first_history = generate_response.call_args_list[1].args[1]
        second_history = generate_response.call_args_list[2].args[1]
        self.assertEqual([message.message for message in first_history], ['I want Java.', 'Java response'])
        self.assertEqual([message.message for message in second_history], [])
        self.assertEqual(ChatMessage.objects.filter(conversation_id=conversation_id).count(), 4)

    @patch('chat.views.generate_learning_response')
    def test_assistant_roadmap_is_persisted_and_restored(self, generate_response):
        roadmap = {'goal': 'Java developer', 'steps': [{'title': 'Syntax'}]}
        generate_response.return_value = iter([{'response': 'Here you go.'}, {'roadmap': roadmap}])

        payload = read_stream(self.client.post('/api/chat/', {'message': 'Java roadmap please'}, format='json'))

        stored = ChatMessage.objects.get(conversation_id=payload['conversation_id'], role='assistant')
        self.assertEqual(stored.roadmap, roadmap)

        detail = self.client.get(f"/api/conversations/{payload['conversation_id']}/")
        self.assertEqual(detail.data['roadmap'], roadmap)
        self.assertEqual(detail.data['title'], 'Java roadmap please')

    @patch('chat.views.generate_learning_response')
    def test_learner_profile_is_passed_to_the_service(self, generate_response):
        generate_response.return_value = iter([{'response': 'ok'}])
        profile = self.user.learner_profile
        profile.interests = ['Robotics']
        profile.save()

        read_stream(self.client.post('/api/chat/', {'message': 'Hello'}, format='json'))

        self.assertIn('Robotics', generate_response.call_args.kwargs['profile_context'])

    def test_conversations_are_scoped_to_their_owner(self):
        mine = Conversation.objects.create(user=self.user, title='Mine')
        other = User.objects.create_user(username='other@example.com', email='other@example.com', password='Str0ngPass!99')
        theirs = Conversation.objects.create(user=other, title='Theirs')

        listing = self.client.get('/api/conversations/')
        self.assertEqual([c['id'] for c in listing.data], [mine.id])
        self.assertEqual(self.client.get(f'/api/conversations/{theirs.id}/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/conversations/{theirs.id}/').status_code, 404)

    def test_posting_to_another_users_conversation_is_rejected(self):
        other = User.objects.create_user(username='other2@example.com', email='other2@example.com', password='Str0ngPass!99')
        theirs = Conversation.objects.create(user=other)

        response = self.client.post('/api/chat/', {'message': 'Hi', 'conversation_id': theirs.id}, format='json')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(theirs.messages.count(), 0)

    @patch('chat.services.Groq')
    @patch('chat.services.genai.Client')
    def test_provider_failure_is_reported_without_leaking_details(self, gemini_client, groq_client):
        gemini = Mock()
        gemini.models.generate_content.side_effect = TimeoutError()
        gemini_client.return_value = gemini
        groq = Mock()
        groq.chat.completions.create.side_effect = RuntimeError('provider detail must stay hidden')
        groq_client.return_value = groq

        payload = read_stream(self.client.post('/api/chat/', {'message': 'Create a roadmap.'}, format='json'))

        self.assertIn('error', payload)
        self.assertNotIn('provider detail', payload['error'])
        # A failed turn must not leave a half-written assistant message behind.
        self.assertFalse(ChatMessage.objects.filter(role='assistant').exists())

    def test_conversations_are_listed_most_recently_updated_first(self):
        oldest = Conversation.objects.create(user=self.user, title='Oldest')
        middle = Conversation.objects.create(user=self.user, title='Middle')
        newest = Conversation.objects.create(user=self.user, title='Newest')

        listing = self.client.get('/api/conversations/')

        self.assertEqual(
            [c['id'] for c in listing.data],
            [newest.id, middle.id, oldest.id],
        )

    @patch('chat.views.generate_learning_response')
    def test_replying_in_an_old_thread_moves_it_to_the_top(self, generate_response):
        generate_response.return_value = iter([{'response': 'ok'}])
        stale = Conversation.objects.create(user=self.user, title='Stale')
        Conversation.objects.create(user=self.user, title='Fresher')

        read_stream(self.client.post(
            '/api/chat/', {'message': 'Still here?', 'conversation_id': stale.id}, format='json'
        ))

        self.assertEqual(self.client.get('/api/conversations/').data[0]['id'], stale.id)

    def test_conversation_can_be_renamed_and_deleted(self):
        conversation = Conversation.objects.create(user=self.user, title='Old title')

        renamed = self.client.patch(f'/api/conversations/{conversation.id}/', {'title': 'New title'}, format='json')
        self.assertEqual(renamed.data['title'], 'New title')

        self.assertEqual(self.client.delete(f'/api/conversations/{conversation.id}/').status_code, 204)
        self.assertFalse(Conversation.objects.filter(id=conversation.id).exists())
