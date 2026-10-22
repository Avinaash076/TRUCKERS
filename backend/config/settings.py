import os
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-development-only")
if not DEBUG and SECRET_KEY == "local-development-only":
    raise RuntimeError("Set DJANGO_SECRET_KEY for production or DEBUG=true locally")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
if os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
INSTALLED_APPS = ["rest_framework", "corsheaders", "routing"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "corsheaders.middleware.CorsMiddleware", "django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
USE_TZ = True
TIME_ZONE = "UTC"
REST_FRAMEWORK = {"UNAUTHENTICATED_USER": None, "DEFAULT_AUTHENTICATION_CLASSES": [], "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]}
OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
WEATHER_URL = os.getenv("WEATHER_URL", "https://api.open-meteo.com/v1/forecast")
GEOCODER_URL = os.getenv("GEOCODER_URL", "https://nominatim.openstreetmap.org/search")
PROVIDER_USER_AGENT = os.getenv("PROVIDER_USER_AGENT", "WeatherHaul-assessment/1.0")
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "weatherhaul", "OPTIONS": {"MAX_ENTRIES": 4000}}}
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 16000000
