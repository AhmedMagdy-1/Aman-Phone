import sqlite3
from datetime import datetime, timedelta

# Path to the SQLite database file
DATABASE = "aman.db"


# ─────────────────────────────────────────────
# Get a database connection
# ─────────────────────────────────────────────
def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row   # allows accessing columns by name
    return conn


# ─────────────────────────────────────────────
# 1. Initialize the database (create tables)
# ─────────────────────────────────────────────
def init_db():
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Table 1: devices
        # Stores full stolen device reports with owner details
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id             INTEGER  PRIMARY KEY AUTOINCREMENT,

                -- Required fields
                imei_1         TEXT     NOT NULL UNIQUE,   -- primary IMEI (15 digits)
                owner_name     TEXT     NOT NULL,
                phone_number   TEXT     NOT NULL,
                email          TEXT     NOT NULL,

                -- Optional fields
                model_name     TEXT,
                color          TEXT,
                place_of_theft TEXT,

                -- Status & timestamp
                status         TEXT     NOT NULL DEFAULT 'stolen',
                reported_at    DATETIME NOT NULL
            )
        """)

        # Index on imei_1 for fast lookups (UNIQUE already creates one,
        # but we add imei_2 explicitly since it is not UNIQUE)
        # Table 2: search_logs
        # Tracks every IMEI lookup (used for suspicion detection)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_logs (
                id          INTEGER  PRIMARY KEY AUTOINCREMENT,
                imei        TEXT     NOT NULL,
                searched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index on search_logs.imei for fast 24-hour count queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_logs_imei
            ON search_logs (imei)
        """)

        conn.commit()
        print("Database initialized successfully.")

    except Exception as e:
        print(f"Error initializing database: {e}")

    finally:
        conn.close()


# ─────────────────────────────────────────────
# Helper: validate that a value is exactly 15 digits
# ─────────────────────────────────────────────
def is_valid_imei(imei):
    return imei is not None and imei.isdigit() and len(imei) == 15


# ─────────────────────────────────────────────
# 2. Log a search (every time a user checks an IMEI)
# ─────────────────────────────────────────────
def log_search(imei):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO search_logs (imei, searched_at)
            VALUES (?, ?)
        """, (imei, datetime.now()))
        conn.commit()

    except Exception as e:
        print(f"Error logging search: {e}")

    finally:
        conn.close()


# ─────────────────────────────────────────────
# 3. Report a stolen device
# Required : imei_1, owner_name, phone_number, email
# Optional : model_name, color, place_of_theft
# Returns  : (success: bool, message: str)
# ─────────────────────────────────────────────
def report_stolen(imei_1, owner_name, phone_number, email,
                  model_name=None, color=None, place_of_theft=None):

    # ── Validate required IMEI_1 ─────────────
    if not is_valid_imei(imei_1):
        return False, "Primary IMEI must be exactly 15 digits."

    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Prevent duplicate reports for the same primary IMEI
        cursor.execute("SELECT id FROM devices WHERE imei_1 = ?", (imei_1,))
        if cursor.fetchone():
            return False, "This IMEI has already been reported as stolen."

        # Insert new stolen report
        cursor.execute("""
            INSERT INTO devices (
                imei_1, owner_name, phone_number, email,
                model_name, color, place_of_theft,
                status, reported_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'stolen', ?)
        """, (
            imei_1, owner_name, phone_number, email,
            model_name or None,
            color or None,
            place_of_theft or None,
            datetime.now()
        ))

        conn.commit()
        return True, "Device reported as stolen successfully."

    except Exception as e:
        print(f"Error reporting stolen device: {e}")
        return False, "A database error occurred. Please try again."

    finally:
        conn.close()


# ─────────────────────────────────────────────
# 4. Get the status of a device by IMEI
# Checks imei_1 
# Returns: 'stolen' or 'clean'
# ─────────────────────────────────────────────
def get_device_status(imei):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Search in both IMEI columns
        cursor.execute("""
            SELECT status FROM devices
            WHERE imei_1 = ?
        """, (imei,))

        row = cursor.fetchone()

        if row:
            return row["status"]    # 'stolen'
        return "clean"              # not found = clean by default

    except Exception as e:
        print(f"Error getting device status: {e}")
        return "clean"              # safe default on error

    finally:
        conn.close()



# ─────────────────────────────────────────────
# 4b. Get full stolen report details by IMEI
# Checks imei_1 
# Returns: dict with report fields, or None if not found
# ─────────────────────────────────────────────
def get_stolen_report(imei):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                owner_name, phone_number, email,
                model_name, color, place_of_theft,
                reported_at
            FROM devices
            WHERE imei_1 = ?
              AND status = 'stolen'
        """, (imei,))

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "owner_name":     row["owner_name"],
            "phone_number":   row["phone_number"],
            "email":          row["email"],
            "model_name":     row["model_name"],
            "color":          row["color"],
            "place_of_theft": row["place_of_theft"],
            "reported_at":    row["reported_at"],
        }

    except Exception as e:
        print(f"Error fetching stolen report: {e}")
        return None

    finally:
        conn.close()

