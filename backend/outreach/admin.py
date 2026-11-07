from django.contrib import admin

from .models import OutreachMessage, SendThrottle, Suppression


@admin.register(OutreachMessage)
class OutreachMessageAdmin(admin.ModelAdmin):
    list_display = ('to_email', 'subject', 'status', 'dry_run', 'approved_at', 'sent_at', 'owner')
    list_filter = ('status', 'dry_run')
    search_fields = ('to_email', 'subject')
    readonly_fields = ('gmail_message_id', 'gmail_thread_id', 'sent_at', 'approved_at')


@admin.register(Suppression)
class SuppressionAdmin(admin.ModelAdmin):
    list_display = ('email', 'reason', 'owner', 'created_at')
    list_filter = ('reason',)
    search_fields = ('email',)


admin.site.register(SendThrottle)
