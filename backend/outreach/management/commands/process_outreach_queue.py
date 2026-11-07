from django.core.management.base import BaseCommand

from outreach.services import process_queue, queue_status


class Command(BaseCommand):
    help = "Run one send tick (what Celery Beat does every minute) and print the queue status."

    def handle(self, *args, **options):
        self.stdout.write(f"Result: {process_queue()}")
        for key, value in queue_status().items():
            self.stdout.write(f"  {key}: {value}")