# ─────────────────────────────────────────────
# 6. Count stolen reports in the same location
#    in the last 7 days
# Returns: int (count of reports)
# ─────────────────────────────────────────────
def count_thefts_in_location(place_of_theft):
    """
    Count how many stolen device reports share the same
    place_of_theft within the last 7 days.

    Used to trigger the area warning on the result page.
    Returns 0 if place_of_theft is None or empty.
    """
    if not place_of_theft:
        return 0

    conn = get_connection()
    try:
        cursor = conn.cursor()

        last_week = datetime.now() - timedelta(days=7)

        cursor.execute("""
            SELECT COUNT(*) AS theft_count
            FROM devices
            WHERE place_of_theft = ?
              AND status = 'stolen'
              AND reported_at >= ?
        """, (place_of_theft, last_week))

        row = cursor.fetchone()
        return row["theft_count"] if row else 0

    except Exception as e:
        print(f"Error counting location thefts: {e}")
        return 0

    finally:
        conn.close()


# ─────────────────────────────────────────────
# 5. Count how many times an IMEI was searched
#    in the last 24 hours
# ─────────────────────────────────────────────
def count_recent_searches(imei):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        yesterday = datetime.now() - timedelta(hours=24)

        cursor.execute("""
            SELECT COUNT(*) AS search_count
            FROM search_logs
            WHERE imei = ?
              AND searched_at >= ?
        """, (imei, yesterday))

        row = cursor.fetchone()
        return row["search_count"] if row else 0

    except Exception as e:
        print(f"Error counting recent searches: {e}")
        return 0                    # safe default on error

    finally:
        conn.close()


# ─────────────────────────────────────────────
# 7. Live statistics for the home page
# ─────────────────────────────────────────────

def get_total_reports():
    """Return the total count of stolen device reports."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM devices WHERE status = 'stolen'")
        row = cursor.fetchone()
        return row["total"] if row else 0
    except Exception as e:
        print(f"Error getting total reports: {e}")
        return 0
    finally:
        conn.close()


def get_total_checks():
    """Return the total count of all IMEI searches logged."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM search_logs")
        row = cursor.fetchone()
        return row["total"] if row else 0
    except Exception as e:
        print(f"Error getting total checks: {e}")
        return 0
    finally:
        conn.close()


def get_unique_locations():
    """Return the number of distinct place_of_theft values in stolen reports."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT place_of_theft) AS total
            FROM devices
            WHERE status = 'stolen'
              AND place_of_theft IS NOT NULL
              AND place_of_theft != ''
        """)
        row = cursor.fetchone()
        return row["total"] if row else 0
    except Exception as e:
        print(f"Error getting unique locations: {e}")
        return 0
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 8. Dashboard data queries
# ─────────────────────────────────────────────

def get_recent_reports(limit=10):
    """
    Return the most recently submitted stolen device reports.
    Ordered newest first. Returns a list of dicts.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, imei_1, model_name, place_of_theft, reported_at
            FROM   devices
            WHERE  status = 'stolen'
            ORDER  BY reported_at DESC
            LIMIT  ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching recent reports: {e}")
        return []
    finally:
        conn.close()


def get_recent_searches(limit=10):
    """
    Return the most recent IMEI search log entries.
    Ordered newest first. Returns a list of dicts.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT imei, searched_at
            FROM   search_logs
            ORDER  BY searched_at DESC
            LIMIT  ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching recent searches: {e}")
        return []
    finally:
        conn.close()


def get_top_locations(limit=5):
    """
    Return the most common places of theft from stolen reports.
    Only includes non-null, non-empty place_of_theft values.
    Returns a list of dicts with 'location' and 'count'.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT   place_of_theft AS location,
                     COUNT(*)       AS count
            FROM     devices
            WHERE    status = 'stolen'
              AND    place_of_theft IS NOT NULL
              AND    place_of_theft != ''
            GROUP BY place_of_theft
            ORDER BY count DESC
            LIMIT    ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching top locations: {e}")
        return []
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 9. Admin report management
# ─────────────────────────────────────────────

def update_report(report_id, imei_1, model_name, place_of_theft, reported_at):
    """
    Update an existing stolen report by its id.
    Only imei_1, model_name, place_of_theft and reported_at are editable.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE devices
            SET imei_1         = ?,
                model_name     = ?,
                place_of_theft = ?,
                reported_at    = ?
            WHERE id = ?
              AND status = 'stolen'
        """, (imei_1, model_name or None, place_of_theft or None, reported_at, report_id))

        if cursor.rowcount == 0:
            return False, "Report not found."

        conn.commit()
        return True, "Report updated successfully."

    except Exception as e:
        print(f"Error updating report: {e}")
        return False, "Database error occurred."
    finally:
        conn.close()


def delete_report(report_id):
    """
    Permanently delete a stolen report by its id.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM devices WHERE id = ? AND status = 'stolen'", (report_id,))

        if cursor.rowcount == 0:
            return False, "Report not found."

        conn.commit()
        return True, "Report deleted successfully."

    except Exception as e:
        print(f"Error deleting report: {e}")
        return False, "Database error occurred."
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Run this file directly to initialize the DB
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()