from django import forms

from .upload_validation import validate_uploaded_image


class ConversationReplyForm(forms.Form):
    body = forms.CharField(
        label="Message",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "form-input",
                "placeholder": "Write a short reply or update.",
            }
        ),
    )
    image = forms.FileField(
        required=False,
        label="Cow image",
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".jpg,.jpeg,.png,.webp",
            }
        ),
    )

    def clean_body(self):
        body = (self.cleaned_data.get("body") or "").strip()
        if len(body) < 4:
            raise forms.ValidationError(
                "Write a short reply so the other person can act on it."
            )
        return body

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            # Reuse the shared validation path so message uploads stay aligned
            # with the farmer workflow and future attachment forms.
            validate_uploaded_image(image)
        return image
