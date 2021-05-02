INSTALLED_APPS = list(locals().get("INSTALLED_APPS", []))

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "test_db.sqlite3"}}

MIGRATION_MODULES = {app: None for app in INSTALLED_APPS}
