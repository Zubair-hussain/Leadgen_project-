import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outreach', '0004_outreachmessage_auto_approved_leadresearch'),
    ]

    operations = [
        migrations.AddField(
            model_name='outreachmessage',
            name='parent',
            field=models.ForeignKey(blank=True, help_text='The first email of the thread, when this is a follow-up', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='followups', to='outreach.outreachmessage'),
        ),
        migrations.AddField(
            model_name='outreachmessage',
            name='sequence_step',
            field=models.PositiveSmallIntegerField(default=0, help_text='0 = first email, 1+ = follow-up number'),
        ),
        migrations.AddField(
            model_name='outreachmessage',
            name='priority',
            field=models.SmallIntegerField(default=0, help_text='Higher is sent first (see outreach/playbook.py)'),
        ),
        migrations.AddField(
            model_name='outreachmessage',
            name='rfc_message_id',
            field=models.CharField(blank=True, db_index=True, help_text='Message-ID header, used to thread follow-ups and match replies', max_length=255),
        ),
        migrations.AddField(
            model_name='outreachmessage',
            name='replied_at',
            field=models.DateTimeField(blank=True, help_text='Set on the first email when the lead replies', null=True),
        ),
        migrations.AddField(
            model_name='outreachmessage',
            name='bounced_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
