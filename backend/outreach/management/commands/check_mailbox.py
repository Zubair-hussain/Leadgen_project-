from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from outreach import branding, inbox, mailer, smtp_client


class Command(BaseCommand):
    help = ("Check the sending mailbox: SMTP login, IMAP login and Sent folder. "
            "With --send-test, email yourself a branded sample (ignores dry run).")

    def add_arguments(self, parser):
        parser.add_argument('--send-test', action='store_true', help="Send a sample to OUTREACH_NOTIFY_EMAIL")
        parser.add_argument('--to', default='', help="Send the sample to this address instead")

    def handle(self, *args, **options):
        self.stdout.write(f"Transport: {mailer.transport()}  From: {settings.OUTREACH_FROM_EMAIL}")
        if not mailer.is_configured():
            raise CommandError("Mailbox is not configured. Set OUTREACH_SMTP_PASSWORD (or the GOOGLE_* values).")

        if mailer.transport() == 'smtp':
            server = smtp_client.connect()
            server.quit()
            self.stdout.write(self.style.SUCCESS(
                f"SMTP login OK ({settings.OUTREACH_SMTP_HOST}:{settings.OUTREACH_SMTP_PORT})"))

        if inbox.is_configured():
            with inbox.connect() as imap:
                self.stdout.write(self.style.SUCCESS(
                    f"IMAP login OK ({settings.OUTREACH_IMAP_HOST}); Sent folder: {inbox.sent_folder(imap)}"))
        else:
            self.stdout.write(self.style.WARNING("IMAP not configured: replies will not stop follow-ups."))

        if options['send_test'] or options['to']:
            to = options['to'] or settings.OUTREACH_NOTIFY_EMAIL
            subject = "quick idea for your site"
            body = ("Hi there,\n\nThis is how a LeadGen outreach email looks in your inbox: a personal note on top, "
                    "your ZH. signature below. Does it look right on your phone too?\n\nRegards,\n"
                    + (settings.OUTREACH_FROM_NAME or 'Zubair').split()[0])
            text, html = branding.compose(subject, body)
            message_id, _ = mailer.send_message(to, subject, text, html=html, message_id=mailer.new_message_id())
            self.stdout.write(self.style.SUCCESS(f"Sample sent to {to} ({message_id})."))
            self.stdout.write("Plain-text part:\n" + text)
