import re
# validators.py
# ─────────────────────────────────────────────────────────────────
# Shared validation helpers for the AMAN PHONE project.
#
# Centralising all validation here means:
#   - No duplicated logic across app.py and ocr.py
#   - One place to update rules (e.g. phone length, IMEI format)
#   - Every module imports from here instead of re-implementing
# ─────────────────────────────────────────────────────────────────

import os
from werkzeug.utils import secure_filename

# ── Allowed image extensions for uploads ─────────────────────────
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# ── Input length limits ───────────────────────────────────────────
MAX_OWNER_NAME     = 100   # characters
MAX_MODEL_NAME     = 100
MAX_PLACE_OF_THEFT = 200
MAX_COLOR          = 50
MAX_EMAIL          = 150
MAX_PHONE_NUMBER   = 15    # digits
MIN_PHONE_NUMBER   = 7


# ─────────────────────────────────────────────
# Luhn algorithm — validates an IMEI checksum
# ─────────────────────────────────────────────
def is_valid_luhn(imei):
    """
    Run the Luhn checksum on a numeric string.
    Returns True if the checksum passes, False otherwise.
    Used to verify that an IMEI is structurally valid,
    not just 15 digits long.
    """
    total = 0
    for i, digit in enumerate(reversed(imei)):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


# ─────────────────────────────────────────────
# IMEI validation
# ─────────────────────────────────────────────
def validate_imei(imei, field_name="IMEI"):
    """
    Validate a single IMEI string.
      - Must be exactly 15 digits
      - Must pass the Luhn checksum

    Returns an error message string if invalid, or None if valid.
    Pass field_name to get clear messages e.g. "Primary IMEI".
    """
    if not imei or not imei.isdigit() or len(imei) != 15:
        return f"{field_name} must be exactly 15 digits."
    if not is_valid_luhn(imei):
        return f"{field_name} is invalid — checksum failed."
    return None


# ─────────────────────────────────────────────
# Phone number validation
# ─────────────────────────────────────────────
def validate_phone_number(phone_number):
    """
    Validate a phone number string.
      - Must not be empty
      - Must contain digits only
      - Must be between MIN_PHONE_NUMBER and MAX_PHONE_NUMBER digits

    Returns an error message string if invalid, or None if valid.
    """
    if not phone_number:
        return "Phone number is required."
    if not phone_number.isdigit():
        return "Phone number must contain digits only."
    if not (MIN_PHONE_NUMBER <= len(phone_number) <= MAX_PHONE_NUMBER):
        return f"Phone number must be between {MIN_PHONE_NUMBER} and {MAX_PHONE_NUMBER} digits."
    return None

# ─────────────────────────────────────────────
# Email validation
# ─────────────────────────────────────────────

# Simple regex: local@domain.tld — covers all common real-world formats
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

def validate_email(email):
    """
    Validate an email address using a simple regex.
      - Must not be empty
      - Must follow the pattern: something@something.tld

    Returns an error message string if invalid, or None if valid.
    """
    if not email:
        return "Email address is required."
    if len(email) > MAX_EMAIL:
        return f"Email address must be under {MAX_EMAIL} characters."
    if not _EMAIL_RE.match(email):
        return "Please enter a valid email address (e.g. name@example.com)."
    return None



# ─────────────────────────────────────────────
# File type validation
# ─────────────────────────────────────────────
def allowed_file(filename):
    """
    Check that the uploaded filename has an allowed image extension.
    Returns True if allowed, False otherwise.
    """
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ─────────────────────────────────────────────
# Safe file save helper
# ─────────────────────────────────────────────
def save_upload(file, upload_folder):
    """
    Sanitise the filename with secure_filename() and save
    the uploaded file to upload_folder.

    Returns the full saved file path as a string.
    Raises ValueError if the filename becomes empty after sanitising.
    """
    filename = secure_filename(file.filename)

    if not filename:
        raise ValueError("Invalid filename after sanitisation.")

    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    return file_path


# ─────────────────────────────────────────────
# Text field length trimmer
# ─────────────────────────────────────────────
def trim(value, max_length):
    """
    Strip whitespace and truncate a string to max_length characters.
    Returns an empty string if value is None.
    """
    if not value:
        return ""
    return value.strip()[:max_length]