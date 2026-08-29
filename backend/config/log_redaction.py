"""Log formatting that cannot leak a credential.

Provider errors are logged with their traceback, and a traceback can carry a
request URL, a header dump or a quota message from a third party. Redacting at
the formatter means every record -- message, arguments and traceback alike --
passes through one scrubber, instead of relying on each call site to remember.
"""

import logging
import re

REDACTED = '[REDACTED]'

# Shapes that identify a credential on sight, so a token this process was never
# configured with -- one echoed back by a provider, say -- is caught too.
SECRET_PATTERNS = (
    (re.compile(r'AIza[0-9A-Za-z_-]{10,}'), REDACTED),                  # Google API keys
    (re.compile(r'gsk_[0-9A-Za-z_-]{10,}'), REDACTED),                  # Groq API keys
    (re.compile(r'sk-[0-9A-Za-z_-]{16,}'), REDACTED),                   # OpenAI-style keys
    # A labelled value: keep the label, drop the value.
    (
        re.compile(
            r'(?i)(authorization|x-api-key|x-goog-api-key|api[-_]?key|token)'
            r'(["\']?\s*[:=]\s*["\']?)'
            r'([^"\'\s,}\])]+)'
        ),
        r'\1\2' + REDACTED,
    ),
    (re.compile(r'(?i)([?&](?:key|api_key|access_token)=)[^&\s]+'), r'\1' + REDACTED),
)


def _configured_secrets():
    """The credentials this process actually holds, longest first."""
    from django.conf import settings

    secrets = {
        getattr(settings, name, '')
        for name in ('GEMINI_API_KEY', 'GROQ_API_KEY', 'SERPER_API_KEY', 'SECRET_KEY')
    }
    # Very short values would match everywhere and are not real credentials.
    return sorted(
        (secret for secret in secrets if isinstance(secret, str) and len(secret) >= 8),
        key=len,
        reverse=True,
    )


def redact(text):
    if not text:
        return text
    for secret in _configured_secrets():
        text = text.replace(secret, REDACTED)
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactingFormatter(logging.Formatter):
    def format(self, record):
        return redact(super().format(record))