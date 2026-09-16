from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('leads', '0005_lead_is_verified'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                help_text='Authenticated user who owns this lead',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='leads',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name='lead',
            index=models.Index(fields=['owner'], name='leads_lead_owner_i_b69f32_idx'),
        ),
    ]
