"""AI generation for the chat endpoint.

Every outbound call made here runs inside a request-handling worker, so each one
is explicitly bounded: a hard timeout, a small retry budget, and no exception
that can escape into the WSGI layer. Resource searches fan out through a small
thread pool so a roadmap with a dozen topics costs a few seconds instead of a
few minutes of worker occupancy.
"""

import json
import logging
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings
from google import genai
from google.genai import types
from groq import Groq


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are PAXIS AI (Personalized AI Exploration and Intelligent Strategy), a learning assistant.
Understand the user's goal, target skill or career, timeline, current level, and daily study time when available.
Create realistic, practical learning roadmaps broken into logical stages. Prioritize what to learn first, suggest
topics, practical projects, milestones, and the next action. Avoid unrealistic promises and ask one short
clarification question only when critical information is genuinely missing. Respond naturally in English, Hindi,
or Hinglish, matching the user's language. Keep the response concise and useful.

Return only valid JSON in this shape:
{
  "response": "concise natural-language answer",
  "roadmap": {
    "goal": "string",
    "duration": "string",
    "starting_level": "string",
    "steps": [
      {"title": "string", "duration": "string", "description": "string", "topics": ["string"]}
    ],
    "projects": ["string"],
    "milestones": ["string"],
    "next_action": "string"
  }
}
Use null for roadmap when the user has not asked for a learning path or important details are missing.
""".strip()


PROFILE_PREAMBLE = """
The learner has filled in the following profile. Treat it as their true starting point: do not re-ask for
information already given here, skip topics they have already completed, and pitch depth and pace at their
stated experience level and weekly study time. If the message contradicts the profile, trust the message.

Learner profile:
{profile}
""".strip()


STUDY_MATERIAL_PROMPT = """
Select one suitable website result and one specific YouTube video result for each roadmap topic from the
provided Serper search results. Evaluate relevance to the exact topic, learner level, clarity, credibility,
and whether the result directly teaches the topic. Use only URLs present in the supplied results. Never invent
URLs, use a homepage when a relevant page exists, or use a YouTube channel homepage. Use null when no suitable
result exists. Keep reasons short.

Return only valid JSON in this shape:
{
    "topics": [
        {
            "topic": "exact topic from the supplied results",
            "study_material": {
                "website": {"name": "string", "url": "https://...", "reason": "short reason"},
                "youtube": {"title": "string", "channel": "string", "url": "https://www.youtube.com/watch?v=...", "reason": "short reason"}
            }
        }
    ]
}

