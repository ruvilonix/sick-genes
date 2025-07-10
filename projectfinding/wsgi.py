"""
WSGI config for projectfinding project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from pathlib import  Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projectfinding.settings')

application = get_wsgi_application()


BASE_DIR = Path(__file__).resolve().parent.parent
WHITE_NOISE_ENABLED = os.environ.get('WHITE_NOISE_ENABLED', None) == 'True' 

if WHITE_NOISE_ENABLED:
    from whitenoise import WhiteNoise
    application = WhiteNoise(application, root=BASE_DIR)
    application.add_files(BASE_DIR / 'static', prefix='/static') # ' BASE_DIR/static': directory where the collected static files are located.
