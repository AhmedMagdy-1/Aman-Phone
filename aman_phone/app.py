import os
import csv
import io
from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from database import (
    init_db, log_search, report_stolen, count_thefts_in_location,
    get_total_reports, get_total_checks, get_unique_locations,
    get_recent_reports, get_recent_searches, get_top_locations,
    update_report, delete_report
)
from detector import classify_device
from ocr import extract_imei_from_image
from validators import (
    allowed_file, save_upload, validate_imei,
    validate_phone_number, validate_email, trim,
    MAX_OWNER_NAME,
    MAX_MODEL_NAME, MAX_COLOR, MAX_EMAIL, MAX_PLACE_OF_THEFT
)

# ─────────────────────────────────────────────
# Flask app setup
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "aman_phone_secret_key_2025"   # change in production

# Folder where uploaded images are saved
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ─────────────────────────────────────────────
# Initialize the database on startup
# ─────────────────────────────────────────────
with app.app_context():
    init_db()


# ─────────────────────────────────────────────
# Private helper — handle image upload + OCR
# Shared by /check and /extract-imei to avoid duplication
# ─────────────────────────────────────────────
def _process_uploaded_image(image):
    """
    Validate, save, and run OCR/barcode detection on an uploaded image.

    Returns a tuple: (result_dict, error_message)
      - On success : ({"imei_1": ..., "imei_2": ..., "detection_method": ...}, None)
      - On failure : (None, "human-readable error string")
    """
    # Validate file type
    if not allowed_file(image.filename):
        return None, "Only JPG, PNG, or WEBP images are allowed."

    # Save safely — secure_filename is applied inside save_upload()
    try:
        image_path = save_upload(image, UPLOAD_FOLDER)
    except ValueError:
        return None, "Invalid image filename."

    # Run OCR / barcode detection
    try:
        result = extract_imei_from_image(image_path)
    except Exception as e:
        print(f"OCR error: {e}")
        return None, "Failed to process the image. Please try another."

    return result, None


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

# GET / — Home page
@app.route("/")
def home():
    return render_template("home.html",
                           active_page="home",
                           total_reports=get_total_reports(),
                           total_checks=get_total_checks(),
                           total_locations=get_unique_locations())


# POST /extract-imei — AJAX: auto-detect IMEI from image, returns JSON
# Called by JavaScript on image select — does NOT submit the form
@app.route("/extract-imei", methods=["POST"])
def extract_imei():

    image = request.files.get("image")

    # Guard: file must be present
    if not image or image.filename == "":
        return jsonify({"error": "No image provided."}), 400

    result, error = _process_uploaded_image(image)

    if error:
        return jsonify({"error": error}), 400

    # Return all extracted fields as JSON
    return jsonify({
        "imei_1":           result.get("imei_1"),
        "model_name":       result.get("model_name"),
        "color":            result.get("color"),
        "detection_method": result.get("detection_method")
    })


# POST /check — Check IMEI status (manual entry or image upload)
@app.route("/check", methods=["GET", "POST"])
def check_imei():

    # ── GET → render the check page ──────────────
    if request.method == "GET":
        return render_template("check.html", active_page="check")

    # ── POST → run IMEI check logic ───────────────
    imei             = request.form.get("imei", "").strip()
    image            = request.files.get("image")
    detection_method = None   # "barcode" | "ocr" | None (manual)

    # ── Option 1: Image uploaded → OCR / barcode ─
    if image and image.filename != "":

        result, error = _process_uploaded_image(image)

        if error:
            return render_template("check.html", active_page="check", error=error)

        imei             = result.get("imei_1")
        detection_method = result.get("detection_method")

        # imei_1 must be found for the check to proceed
        if not imei:
            return render_template("check.html",
                                   error="Could not extract a valid IMEI from the image.")

    # ── Option 2: Manual IMEI entry ──────────────
    else:
        if not imei:
            return render_template("check.html", active_page="check", error="No IMEI provided.")

    # ── Validate IMEI: length + Luhn ─────────────
    error = validate_imei(imei, "IMEI")
    if error:
        return render_template("check.html", active_page="check", error=error)

    # ── Log the search ────────────────────────────
    log_search(imei)

    # ── Classify the device ───────────────────────
    # Returns a string ("clean" / "suspicious") or a dict when stolen
    classification = classify_device(imei)

    if isinstance(classification, dict):
        # Stolen — check for location warning
        place        = classification.get("place_of_theft")
        area_warning = None
        if place:
            theft_count = count_thefts_in_location(place)
            if theft_count >= 3:
                area_warning = f"⚠️ Multiple thefts reported recently in {place}. Be cautious."

        return render_template("result.html", active_page=None,
                               imei=imei,
                               status="stolen",
                               detection_method=detection_method,
                               report=classification,
                               area_warning=area_warning)
    else:
        # Clean or suspicious — no report details
        return render_template("result.html", active_page=None,
                               imei=imei,
                               status=classification,
                               detection_method=detection_method,
                               report=None,
                               area_warning=None)


