"""Local development settings for Phoenix Scientific Platform"""

# Import all settings from the main settings file
from .settings import *

# Override database settings for SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Disable SSL for local development
DATABASES['default']['OPTIONS'] = {}

# Disable SSL for PostgreSQL if used
for db in DATABASES.values():
    if 'OPTIONS' in db and 'sslmode' in db['OPTIONS']:
        del db['OPTIONS']['sslmode']

# Allow all hosts for local development
ALLOWED_HOSTS = ['*']

# Enable debug mode
DEBUG = True

# Disable HTTPS for local development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Enable CORS for local development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Click Payment Settings
CLICK_SETTINGS = {
    '82154': {
        'MERCHANT_ID': os.getenv('CLICK_MERCHANT_ID_82154', '45730'),
        'SERVICE_ID': os.getenv('CLICK_SERVICE_ID_82154', '82154'),
        'SECRET_KEY': os.getenv('CLICK_SECRET_KEY_82154', 'XZC6u3JBBh'),
        'MERCHANT_USER_ID': os.getenv('CLICK_MERCHANT_USER_ID_82154', '63536'),
    },
    '82155': {
        'MERCHANT_ID': os.getenv('CLICK_MERCHANT_ID_82155', '45730'),
        'SERVICE_ID': os.getenv('CLICK_SERVICE_ID_82155', '82155'),
        'SECRET_KEY': os.getenv('CLICK_SECRET_KEY_82155', 'icHbYQnMBx'),
        'MERCHANT_USER_ID': os.getenv('CLICK_MERCHANT_USER_ID_82155', '64985'),
    },
    '89248': {
        'MERCHANT_ID': os.getenv('CLICK_MERCHANT_ID_89248', '45730'),
        'SERVICE_ID': os.getenv('CLICK_SERVICE_ID_89248', '89248'),
        'SECRET_KEY': os.getenv('CLICK_SECRET_KEY_89248', '08ClKUoBemAxyM'),
        'MERCHANT_USER_ID': os.getenv('CLICK_MERCHANT_USER_ID_89248', '72021'),
    },
}
