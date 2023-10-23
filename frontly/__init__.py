""" Frontly - A front-end editor for Django with HTMX
"""
from django.conf import settings

VERSION = '1.0.3'

FRONTLY_CHECK_KILLSWITCH_PERM = getattr(settings, 'FRONTLY_CHECK_KILLSWITCH_PERM', True)
FRONTLY_SANITIZE = getattr(settings, 'FRONTLY_SANITIZE', True)
