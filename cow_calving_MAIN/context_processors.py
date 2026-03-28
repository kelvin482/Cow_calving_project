from time import time

from django.conf import settings


def dev_static_version(request):
    # In development, change the static asset query string on each request so
    # browser-cached JS/CSS does not make local changes look "stuck".
    if settings.DEBUG:
        return {"dev_static_version": str(int(time()))}
    return {"dev_static_version": ""}
