from decimal import Decimal

from django import template
from django.utils.translation import get_language

register = template.Library()

_BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


@register.filter
def num(value):
    """Show numbers in Bangla digits on the Bangla site: 500mg -> ৫০০mg."""
    if value is None:
        return ""
    text = str(value)
    return text.translate(_BN_DIGITS) if get_language() == "bn" else text


@register.filter
def taka(value):
    """Format a price: 12.50 -> ৳ ১২.৫০; 12.00 -> ৳ ১২."""
    if value is None:
        return ""
    amount = Decimal(value).quantize(Decimal("0.01"))
    text = f"{amount:,.2f}".removesuffix(".00")
    return f"৳ {num(text)}"


@register.filter
def lines(value):
    """Split a text field into bullet points, one per line."""
    return [line.strip(" -•\t") for line in (value or "").splitlines() if line.strip(" -•\t")]


@register.simple_tag(takes_context=True)
def page_url(context, page):
    """The current URL with only the page number changed (keeps ?q=...)."""
    params = context["request"].GET.copy()
    params["page"] = page
    return f"?{params.urlencode()}"


@register.filter
def localized(obj, field="name"):
    """obj.name_bn on the Bangla site (when filled in), otherwise obj.name."""
    if get_language() == "bn":
        bangla = getattr(obj, f"{field}_bn", "")
        if bangla:
            return bangla
    return getattr(obj, field)


@register.filter
def dual(obj, field="name"):
    """Bangla site: 'নাপা (Napa)', keeping the English that's printed on the box. Otherwise just English."""
    english = getattr(obj, field)
    if get_language() == "bn":
        bangla = getattr(obj, f"{field}_bn", "")
        if bangla and bangla != english:
            return f"{bangla} ({english})"
    return english


@register.inclusion_tag("core/_avatar.html")
def avatar(user, large=False):
    """The Google photo when there is one, on top of the first letter of the name, which shows if it can't load."""
    accounts = user.socialaccount_set.all()
    return {
        "large": large,
        "letter": (user.first_name or user.email or user.username)[:1].upper(),
        "picture": next((url for account in accounts if (url := account.get_avatar_url())), ""),
    }
