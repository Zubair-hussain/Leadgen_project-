"""One-time Gmail OAuth: opens Google's consent screen and prints a refresh token.

Run on your PC (not inside Docker), because Google redirects the browser back
to http://127.0.0.1:<port>/:

    python manage.py gmail_authorize --write-env
"""
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from outreach import gmail


class _CallbackHandler(BaseHTTPRequestHandler):
    result = {}

    def do_GET(self):  # noqa: N802 (http.server naming)
        params = parse_qs(urlparse(self.path).query)
        _CallbackHandler.result = {key: values[0] for key, values in params.items()}
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"<h2>Done. You can close this tab and return to the terminal.</h2>")

    def log_message(self, *args):
        pass


def write_env(path, key, value):
    lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
    replaced = False
    for index, line in enumerate(lines):
        if line.startswith(f'{key}='):
            lines[index] = f'{key}={value}'
            replaced = True
    if not replaced:
        lines.append(f'{key}={value}')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


class Command(BaseCommand):
    help = "Authorise the outreach Gmail account and obtain GOOGLE_REFRESH_TOKEN."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('--port', type=int, default=8765)
        parser.add_argument('--write-env', action='store_true',
                            help="Save the refresh token into backend/.env")

    def handle(self, *args, **options):
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise CommandError("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env first.")

        redirect_uri = f"http://127.0.0.1:{options['port']}/"
        state = secrets.token_urlsafe(16)
        url = gmail.AUTH_URL + '?' + urlencode({
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(gmail.SCOPES),
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state,
        })

        self.stdout.write("Opening Google sign-in. If it doesn't open, paste this URL into your browser:\n")
        self.stdout.write(url + "\n")
        webbrowser.open(url)

        server = HTTPServer(('127.0.0.1', options['port']), _CallbackHandler)
        server.handle_request()
        server.server_close()
        result = _CallbackHandler.result

        if result.get('state') != state:
            raise CommandError("State mismatch; aborting for safety. Run the command again.")
        if 'error' in result:
            raise CommandError(f"Google returned an error: {result['error']}")

        response = requests.post(gmail.TOKEN_URL, data={
            'code': result.get('code', ''),
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }, timeout=15)
        if response.status_code != 200:
            raise CommandError(f"Token exchange failed: {response.text[:300]}")
        refresh_token = response.json().get('refresh_token')
        if not refresh_token:
            raise CommandError("Google did not return a refresh token. Remove the app's access at "
                               "myaccount.google.com/permissions and run this again.")

        if options['write_env']:
            env_path = Path(settings.BASE_DIR) / '.env'
            write_env(env_path, 'GOOGLE_REFRESH_TOKEN', refresh_token)
            self.stdout.write(self.style.SUCCESS(f"Saved GOOGLE_REFRESH_TOKEN to {env_path}"))
        else:
            self.stdout.write(self.style.SUCCESS("Add this line to backend/.env:"))
            self.stdout.write(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
