from project.settings.base import *  # noqa

DEBUG = True

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
]

INSTALLED_APPS += [
    "django_browser_reload",
]

MIDDLEWARE += [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="mindjunkies"),
        "USER": config("POSTGRES_USER", default="mindjunkies"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="mindjunkies"),
        "HOST": config("POSTGRES_HOST", default="localhost"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

REDIS_HOST = config("REDIS_HOST", default="127.0.0.1")
REDIS_PORT = config("REDIS_PORT", default="6379")
REDIS_PASSWORD = config("REDIS_PASSWORD", default=None)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        "OPTIONS": {
            **({"PASSWORD": REDIS_PASSWORD} if REDIS_PASSWORD else {}),
        },
    }
}

RESEND_API_KEY = config("RESEND_API_KEY")
EMAIL_BACKEND = "utils.email_backends.ResendEmailBackend"
DEFAULT_FROM_EMAIL = config("RESEND_FROM_EMAIL")

ACCOUNT_EMAIL_VERIFICATION = "mandatory"
