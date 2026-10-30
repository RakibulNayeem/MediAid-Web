from django.conf import settings
from django.utils import translation
from django.utils.cache import patch_vary_headers


class BanglaFirstLocaleMiddleware:
    """Use the language cookie if set, otherwise Bangla.

    Django's own LocaleMiddleware would follow the browser's language, so anyone with an
    English phone would land on the English site. MediAid should open in Bangla for them too.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if language not in dict(settings.LANGUAGES):
            language = settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = language
        response = self.get_response(request)
        patch_vary_headers(response, ("Cookie",))
        response.setdefault("Content-Language", language)
        return response
