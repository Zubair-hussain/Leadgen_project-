from django.apps import AppConfig


class OutreachConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'outreach'

    def ready(self):
        from . import signals  # noqa: F401  pylint: disable=import-outside-toplevel,unused-import
