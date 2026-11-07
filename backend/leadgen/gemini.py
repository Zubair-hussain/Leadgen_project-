"""Tiny Gemini REST client (no SDK dependency, easy to mock)."""
import json
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'


class GeminiError(Exception):
    """Gemini is unavailable, misconfigured, or returned something unusable."""


def is_configured():
    return bool(settings.GEMINI_API_KEY)


def generate(prompt, json_output=False, temperature=0.4, timeout=60):
    """Return Gemini's text answer. With json_output=True, return parsed JSON."""
    if not settings.GEMINI_API_KEY:
        raise GeminiError('GEMINI_API_KEY is not set.')
    config = {'temperature': temperature, 'thinkingConfig': {'thinkingBudget': 0}}
    if json_output:
        config['responseMimeType'] = 'application/json'
    try:
        response = requests.post(
            URL.format(model=settings.GEMINI_MODEL),
            headers={'x-goog-api-key': settings.GEMINI_API_KEY},
            json={'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': config},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise GeminiError(f'Gemini request failed: {exc}') from exc
    if response.status_code != 200:
        raise GeminiError(f'Gemini returned {response.status_code}: {response.text[:200]}')
    try:
        text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except (KeyError, IndexError, ValueError) as exc:
        raise GeminiError('Gemini returned no usable text.') from exc
    if not json_output:
        return text
    try:
        return json.loads(re.sub(r'^```(?:json)?|```$', '', text, flags=re.MULTILINE).strip())
    except ValueError as exc:
        raise GeminiError('Gemini did not return valid JSON.') from exc
