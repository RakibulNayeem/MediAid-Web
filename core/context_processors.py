from django.conf import settings


def site(request):
    return {"accounts_enabled": settings.ACCOUNTS_ENABLED}
