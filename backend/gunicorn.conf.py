"""Gunicorn configuration tuned for a 512 MB single-CPU instance.

The chat endpoint streams Server-Sent Events, so a request can legitimately hold
its execution slot for the better part of a minute. Two properties matter:

1. Slots must be cheap. A sync worker gives one slot per *process*, and each
   process here carries Django, google-genai, groq and psycopg -- on the order of
   150-200 MB resident. Four of those is how a 512 MB instance ends up with
   "Worker was sent SIGKILL! Perhaps out of memory?". Threads give extra slots
   for a few megabytes each, and every slow call in this application is blocked
   on a socket (Gemini, Groq, Serper, Postgres), which releases the GIL. So:
   one worker, several threads.

2. A long request must not look dead. Gunicorn's --timeout is a worker
   liveness check, not a request deadline. The sync worker only reports in
   between requests, so any request slower than --timeout gets the worker
   killed; the gthread worker reports from its accept loop, so an in-flight SSE
   stream cannot trip it. The application's own budgets (GEMINI_TIMEOUT_MS,
   SERPER_TIMEOUT_SECONDS, ...) are what actually bound a chat turn.

Override anything here with the matching environment variable.
"""

import multiprocessing
import os


bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

workers = int(os.getenv('WEB_CONCURRENCY', '1'))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'gthread')
threads = int(os.getenv('GUNICORN_THREADS', '4'))

timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
graceful_timeout = int(os.getenv('GUNICORN_GRACEFUL_TIMEOUT', '30'))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', '15'))
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '400'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '50'))

accesslog = os.getenv('GUNICORN_ACCESS_LOG', '-')
errorlog = '-'
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s "%(m)s %(U)s" %(s)s %(b)s %(M)sms'

limit_request_line = 8190
limit_request_fields = 100

_cpu_count = multiprocessing.cpu_count()


def on_starting(server):
    server.log.info(
        '[gunicorn] workers=%s worker_class=%s threads=%s timeout=%ss cpus=%s',
        workers, worker_class, threads, timeout, _cpu_count,
    )