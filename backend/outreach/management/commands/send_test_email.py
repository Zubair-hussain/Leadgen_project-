"""Send yourself the exact branded cold email a lead receives, to check inbox placement and looks."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from outreach import branding, mailer
from outreach.management.commands.preview_outreach_email import SAMPLE_BODY, SAMPLE_SUBJECT

PREVIEW_UNSUBSCRIBE = '/api/outreach/unsubscribe/preview/'


class Command(BaseCommand):
    help = "Email the sample cold email (US footer, booking button, one-click unsubscribe) to OUTREACH_NOTIFY_EMAIL."

    def add_arguments(self, parser):
        parser.add_argument('--to', default='', help="Send here instead of OUTREACH_NOTIFY_EMAIL (e.g. a mail-tester.com address)")
        parser.add_argument('--region', default='US', help="US, UK, EU or AU legal footer")

    def handle(self, *args, **options):
        to = options['to'] or settings.OUTREACH_NOTIFY_EMAIL
        if not to:
            raise CommandError('Set OUTREACH_NOTIFY_EMAIL or pass --to.')
        if not mailer.is_configured():
            raise CommandError(f'The {mailer.transport()} transport is not configured (see docs/resend-autopilot-setup.md).')
        unsubscribe_url = f'{settings.OUTREACH_REVIEW_BASE_URL}{PREVIEW_UNSUBSCRIBE}'
        text, html = branding.compose(SAMPLE_SUBJECT, SAMPLE_BODY, region=options['region'], source='google-maps',
                                      unsubscribe_url=unsubscribe_url)
        try:
            provider_id, _ = mailer.send_message(to, f'[TEST] {SAMPLE_SUBJECT}', text, html=html,
                                                 unsubscribe_url=unsubscribe_url)
        except mailer.ERRORS as exc:
            raise CommandError(f'Send failed: {exc}') from exc
        self.stdout.write(f'Sent via {mailer.transport()} from {settings.OUTREACH_FROM_EMAIL} to {to} (id {provider_id}).')
        self.stdout.write('Check: inbox (not spam/promotions)? In Gmail open it, then More > Show original: '
                          'SPF, DKIM and DMARC should all say PASS.')