# GET /report — Show report form
@app.route("/report", methods=["GET"])
def report_page():
    return render_template("report.html", active_page="report")


# ─────────────────────────────────────────────
# Authentication credentials (change for production)
# ─────────────────────────────────────────────
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"


# POST /login — Validate credentials (called by modal via fetch)
# Returns JSON so the modal can handle success/failure without a page reload
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["user"] = username
        session["role"] = "admin"
        return jsonify({"success": True, "redirect": url_for("dashboard")})

    return jsonify({"success": False, "error": "Invalid username or password."}), 401


# GET /logout — Clear session and return home
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# GET /dashboard — Admin dashboard
@app.route("/dashboard", methods=["GET"])
def dashboard():
    if not session.get("user"):
        return redirect(url_for("home") + "?login=1")
    return render_template("dashboard.html",
                           active_page="dashboard",
                           recent_reports=get_recent_reports(),
                           recent_searches=get_recent_searches(),
                           top_locations=get_top_locations(),
                           total_reports=get_total_reports(),
                           total_checks=get_total_checks(),
                           total_locations=get_unique_locations())


# POST /report — Submit a stolen phone report
@app.route("/report", methods=["POST"])
def report_phone():

    # ── Read and trim required fields ────────────
    imei_1       = request.form.get("imei_1",       "").strip()
    owner_name   = trim(request.form.get("owner_name",   ""), MAX_OWNER_NAME)
    phone_number = request.form.get("phone_number", "").strip()
    email        = trim(request.form.get("email", ""), MAX_EMAIL)

    # ── Read and trim optional fields ────────────
    model_name     = trim(request.form.get("model_name",     ""), MAX_MODEL_NAME)
    color          = trim(request.form.get("color",          ""), MAX_COLOR)
    place_of_theft = trim(request.form.get("place_of_theft", ""), MAX_PLACE_OF_THEFT)

    # ── Validate required: empty field guards ────
    if not imei_1:
        return render_template("report.html", active_page="report", error="Primary IMEI is required.")
    if not owner_name:
        return render_template("report.html", active_page="report", error="Owner name is required.")
    if not phone_number:
        return render_template("report.html", active_page="report", error="Phone number is required.")
    if not email:
        return render_template("report.html", active_page="report", error="Email address is required.")

    # ── Validate IMEI_1: format + Luhn ───────────
    error = validate_imei(imei_1, "Primary IMEI")
    if error:
        return render_template("report.html", active_page="report", error=error)

    # ── Validate phone number ─────────────────────
    error = validate_phone_number(phone_number)
    if error:
        return render_template("report.html", active_page="report", error=error)

    # ── Validate email format ─────────────────────
    error = validate_email(email)
    if error:
        return render_template("report.html", active_page="report", error=error)

    # ── Save to database ──────────────────────────
    success, message = report_stolen(
        imei_1         = imei_1,
        owner_name     = owner_name,
        phone_number   = phone_number,
        email          = email,
        model_name     = model_name     or None,
        color          = color          or None,
        place_of_theft = place_of_theft or None
    )

    if not success:
        return render_template("report.html", active_page="report", error=message)

    # Build report dict to display on result page
    stolen_report = {
        "status":         "stolen",
        "owner_name":     owner_name,
        "phone_number":   phone_number,
        "email":          email,
        "model_name":     model_name     or None,
        "color":          color          or None,
        "place_of_theft": place_of_theft or None,
        "reported_at":    None,   # just submitted — DB timestamp not needed here
    }

    # Check for area warning based on submitted place_of_theft
    area_warning = None
    if place_of_theft:
        theft_count = count_thefts_in_location(place_of_theft)
        if theft_count >= 3:
            area_warning = f"⚠️ Multiple thefts reported recently in {place_of_theft}. Be cautious."

    return render_template("result.html", active_page=None,
                           imei=imei_1,
                           status="stolen",
                           detection_method=None,
                           report=stolen_report,
                           area_warning=area_warning)


