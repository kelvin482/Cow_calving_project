from django import forms
from django.contrib.auth.models import User

from .models import Role


def _profile_widget(placeholder, extra_classes=""):
    classes = (
        "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 "
        "placeholder:text-slate-400 shadow-sm shadow-slate-200/40 transition "
        "focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-100"
    )
    if extra_classes:
        classes = f"{classes} {extra_classes}"
    return {"class": classes, "placeholder": placeholder}


class ProfileUpdateForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    role = forms.ModelChoiceField(
        queryset=Role.objects.none(),
        required=True,
        empty_label="Select role",
    )
    farm_name = forms.CharField(max_length=200, required=False)
    phone_number = forms.CharField(max_length=30, required=False)

    def __init__(self, *args, user, profile, **kwargs):
        self.user = user
        self.profile = profile
        super().__init__(*args, **kwargs)

        # Self-service profile edits must not let users escalate themselves into
        # the veterinary role. Veterinary accounts stay admin-provisioned,
        # while all other users can only keep or select the farmer role.
        active_roles = Role.objects.filter(is_active=True)
        if profile.role and profile.role.slug == "veterinary":
            self.fields["role"].queryset = active_roles.filter(slug="veterinary")
        else:
            self.fields["role"].queryset = active_roles.filter(slug="farmer")

        self.fields["first_name"].widget.attrs.update(_profile_widget("First name"))
        self.fields["last_name"].widget.attrs.update(_profile_widget("Last name"))
        self.fields["email"].widget.attrs.update(
            _profile_widget("Email address", extra_classes="lowercase")
        )
        self.fields["role"].widget.attrs.update(_profile_widget("Select role"))
        self.fields["farm_name"].widget.attrs.update(_profile_widget("Farm name"))
        self.fields["phone_number"].widget.attrs.update(_profile_widget("Phone number"))

        self.initial.setdefault("first_name", user.first_name)
        self.initial.setdefault("last_name", user.last_name)
        self.initial.setdefault("email", user.email)
        self.initial.setdefault("role", profile.role)
        self.initial.setdefault("farm_name", profile.farm_name)
        self.initial.setdefault("phone_number", profile.phone_number)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if not email:
            return email

        existing = User.objects.filter(email__iexact=email).exclude(pk=self.user.pk)
        if existing.exists():
            raise forms.ValidationError("Another account is already using this email.")
        return email

    def save(self):
        self.user.first_name = self.cleaned_data["first_name"].strip()
        self.user.last_name = self.cleaned_data["last_name"].strip()
        self.user.email = self.cleaned_data["email"].strip()
        self.user.save(update_fields=["first_name", "last_name", "email"])

        self.profile.role = self.cleaned_data["role"]
        self.profile.farm_name = self.cleaned_data["farm_name"].strip()
        self.profile.phone_number = self.cleaned_data["phone_number"].strip()
        # Profile completeness now depends on the fields users can actually edit
        # on this screen rather than a hardcoded one-off signup assumption.
        self.profile.is_profile_complete = all(
            [
                self.user.first_name,
                self.user.last_name,
                self.user.email,
                self.profile.role_id,
            ]
        )
        self.profile.save(
            update_fields=[
                "role",
                "farm_name",
                "phone_number",
                "is_profile_complete",
            ]
        )

        return self.profile
