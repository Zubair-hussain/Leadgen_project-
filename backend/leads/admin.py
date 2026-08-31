from django.contrib import admin
from .models import Lead

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('email', 'phone', 'source', 'category', 'service', 'location', 'found_at')
    search_fields = ('email', 'source', 'category', 'service', 'location')
    list_filter = ('source', 'category', 'service', 'found_at')