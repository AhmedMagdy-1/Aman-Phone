"""
ocr.py — IMEI Extraction Pipeline for AMAN PHONE
=================================================
Detection flow (in priority order):

  1. YOLOv8 (best.pt)  →  detect barcode / QR regions
  2. Crop each detected region
  3. pyzbar            →  decode barcode / QR
  4. find_imei_candidates()  →  extract 15-digit numeric sequences
  5. is_valid_luhn()   →  validate each candidate
  6. Return IMEI, and detection_method

"""

import os
import re
from PIL import Image
from validators import is_valid_luhn


# ─────────────────────────────────────────────
# Windows: ensure ZBar DLLs are on the path.
# Place libiconv.dll and libzbar-64.dll next to
# app.py before importing pyzbar.
# ─────────────────────────────────────────────
if os.name == "nt":
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.add_dll_directory(project_root)

try:
    from pyzbar.pyzbar import decode as decode_barcodes
    PYZBAR_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] pyzbar unavailable — barcode decoding disabled. Reason: {e}")
    PYZBAR_AVAILABLE = False


# ─────────────────────────────────────────────
# YOLOv8 — lazy-loaded singleton.
# The model is loaded once on the first image
# request, not at application startup.
# Place best.pt in the project root folder.
# ─────────────────────────────────────────────
_yolo_model = None


def _load_yolo():
    """Load YOLOv8 model once. Returns None if best.pt is missing."""
    global _yolo_model
    if _yolo_model is not None:
        return _yolo_model  # already loaded

    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.pt")
    if not os.path.exists(model_path):
        print("[INFO] best.pt not found — YOLO detection disabled.")
        return None

    try:
        from ultralytics import YOLO
        _yolo_model = YOLO(model_path)
        print("[INFO] YOLOv8 model loaded successfully.")
    except Exception as e:
        print(f"[WARNING] Failed to load YOLOv8: {e}")
        _yolo_model = None

    return _yolo_model


# ─────────────────────────────────────────────
# IMEI candidate extraction
# ─────────────────────────────────────────────

def find_imei_candidates(text):
    """
    Find all 15-digit numeric sequences in a decoded barcode string.

    Spaces are stripped first so barcodes like "354923 04 1234567"
    are still found.  Duplicates are removed and Luhn-valid candidates
    are sorted first.
    """
    cleaned  = text.replace(" ", "")
    matches  = re.findall(r"\d{15}", cleaned)

    # Deduplicate while preserving order
    seen, unique = set(), []
    for m in matches:
        if m not in seen:
            seen.add(m)
            unique.append(m)

    # Put Luhn-valid candidates first
    unique.sort(key=lambda x: (0 if is_valid_luhn(x) else 1))
    return unique


# ─────────────────────────────────────────────
# Barcode region cropping helper
# ─────────────────────────────────────────────

def _crop_regions(image_pil, boxes, padding=10):
    """
    Crop bounding-box regions from a PIL image.

    A small padding is added so the barcode is not cut too tight.
    Coordinates are clamped to the image boundaries.
    """
    w, h   = image_pil.size
    crops  = []
    for (x1, y1, x2, y2) in boxes:
        x1 = max(0, int(x1) - padding)
        y1 = max(0, int(y1) - padding)
        x2 = min(w, int(x2) + padding)
        y2 = min(h, int(y2) + padding)
        crops.append(image_pil.crop((x1, y1, x2, y2)))
    return crops


# ─────────────────────────────────────────────
# pyzbar decoding helper
# ─────────────────────────────────────────────

def _decode_barcodes_from_image(image_pil):
    """
    Run pyzbar on a PIL image and return all Luhn-valid IMEI candidates found.
    Returns an empty list if pyzbar is unavailable or no barcodes are found.
    """
    if not PYZBAR_AVAILABLE:
        return []
    try:
        decoded = decode_barcodes(image_pil)
    except Exception as e:
        print(f"[pyzbar] Decode error: {e}")
        return []

    candidates = []
    for code in decoded:
        raw_text = code.data.decode("utf-8", errors="ignore")
        for c in find_imei_candidates(raw_text):
            if is_valid_luhn(c) and c not in candidates:
                candidates.append(c)
    return candidates


# ─────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────

def extract_imei_from_image(image_path):
    """
    Extract IMEI from an uploaded image using the following pipeline:

    Stage 1 — YOLOv8 (primary):
        - Run best.pt to detect barcode/QR regions.
        - Crop each region (+10px padding).
        - Decode each crop with pyzbar.
        - Collect Luhn-valid IMEI candidates.
        detection_method: "yolo_barcode"

    Returns:
    {
        "imei_1":           str | None,
        "detection_method": "yolo_barcode" | "barcode" | None
    }
    """
    imei_candidates  = []
    detection_method = None

    try:
        image_pil = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"[ocr.py] Failed to open image: {e}")
        return {"imei_1": None, "detection_method": None}

    # ── Stage 1: YOLO → crop → pyzbar ────────
    model = _load_yolo()
    if model is not None:
        try:
            results = model(image_pil, verbose=False)

            boxes = []
            for result in results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    if float(box.conf[0]) >= 0.5:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        boxes.append((x1, y1, x2, y2))

            if boxes:
                crops = _crop_regions(image_pil, boxes)
                for crop in crops:
                    found = _decode_barcodes_from_image(crop)
                    for c in found:
                        if c not in imei_candidates:
                            imei_candidates.append(c)

                if imei_candidates:
                    detection_method = "yolo_barcode"

        except Exception as e:
            print(f"[YOLO] Inference error: {e}")


    return {
        "imei_1":           imei_candidates[0] if len(imei_candidates) >= 1 else None,
        "detection_method": detection_method
    }