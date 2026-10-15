"""App configuration."""
from django.apps import AppConfig


class StoreConfig(AppConfig):
    """Configuration for the ``store`` app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "store"
