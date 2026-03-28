from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm
from django.contrib.auth.models import User

from users.models import Profile, Role
from users.services import get_or_create_profile

try:
    from allauth.account.models import EmailAddress
except ImportError:  # pragma: no cover - fallback if allauth account app changes
    EmailAddress = None


def _apply_widget_attrs(field, placeholder, extra_classes=""):
    # Centralize auth field styling so the templates stay focused on layout.
    classes = (
        "auth-input w-full bg-transparent border-b border-sage/40 text-slate-900 "
        "placeholder:text-slate-400 focus:outline-none focus:border-forest "
        "focus:ring-0 py-2 transition"
    )
    if extra_classes:
        classes = f"{classes} {extra_classes}"
    field.widget.attrs.update(
        {
            "class": classes,
            "placeholder": placeholder,
        }
    )


class CowCalvingLoginForm(forms.Form):
    LOGIN_TYPE_FARMER = "farmer"
    LOGIN_TYPE_VETERINARY = "veterinary"
    LOGIN_TYPE_CHOICES = (
        (LOGIN_TYPE_FARMER, "Farmer"),
        (LOGIN_TYPE_VETERINARY, "Veterinary"),
    )

    login_type = forms.ChoiceField(
        choices=LOGIN_TYPE_CHOICES,
        initial=LOGIN_TYPE_FARMER,
        widget=forms.RadioSelect,
    )
    email = forms.EmailField(required=False)
    professional_id = forms.CharField(required=False)
    password = forms.CharField(required=True, strip=False, widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

        self.fields["login_type"].widget.attrs.update(
            {"class": "auth-login-type", "data-login-type-toggle": "true"}
        )
        _apply_widget_attrs(self.fields["email"], "name@example.com")
        _apply_widget_attrs(self.fields["professional_id"], "Enter your professional ID")
        _apply_widget_attrs(self.fields["password"], "Enter your password")

    def clean(self):
        cleaned_data = super().clean()
        login_type = (cleaned_data.get("login_type") or self.LOGIN_TYPE_FARMER).strip()
        password = cleaned_data.get("password") or ""

        if login_type == self.LOGIN_TYPE_VETERINARY:
            professional_id = (cleaned_data.get("professional_id") or "").strip()
            if not professional_id:
                self.add_error("professional_id", "Enter the professional ID provided by admin.")
                return cleaned_data

            self.user_cache = authenticate(
                self.request,
                professional_id=professional_id,
                password=password,
            )
            if self.user_cache is None:
                raise forms.ValidationError("Professional ID or password is incorrect.")
        else:
            email = (cleaned_data.get("email") or "").strip()
            if not email:
                self.add_error("email", "Enter your email address.")
                return cleaned_data

            self.user_cache = authenticate(
                self.request,
                email=email,
                password=password,
            )
            if self.user_cache is None:
                raise forms.ValidationError("Email or password is incorrect.")

            profile = Profile.objects.select_related("role").filter(user=self.user_cache).first()
            if (
                not self.user_cache.is_superuser
                and profile
                and profile.role
                and profile.role.slug == self.LOGIN_TYPE_VETERINARY
            ):
                self.user_cache = None
                raise forms.ValidationError(
                    "Veterinary accounts must sign in with the professional ID assigned by admin."
                )

        if self.user_cache is not None and not self.user_cache.is_active:
            self.user_cache = None
            raise forms.ValidationError("This account is inactive.")

        return cleaned_data

    def get_user(self):
        return self.user_cache


class PasswordResetCodeRequestForm(forms.Form):
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_widget_attrs(self.fields["email"], "name@example.com")


class PasswordResetCodeConfirmForm(SetPasswordForm):
    code = forms.CharField(max_length=6, min_length=6, required=True)

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        _apply_widget_attrs(self.fields["code"], "Enter the 6-digit code")
        _apply_widget_attrs(self.fields["new_password1"], "Create a new password")
        _apply_widget_attrs(self.fields["new_password2"], "Confirm the new password")

    def clean_code(self):
        # Keeping the code numeric makes it faster to enter from an email screen.
        code = (self.cleaned_data.get("code") or "").strip()
        if not code.isdigit():
            raise forms.ValidationError("Enter the 6-digit code from your email.")
        return code


class CowCalvingRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    farm_name = forms.CharField(max_length=200, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "farm_name",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_widget_attrs(self.fields["first_name"], "First name")
        _apply_widget_attrs(self.fields["last_name"], "Last name")
        _apply_widget_attrs(self.fields["username"], "Choose a username")
        _apply_widget_attrs(self.fields["email"], "name@example.com")
        _apply_widget_attrs(self.fields["farm_name"], "Optional farm name")
        _apply_widget_attrs(self.fields["password1"], "Create a password")
        _apply_widget_attrs(self.fields["password2"], "Confirm your password")

        for field in self.fields.values():
            if field.required:
                field.widget.attrs.setdefault("data-progress", "1")

    def clean_email(self):
        # Manual signup should honor the same unique-email expectation as account recovery.
        email = (self.cleaned_data.get("email") or "").strip()
        if not email:
            return email

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")

        if EmailAddress and EmailAddress.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")

        return email

    def clean(self):
        cleaned_data = super().clean()
        farmer_role = Role.objects.filter(slug="farmer", is_active=True).first()
        if not farmer_role:
            raise forms.ValidationError(
                "Farmer registration is temporarily unavailable. Ask the admin to restore the farmer role."
            )
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.email = self.cleaned_data.get("email", "")

        if commit:
            user.save()
            profile = get_or_create_profile(user)
            profile.role = Role.objects.get(slug="farmer")
            profile.farm_name = self.cleaned_data.get("farm_name", "")
            # Treat role assignment as the first milestone of profile setup.
            profile.is_profile_complete = bool(profile.role)
            profile.save()
        return user