Roadmap:
""".strip()


# Generic, user-safe wording. Provider text never reaches the browser.
AI_UNAVAILABLE_MESSAGE = 'The learning assistant is temporarily unavailable. Please try again in a moment.'


class GeminiConfigurationError(Exception):
    pass


class GeminiResponseError(Exception):
    pass


class GroqConfigurationError(Exception):
    pass


class GroqResponseError(Exception):
    pass


class SerperConfigurationError(Exception):
    """Raised when a Serper search is attempted without an API key."""


def build_system_prompt(profile_context=''):
    """SYSTEM_PROMPT, with the profiling-engine record prepended when present."""
    profile_context = (profile_context or '').strip()
    if not profile_context:
        return SYSTEM_PROMPT
    return '\n\n'.join([PROFILE_PREAMBLE.format(profile=profile_context), SYSTEM_PROMPT])


def _int_setting(name, default):
    """A positive integer setting, falling back to the default when unusable."""
    try:
        value = int(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _float_setting(name, default):
    """A positive float setting, falling back to the default when unusable."""
    try:
        value = float(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


# ---------------------------------------------------------------------------
# Provider clients
#
# Each client owns an HTTP connection pool. Building one per request leaked a
# pool per chat turn, which is what let memory creep up until the platform
# killed the worker. A single-slot cache keyed on the effective configuration
# reuses one client per process and rebuilds only when that configuration (or,
# under test, the patched constructor) actually changes.
# ---------------------------------------------------------------------------

_client_lock = threading.Lock()
_gemini_cache = {'key': None, 'client': None}
_groq_cache = {'key': None, 'client': None}


def reset_ai_clients():
    """Drop the cached provider clients. Used by tests and after a config change."""
    with _client_lock:
        _gemini_cache.update(key=None, client=None)
        _groq_cache.update(key=None, client=None)


def _gemini_http_options():
    return types.HttpOptions(
        timeout=_int_setting('GEMINI_TIMEOUT_MS', 45000),
        # The SDK retries five times with exponential backoff by default, so a
        # throttled provider could hold a worker for minutes before we ever got
        # the chance to fall back to Groq. Keep the budget small and fail over.
        retry_options=types.HttpRetryOptions(
            attempts=_int_setting('GEMINI_RETRY_ATTEMPTS', 2),
            initial_delay=_float_setting('GEMINI_RETRY_INITIAL_DELAY', 0.5),
            max_delay=_float_setting('GEMINI_RETRY_MAX_DELAY', 4.0),
        ),
    )


def _gemini_client():
    http_options = _gemini_http_options()
    key = (
        id(genai.Client),
        settings.GEMINI_API_KEY,
        http_options.timeout,
        http_options.retry_options.attempts,
    )
    with _client_lock:
        if _gemini_cache['key'] != key:
            _gemini_cache['client'] = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=http_options,
            )
            _gemini_cache['key'] = key
        return _gemini_cache['client']


def _groq_client():
    timeout = _float_setting('GROQ_TIMEOUT_SECONDS', 30.0)
    attempts = _int_setting('GROQ_RETRY_ATTEMPTS', 1)
    key = (id(Groq), settings.GROQ_API_KEY, timeout, attempts)
    with _client_lock:
        if _groq_cache['key'] != key:
            _groq_cache['client'] = Groq(
                api_key=settings.GROQ_API_KEY,
                timeout=timeout,
                max_retries=max(attempts - 1, 0),
            )
            _groq_cache['key'] = key
        return _groq_cache['client']


# ---------------------------------------------------------------------------
# Response validation
# ---------------------------------------------------------------------------

def _parse_provider_response(response_text, provider):
    response_text = (response_text or '').strip()
    if not response_text:
        raise GeminiResponseError(f'{provider} returned an empty response.')

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise GeminiResponseError(f'{provider} returned an invalid structured response.') from exc

    if not isinstance(payload, dict) or not isinstance(payload.get('response'), str):
        raise GeminiResponseError(f'{provider} returned an incomplete structured response.')

    roadmap = payload.get('roadmap')
    if roadmap is not None and not isinstance(roadmap, dict):
        raise GeminiResponseError(f'{provider} returned an invalid roadmap.')
    return payload['response'].strip(), roadmap


def _valid_resource(resource, resource_type):
    if not isinstance(resource, dict):
        return None
    url = resource.get('url')
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return None
    required_fields = ('name', 'reason') if resource_type == 'website' else ('title', 'channel', 'reason')
    if any(not isinstance(resource.get(field), str) or not resource[field].strip() for field in required_fields):
        return None
    if resource_type == 'youtube' and 'youtube.com/watch?' not in url and 'youtu.be/' not in url:
        return None
    return {field: resource[field].strip() for field in (*required_fields, 'url')}


def _safe_exception_detail(exc):
    """str(exc) with any provider credential scrubbed, for server-side logs only."""
    detail = str(exc)
    for secret in (
        getattr(settings, 'GEMINI_API_KEY', ''),
        getattr(settings, 'GROQ_API_KEY', ''),
        getattr(settings, 'SERPER_API_KEY', ''),
    ):
        if secret:
            detail = detail.replace(secret, '[REDACTED]')
    return re.sub(r'(AIza[0-9A-Za-z_-]+|gsk_[0-9A-Za-z_-]+)', '[REDACTED]', detail)


def _is_temporary_gemini_error(exc):
    """True when the failure looks transient and Groq is worth trying."""
    status_code = getattr(exc, 'status_code', None) or getattr(exc, 'code', None)
    if hasattr(status_code, 'value'):
        status_code = status_code.value
    if isinstance(status_code, int) and (status_code == 429 or 500 <= status_code <= 599):
        return True

    error_name = type(exc).__name__.lower()
    temporary_names = (
        'ratelimit',
        'resourceexhausted',
        'toomanyrequests',
        'serviceunavailable',
        'servererror',
        'internalserver',
        'deadlineexceeded',
        'timeout',
        'connection',
        'connecterror',
        'readerror',
        'remoteprotocol',
    )
    return isinstance(exc, (ConnectionError, TimeoutError, socket.timeout)) or any(
        name in error_name for name in temporary_names
    )


# ---------------------------------------------------------------------------
# Serper resource search
# ---------------------------------------------------------------------------

SERPER_ENDPOINTS = {
    'search': 'https://google.serper.dev/search',
    'videos': 'https://google.serper.dev/videos',
}
_SERPER_FIELDS = {
    'search': ('title', 'link', 'snippet'),
    'videos': ('title', 'link', 'channel', 'snippet'),
}
_SNIPPET_LIMIT = 240


def _serper_search(query, search_type):
    """One Serper call. Raises on a missing key, a timeout, or an HTTP error."""
    if not settings.SERPER_API_KEY:
        raise SerperConfigurationError('Serper API key is not configured.')

    response = requests.post(
        SERPER_ENDPOINTS.get(search_type, SERPER_ENDPOINTS['search']),
        headers={'X-API-KEY': settings.SERPER_API_KEY, 'Content-Type': 'application/json'},
        json={'q': query, 'num': _int_setting('SERPER_RESULTS_PER_QUERY', 5)},
        timeout=_float_setting('SERPER_TIMEOUT_SECONDS', 8.0),
    )
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError:
        return []
    if not isinstance(data, dict):
        return []

    results = data.get('videos' if search_type == 'videos' else 'organic', [])
    if not isinstance(results, list):
        return []

    fields = _SERPER_FIELDS.get(search_type, _SERPER_FIELDS['search'])
    trimmed = []
    for result in results:
        if not isinstance(result, dict) or not result.get('link'):
            continue
        entry = {}
        for key in fields:
            value = result.get(key)
            if not value:
                continue
            # Snippets are the bulk of the selection prompt; cap them so a long
            # roadmap cannot balloon the request body (and the worker's memory).
            entry[key] = value[:_SNIPPET_LIMIT] if key == 'snippet' and isinstance(value, str) else value
        trimmed.append(entry)
    return trimmed


def _safe_serper_search(query, search_type):
    """_serper_search that reports failure instead of raising, for pool workers.

    Returns (results, error_label); error_label is None on success.
    """
    started = time.monotonic()
    try:
        results = _serper_search(query, search_type)
    except SerperConfigurationError:
        return [], 'not-configured'
    except requests.Timeout:
        logger.warning('[serper] type=%s outcome=timeout duration=%.2fs', search_type, time.monotonic() - started)
        return [], 'timeout'
    except requests.HTTPError as exc:
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        logger.warning(
            '[serper] type=%s outcome=http-error status=%s duration=%.2fs',
            search_type, status, time.monotonic() - started,
        )
        return [], f'http-{status}'
    except Exception as exc:
        logger.warning(
            '[serper] type=%s outcome=error error=%s detail=%s duration=%.2fs',
            search_type, type(exc).__name__, _safe_exception_detail(exc), time.monotonic() - started,
        )
        return [], type(exc).__name__
    logger.debug(
        '[serper] type=%s outcome=ok results=%d duration=%.2fs',
        search_type, len(results), time.monotonic() - started,
    )
    return results, None


def _roadmap_topics(roadmap):
    """Distinct topics across every step, in roadmap order.

    Steps often repeat a topic; searching it twice buys nothing and costs two
    more outbound calls, so duplicates are collapsed case-insensitively.
    """
    topics = []
    seen = set()
    steps = roadmap.get('steps') if isinstance(roadmap.get('steps'), list) else []
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_topics = step.get('topics') if isinstance(step.get('topics'), list) else [step.get('title')]
        for topic in step_topics or []:
            if not isinstance(topic, str) or not topic.strip():
                continue
            key = topic.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            topics.append(topic.strip())
    return topics


def _search_topics_concurrently(topics, level):
    """Run every topic's web and video search through a small bounded pool.

    Two searches per topic, all independent, so they go out together instead of
    one at a time. The pool is deliberately small: the process may be serving
    several chat turns at once and has to stay inside a modest memory and socket
    budget. Worst case is SERPER_MAX_CONCURRENCY threads per in-flight chat
    request, and the number of in-flight requests is itself capped by the
    server's thread count.
    """
    jobs = [(topic, search_type) for topic in topics for search_type in ('search', 'videos')]
    if not jobs:
        return []

    max_workers = min(_int_setting('SERPER_MAX_CONCURRENCY', 4), len(jobs))
    started = time.monotonic()
    by_topic = {}
    failures = 0

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='paxis-serper') as pool:
        submitted = {
            pool.submit(_safe_serper_search, f'{topic} {level} tutorial', search_type): (topic, search_type)
            for topic, search_type in jobs
        }
        for future, (topic, search_type) in submitted.items():
            try:
                results, error = future.result()
            except Exception as exc:  # A worker should never raise, but never trust that.
                logger.warning('[serper] outcome=worker-error error=%s', type(exc).__name__)
                results, error = [], type(exc).__name__
            if error:
                failures += 1
            bucket = by_topic.setdefault(topic, {'topic': topic, 'website_results': [], 'video_results': []})
            bucket['video_results' if search_type == 'videos' else 'website_results'] = results

    candidates = [
        by_topic[topic]
        for topic in topics
        if topic in by_topic and (by_topic[topic]['website_results'] or by_topic[topic]['video_results'])
    ]
    logger.info(
        '[serper] outcome=complete searches=%d concurrency=%d failures=%d topics_with_results=%d duration=%.2fs',
        len(jobs), max_workers, failures, len(candidates), time.monotonic() - started,
    )
    return candidates


def _select_study_material(candidates):
    """Ask Gemini to pick one site and one video per topic. Returns {} on any failure."""
    prompt = f'{STUDY_MATERIAL_PROMPT}\n{json.dumps(candidates)}'
    started = time.monotonic()
    try:
        result = _gemini_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                http_options=_gemini_http_options(),
            ),
        )
        response_text = (getattr(result, 'text', '') or '').strip()
        payload = json.loads(response_text) if response_text else None
    except Exception as exc:
        logger.warning(
            '[gemini] stage=study-material outcome=error error=%s detail=%s duration=%.2fs',
            type(exc).__name__, _safe_exception_detail(exc), time.monotonic() - started,
        )
        return {}

    selected = payload.get('topics') if isinstance(payload, dict) else None
    if not isinstance(selected, list):
        logger.warning(
            '[gemini] stage=study-material outcome=unusable-payload duration=%.2fs',
            time.monotonic() - started,
        )
        return {}

    by_topic = {}
    for item in selected:
        if not isinstance(item, dict) or not isinstance(item.get('topic'), str):
            continue
        material = item.get('study_material')
        if not isinstance(material, dict):
            continue
        website = _valid_resource(material.get('website'), 'website')
        youtube = _valid_resource(material.get('youtube'), 'youtube')
        if website or youtube:
            by_topic[item['topic'].strip().lower()] = {'website': website, 'youtube': youtube}
    logger.info(
        '[gemini] stage=study-material outcome=ok topics_selected=%d duration=%.2fs',
        len(by_topic), time.monotonic() - started,
    )
    return by_topic


def _attach_study_material(roadmap, selected_by_topic):
    """A copy of the roadmap with topic_materials added to each step that has any."""
    enriched_roadmap = dict(roadmap)
    enriched_steps = []
    for step in roadmap.get('steps') or []:
        if not isinstance(step, dict):
            enriched_steps.append(step)
            continue
        enriched_step = dict(step)
        topics = step.get('topics') if isinstance(step.get('topics'), list) else [step.get('title')]
        topic_materials = []
        for topic in topics or []:
            if not isinstance(topic, str) or not topic.strip():
                continue
            material = selected_by_topic.get(topic.strip().lower())
            if material:
                topic_materials.append({'topic': topic, 'study_material': material})
        if topic_materials:
            enriched_step['topic_materials'] = topic_materials
        enriched_steps.append(enriched_step)
    enriched_roadmap['steps'] = enriched_steps
    return enriched_roadmap


def enrich_roadmap_with_study_material(roadmap):
    """Yield status updates, then exactly one {'roadmap': ...}.

    Always yields one roadmap chunk, so a partial or total resource failure
    downgrades to the un-enriched roadmap instead of failing the turn.
    """
    if not settings.SERPER_API_KEY:
        yield {'roadmap': roadmap}
        return

    topics = _roadmap_topics(roadmap)
    max_topics = _int_setting('SERPER_MAX_TOPICS', 12)
    if len(topics) > max_topics:
        logger.info(
            '[serper] outcome=topics-capped requested=%d searched=%d skipped=%d',
            len(topics), max_topics, len(topics) - max_topics,
        )
        topics = topics[:max_topics]
    if not topics:
        yield {'roadmap': roadmap}
        return

    yield {'status': f'Finding study material for {len(topics)} topics...'}
    started = time.monotonic()
    candidates = _search_topics_concurrently(topics, roadmap.get('starting_level') or 'beginner')
    if not candidates:
        logger.info('[enrichment] outcome=no-candidates duration=%.2fs', time.monotonic() - started)
        yield {'roadmap': roadmap}
        return

    yield {'status': 'Analyzing study materials...'}
    selected_by_topic = _select_study_material(candidates)
    if not selected_by_topic:
        logger.info('[enrichment] outcome=nothing-selected duration=%.2fs', time.monotonic() - started)
        yield {'roadmap': roadmap}
        return

    logger.info('[enrichment] outcome=ok duration=%.2fs', time.monotonic() - started)
    yield {'roadmap': _attach_study_material(roadmap, selected_by_topic)}


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

def _provider_history(message, conversation_history):
    if not conversation_history:
        return message
    return [
        {'role': 'user' if item.role == 'user' else 'model', 'parts': [{'text': item.message}]}
        for item in conversation_history
    ] + [{'role': 'user', 'parts': [{'text': message}]}]


def _groq_messages(message, conversation_history, system_prompt=None):
    messages = [{'role': 'system', 'content': system_prompt or SYSTEM_PROMPT}]
    messages.extend(
        {'role': item.role, 'content': item.message}
        for item in conversation_history or []
    )
    messages.append({'role': 'user', 'content': message})
    return messages


def _generate_groq_response(message, conversation_history=None, system_prompt=None):
    if not settings.GROQ_API_KEY:
        raise GroqConfigurationError('Groq API key is not configured. Set GROQ_API_KEY in .env.')
    if not settings.GROQ_MODEL:
        raise GroqConfigurationError('Groq model is not configured. Set GROQ_MODEL in .env.')

    started = time.monotonic()
    try:
        result = _groq_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=_groq_messages(message, conversation_history, system_prompt),
            response_format={'type': 'json_object'},
        )
    except Exception as exc:
        logger.error(
            '[groq] outcome=error error=%s detail=%s duration=%.2fs',
            type(exc).__name__, _safe_exception_detail(exc), time.monotonic() - started,
        )
        raise GroqResponseError('The fallback AI service is temporarily unavailable.') from exc

    try:
        response_text = result.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise GroqResponseError('Groq returned an incomplete structured response.') from exc

    try:
        parsed = _parse_provider_response(response_text, 'Groq')
    except GeminiResponseError as exc:
        logger.error('[groq] outcome=unparsable duration=%.2fs', time.monotonic() - started)
        raise GroqResponseError(str(exc)) from exc
    logger.info('[groq] outcome=ok model=%s duration=%.2fs', settings.GROQ_MODEL, time.monotonic() - started)
    return parsed


def _generate_gemini_response(message, conversation_history, system_prompt):
    """The primary provider.

    Streamed internally only so the SDK reads the body incrementally instead of
    buffering the whole thing at once; the chunks are joined and validated as a
    single JSON document before anything is handed back, because the frontend
    needs a complete roadmap, never partial JSON.
    """
    started = time.monotonic()
    chunks = []
    for chunk in _gemini_client().models.generate_content_stream(
        model=settings.GEMINI_MODEL,
        contents=_provider_history(message, conversation_history),
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type='application/json',
            http_options=_gemini_http_options(),
        ),
    ):
        text = getattr(chunk, 'text', None)
        if text:
            chunks.append(text)

    parsed = _parse_provider_response(''.join(chunks), 'Gemini')
    logger.info(
        '[gemini] stage=core outcome=ok model=%s duration=%.2fs',
        settings.GEMINI_MODEL, time.monotonic() - started,
    )
    return parsed


def generate_learning_response(message, conversation_history=None, profile_context=''):
    """Yield SSE-shaped chunks: {'status'}, then {'response'}, then {'roadmap'}.

    Raises only configuration or provider errors, which the view turns into a
    single SSE error event. Resource enrichment never raises out of here.
    """
    if not settings.GEMINI_API_KEY:
        raise GeminiConfigurationError('Gemini API key is not configured. Set GEMINI_API_KEY in .env.')
    if not settings.GEMINI_MODEL:
        raise GeminiConfigurationError('Gemini model is not configured. Set GEMINI_MODEL in .env.')

    system_prompt = build_system_prompt(profile_context)

    yield {'status': 'Analyzing...'}

    try:
        response, roadmap = _generate_gemini_response(message, conversation_history, system_prompt)
    except Exception as exc:
        logger.warning(
            '[gemini] stage=core outcome=error error=%s detail=%s',
            type(exc).__name__, _safe_exception_detail(exc),
        )
        if not _is_temporary_gemini_error(exc):
            raise
        logger.warning('[chat] provider=gemini outcome=unavailable action=falling-back-to-groq')
        try:
            response, roadmap = _generate_groq_response(message, conversation_history, system_prompt)
        except Exception as fallback_exc:
            raise GroqResponseError(AI_UNAVAILABLE_MESSAGE) from fallback_exc
        # Groq has no resource-search stage here, so hand its roadmap back as
        # generated rather than leaving the frontend without one.
        yield {'response': response, 'roadmap': roadmap}
        return

    logger.info('[chat] provider=gemini outcome=core-response-ready has_roadmap=%s', bool(roadmap))

    # The conversational answer goes out before any resource search, so the
    # learner sees the reply without waiting for enrichment.
    yield {'response': response}

    if not roadmap:
        yield {'roadmap': None}
        return

    # Then the bare roadmap, so the panel renders while resources are gathered.
    yield {'roadmap': roadmap}
    try:
        yield from enrich_roadmap_with_study_material(roadmap)
    except Exception as exc:
        logger.warning(
            '[enrichment] outcome=error error=%s detail=%s; returning roadmap without materials.',
            type(exc).__name__, _safe_exception_detail(exc),
        )
        yield {'roadmap': roadmap}
