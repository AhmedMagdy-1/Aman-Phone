from database import get_device_status, get_stolen_report, count_recent_searches

# Threshold: number of searches within 24h to flag as suspicious
SUSPICIOUS_THRESHOLD = 5


# ─────────────────────────────────────────────
# Classify a device based on its IMEI
#
# Returns one of three shapes:
#   "clean"       → string
#   "suspicious"  → string
#   {             → dict (when stolen)
#     "status":        "stolen",
#     "owner_name":    ...,
#     "phone_number":  ...,
#     "email":         ...,
#     "model_name":    ...,
#     "color":         ...,
#     "place_of_theft":...,
#     "reported_at":   ...,
#   }
# ─────────────────────────────────────────────
def classify_device(imei):

    # Step 1: Check if the device is reported stolen
    status = get_device_status(imei)

    if status == "stolen":
        # Fetch full report details to pass to the result page
        report = get_stolen_report(imei)

        if report:
            return {
                "status":         "stolen",
                "owner_name":     report.get("owner_name"),
                "phone_number":   report.get("phone_number"),
                "email":          report.get("email"),
                "model_name":     report.get("model_name"),
                "color":          report.get("color"),
                "place_of_theft": report.get("place_of_theft"),
                "reported_at":    report.get("reported_at"),
            }

        # Fallback: report row missing — return status only
        return "stolen"

    # Step 2: Check if the device has been searched too many times lately
    recent_searches = count_recent_searches(imei)
    if recent_searches >= SUSPICIOUS_THRESHOLD:
        return "suspicious"

    # Step 3: No red flags — device is clean
    return "clean"