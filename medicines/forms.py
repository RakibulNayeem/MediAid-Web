from django import forms
from django.utils.translation import gettext_lazy as _


class CsvImportForm(forms.Form):
    kind = forms.ChoiceField(
        label=_("What's in the file?"),
        choices=[("medicines", _("Medicines (brands and prices)")), ("generics", _("Generic information pages"))],
    )
    file = forms.FileField(label=_("CSV file"))
    dry_run = forms.BooleanField(
        label=_("Check only, don't save"), required=False, initial=True,
        help_text=_("Untick this after the check passes to save the data."),
    )
