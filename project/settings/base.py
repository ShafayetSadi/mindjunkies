from pathlib import Path

from decouple import Csv, config

# Configuration

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost", cast=Csv())

INTERNAL_IPS = [
    "127.0.0.1",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.postgres",
    # custom mindjunkies
    "mindjunkies.home",
    "mindjunkies.accounts",
    "mindjunkies.courses",
    "mindjunkies.lecture",
    "mindjunkies.dashboard",
    "mindjunkies.live_classes",
    "mindjunkies.forums",
    "mindjunkies.payments",
    # third party mindjunkies
    "django_tailwind_cli",
    "crispy_forms",
    "crispy_tailwind",
    "categories",
    "categories.editor",
    "silk",
    "django_htmx",
    "template_partials",
    "django_extensions",
    "taggit",
    # allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]

MIDDLEWARE = [
    "silk.middleware.SilkyMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # allauth
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # custom middleware here
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "mindjunkies/templates",
            BASE_DIR / "mindjunkies/accounts/templates/accounts/",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",  # allauth
            ],
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",  # allauth
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Dhaka"

USE_I18N = True

USE_TZ = True

STATICFILES_DIRS = [
    BASE_DIR / "mindjunkies/static",
]
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "/"
AUTH_USER_MODEL = "accounts.User"

# allauth settings
SITE_ID = 1
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_CHANGE_EMAIL = True
ACCOUNT_EMAIL_NOTIFICATIONS = True

ACCOUNT_RATE_LIMITS = {
    "login_failed": "5/5m",
}

ACCOUNT_FORMS = {
    "add_email": "allauth.account.forms.AddEmailForm",
    "change_password": "allauth.account.forms.ChangePasswordForm",
    "confirm_login_code": "allauth.account.forms.ConfirmLoginCodeForm",
    "login": "allauth.account.forms.LoginForm",
    "request_login_code": "allauth.account.forms.RequestLoginCodeForm",
    "reset_password": "allauth.account.forms.ResetPasswordForm",
    "reset_password_from_key": "allauth.account.forms.ResetPasswordKeyForm",
    "set_password": "allauth.account.forms.SetPasswordForm",
    "signup": "allauth.account.forms.SignupForm",
    "user_token": "allauth.account.forms.UserTokenForm",
}

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": config("GOOGLE_CLIENT_ID"),
            "secret": config("GOOGLE_CLIENT_SECRET"),
            "key": config("GOOGLE_API_KEY"),
        },
        "EMAIL_AUTHENTICATION": True,
        "FETCH_USERINFO": True,
    },
}


CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

JITSI_APP_ID = config("JITSI_APP_ID")
JITSI_SECRET = config("JITSI_SECRET")

TAGGIT_CASE_INSENSITIVE = True
