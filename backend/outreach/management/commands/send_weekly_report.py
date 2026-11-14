from django.core.management.base import BaseCommand
from django.utils import timezone

from outreach.report import build, collect, send_report


class Command(BaseCommand):
    help = "Email the weekly outreach report now (any day). Use --print to only show it."

    def add_arguments(self, parser):
        parser.add_argument('--print', action='store_true', help="Print the report instead of emailing it.")

    def handle(self, *args, **options):
        if options['print']:
            subject, body = build(collect(timezone.now()))
            self.stdout.write(f"Subject: {subject}\n\n{body}")
            return
        self.stdout.write(send_report())
