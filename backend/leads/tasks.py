from celery import shared_task
from django.contrib.auth import get_user_model

from .services import LeadGenerator


@shared_task(bind=True)
def generate_leads_task(self, user_id, category, platforms, niche=None,
                        target_location=None, is_professional=False):
    User = get_user_model()
    owner = User.objects.get(id=user_id)
    generator = LeadGenerator()
    return generator.generate_leads(
        category,
        platforms,
        niche=niche,
        target_location=target_location,
        is_professional=is_professional,
        owner=owner,
    )