# GET /api/stats — Analytics API for dashboard
# Returns live stats as JSON using existing database functions
@app.route("/api/stats", methods=["GET"])
def api_stats():
    top_locations = get_top_locations(limit=5)

    return jsonify({
        "total_checks":  get_total_checks(),
        "total_reports": get_total_reports(),
        "top_cities": [
            {"city": loc["location"], "count": loc["count"]}
            for loc in top_locations
        ]
    })


# ── Admin: PUT /api/reports/<id> — update a stolen report ──
@app.route("/api/reports/<int:report_id>", methods=["PUT"])
def api_update_report(report_id):
    if not session.get("user"):
        return jsonify({"error": "Unauthorised"}), 401
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden — admin only"}), 403

    data           = request.get_json(silent=True) or {}
    imei_1         = data.get("imei_1",         "").strip()
    model_name     = data.get("model_name",     "").strip()
    place_of_theft = data.get("place_of_theft", "").strip()
    reported_at    = data.get("reported_at",    "").strip()

    if not imei_1:
        return jsonify({"error": "Primary IMEI is required."}), 400

    success, message = update_report(report_id, imei_1, model_name, place_of_theft, reported_at)
    status_code = 200 if success else 404
    return jsonify({"success": success, "message": message}), status_code


# ── Admin: DELETE /api/reports/<id> — delete a stolen report ──
@app.route("/api/reports/<int:report_id>", methods=["DELETE"])
def api_delete_report(report_id):
    if not session.get("user"):
        return jsonify({"error": "Unauthorised"}), 401
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden — admin only"}), 403

    success, message = delete_report(report_id)
    status_code = 200 if success else 404
    return jsonify({"success": success, "message": message}), status_code


# GET /api/export — Download dashboard data as CSV
# Protected: only accessible to logged-in users
@app.route("/api/export", methods=["GET"])
def api_export():
    if not session.get("user"):
        return jsonify({"error": "Unauthorised"}), 401

    # ── Fetch all data ────────────────────────
    reports  = get_recent_reports(limit=1000)
    searches = get_recent_searches(limit=1000)

    # ── Build CSV in memory ───────────────────
    output = io.StringIO()
    writer = csv.writer(output)

    # Section 1: Stolen Reports
    writer.writerow(["--- Stolen Reports ---"])
    writer.writerow(["IMEI", "Model", "Location", "Reported At"])
    for r in reports:
        writer.writerow([
            r.get("imei_1",        ""),
            r.get("model_name",    ""),
            r.get("place_of_theft",""),
            r.get("reported_at",   ""),
        ])

    # Blank separator row
    writer.writerow([])

    # Section 2: IMEI Searches
    writer.writerow(["--- IMEI Searches ---"])
    writer.writerow(["IMEI", "Searched At"])
    for s in searches:
        writer.writerow([
            s.get("imei",        ""),
            s.get("searched_at", ""),
        ])

    # ── Return as downloadable file ───────────
    output.seek(0)
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=dashboard_data.csv"}
    )


# ─────────────────────────────────────────────
# Run the app
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)