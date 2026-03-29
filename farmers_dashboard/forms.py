from django import forms

from communications.upload_validation import validate_uploaded_image

from .models import Cow, ReproductiveEvent


class CowRegistrationForm(forms.ModelForm):
    reproductive_status = forms.ChoiceField(
        choices=Cow.REPRODUCTIVE_STATUS_CHOICES,
        required=True,
        widget=forms.RadioSelect(
            attrs={"class": "sr-only peer reproductive-status-input"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["insemination_type"].choices = [
            ("", "Choose insemination type")
        ] + list(Cow.INSEMINATION_TYPE_CHOICES)

    class Meta:
        model = Cow
        fields = [
            "cow_number",
            "name",
            "breed",
            "date_of_birth",
            "reproductive_status",
            "last_heat_date",
            "insemination_type",
            "insemination_date",
            "pregnancy_confirmation_date",
            "is_pregnant",
            "expected_calving_date",
            "is_lactating",
            "photo",
            "notes",
        ]
        widgets = {
            "cow_number": forms.TextInput(
                attrs={"placeholder": "e.g. COW-001", "class": "form-input"}
            ),
            "name": forms.TextInput(
                attrs={"placeholder": "e.g. Daisy, Bella, Rosie", "class": "form-input"}
            ),
            "breed": forms.Select(attrs={"class": "form-input"}),
            "date_of_birth": forms.DateInput(
                attrs={"type": "date", "class": "form-input"}
            ),
            "last_heat_date": forms.DateInput(
                attrs={"type": "date", "class": "form-input"}
            ),
            "insemination_type": forms.Select(
                attrs={"class": "form-input"}
            ),
            "insemination_date": forms.DateInput(
                attrs={"type": "date", "class": "form-input"}
            ),
            "pregnancy_confirmation_date": forms.DateInput(
                attrs={"type": "date", "class": "form-input"}
            ),
            "expected_calving_date": forms.DateInput(
                attrs={"type": "date", "class": "form-input"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Any notes about this cow...",
                    "class": "form-input",
                }
            ),
            "photo": forms.ClearableFileInput(
                attrs={"accept": "image/*", "class": "sr-only", "id": "id_photo"}
            ),
        }
        labels = {
            "cow_number": "Cow Number",
            "date_of_birth": "Date of Birth",
            "last_heat_date": "Last Heat Date",
            "insemination_type": "Insemination Type",
            "insemination_date": "Insemination Date",
            "pregnancy_confirmation_date": "Pregnancy Confirmation Date",
            "expected_calving_date": "Expected Calving Date",
            "is_pregnant": "Currently Pregnant?",
            "is_lactating": "Currently Lactating?",
            "photo": "Cow Image",
        }

    def clean(self):
        cleaned_data = super().clean()
        reproductive_status = cleaned_data.get("reproductive_status")
        last_heat_date = cleaned_data.get("last_heat_date")
        insemination_type = cleaned_data.get("insemination_type")
        insemination_date = cleaned_data.get("insemination_date")
        pregnancy_confirmation_date = cleaned_data.get("pregnancy_confirmation_date")
        is_pregnant = cleaned_data.get("is_pregnant")
        expected_calving_date = cleaned_data.get("expected_calving_date")

        if not reproductive_status:
            self.add_error(
                "reproductive_status",
                "Choose the current reproductive starting point for this cow.",
            )
            return cleaned_data

        if reproductive_status == Cow.REPRODUCTIVE_STATUS_NOT_INSEMINATED:
            if not last_heat_date:
                self.add_error(
                    "last_heat_date",
                    "Add the latest observed heat date to start the cow on the right path.",
                )
            if not insemination_type:
                self.add_error(
                    "insemination_type",
                    "Choose the insemination type you want to prepare for this cow.",
                )

        if reproductive_status == Cow.REPRODUCTIVE_STATUS_INSEMINATED:
            if not insemination_date:
                self.add_error(
                    "insemination_date",
                    "Add the insemination date to continue with the tracker.",
                )

        if reproductive_status == Cow.REPRODUCTIVE_STATUS_PREGNANCY_CONFIRMED:
            if not (pregnancy_confirmation_date or expected_calving_date):
                self.add_error(
                    "pregnancy_confirmation_date",
                    "Add a pregnancy confirmation date or an expected calving date.",
                )

        if reproductive_status == Cow.REPRODUCTIVE_STATUS_NEAR_CALVING:
            if not expected_calving_date:
                self.add_error(
                    "expected_calving_date",
                    "Add the expected calving date before starting the calving watch.",
                )

        if expected_calving_date and reproductive_status in {
            Cow.REPRODUCTIVE_STATUS_PREGNANCY_CONFIRMED,
            Cow.REPRODUCTIVE_STATUS_NEAR_CALVING,
        }:
            cleaned_data["is_pregnant"] = True
        elif reproductive_status in {
            Cow.REPRODUCTIVE_STATUS_NOT_INSEMINATED,
            Cow.REPRODUCTIVE_STATUS_INSEMINATED,
        }:
            cleaned_data["is_pregnant"] = False

        if expected_calving_date and reproductive_status == Cow.REPRODUCTIVE_STATUS_NOT_INSEMINATED:
            self.add_error(
                "expected_calving_date",
                "Expected calving date comes later after insemination or pregnancy confirmation.",
            )
        return cleaned_data

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo:
            return photo

        # Route cow photo checks through the shared helper so size and MIME
        # rules stay consistent with the messaging upload surfaces.
        return validate_uploaded_image(
            photo,
            allowed_extensions=("jpg", "jpeg", "png", "webp", "gif"),
        )


class ReproductiveEventForm(forms.Form):
    event_type = forms.ChoiceField(
        choices=ReproductiveEvent.EVENT_TYPE_CHOICES,
        widget=forms.RadioSelect(
            attrs={"class": "sr-only peer reproductive-event-input"}
        ),
    )
    event_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "form-input",
                "placeholder": "Optional short note for this event",
            }
        ),
    )

    def __init__(self, *args, cow=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cow = cow

    def clean(self):
        cleaned_data = super().clean()
        event_type = cleaned_data.get("event_type")
        event_date = cleaned_data.get("event_date")

        if not event_type or not event_date:
            return cleaned_data

        if self.cow and event_type == ReproductiveEvent.EVENT_PREGNANCY_CONFIRMED:
            if not self.cow.insemination_date and not self.cow.expected_calving_date:
                self.add_error(
                    "event_type",
                    "Record insemination first so the pregnancy follow-up can stay accurate.",
                )

        if self.cow and event_type == ReproductiveEvent.EVENT_CALVED and not (
            self.cow.is_pregnant
            or self.cow.expected_calving_date
            or self.cow.tracking_stage == Cow.STAGE_ACTIVE_LABOR
        ):
            self.add_error(
                "event_type",
                "Mark calving after the pregnancy path has been started for this cow.",
            )

        return cleaned_data


class ServiceProviderMessageForm(forms.Form):
    provider_key = forms.CharField(widget=forms.HiddenInput())
    county = forms.CharField(required=False, widget=forms.HiddenInput())
    service_type = forms.CharField(required=False, widget=forms.HiddenInput())
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "form-input",
                "placeholder": "Type a short message about the help you need.",
            }
        ),
    )
    image = forms.FileField(
        required=False,
        label="Cow image",
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".jpg,.jpeg,.png,.webp",
                "class": "form-input",
            }
        ),
    )

    def clean_message(self):
        message = (self.cleaned_data.get("message") or "").strip()
        if len(message) < 8:
            raise forms.ValidationError(
                "Write a short message so the provider understands the request."
            )
        return message

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            # Messaging attachments use the same guardrails as other image
            # uploads to avoid one form becoming the weaker path.
            validate_uploaded_image(image)
        return image


class FarmLocationForm(forms.Form):
    latitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput(),
    )
    longitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput(),
    )
    source = forms.ChoiceField(
        choices=[
            ("manual_pin", "Pin on map"),
            ("current_location", "Current location"),
        ],
        widget=forms.HiddenInput(),
    )

    def clean_latitude(self):
        latitude = self.cleaned_data["latitude"]
        if latitude < -90 or latitude > 90:
            raise forms.ValidationError("Choose a valid farm location on the map.")
        return latitude

    def clean_longitude(self):
        longitude = self.cleaned_data["longitude"]
        if longitude < -180 or longitude > 180:
            raise forms.ValidationError("Choose a valid farm location on the map.")
        return longitude
