from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator


DEFAULT_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp")
DEFAULT_MAX_IMAGE_UPLOAD_SIZE = 5 * 1024 * 1024


def validate_uploaded_image(
    upload,
    *,
    allowed_extensions=DEFAULT_IMAGE_EXTENSIONS,
    max_size_bytes=DEFAULT_MAX_IMAGE_UPLOAD_SIZE,
):
    if not upload:
        return upload

    # Check both the filename extension and the browser-reported content type
    # so obviously disguised non-image uploads are rejected early.
    FileExtensionValidator(allowed_extensions=list(allowed_extensions))(upload)

    content_type = (getattr(upload, "content_type", "") or "").strip().lower()
    if content_type and not content_type.startswith("image/"):
        raise ValidationError("Upload an image file only.")

    # Keep uploads small enough that the messaging flow cannot be abused with
    # oversized files or accidental high-resolution images.
    if upload.size > max_size_bytes:
        raise ValidationError("Image size should be 5 MB or less.")

    return upload
