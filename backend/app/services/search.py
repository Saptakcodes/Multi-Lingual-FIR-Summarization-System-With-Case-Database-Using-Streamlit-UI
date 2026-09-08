import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path("fir_metadata.db")

# -------------------------------------------------------------
# 1. Database init & record insertion (unchanged)
# -------------------------------------------------------------
def init_db():
    """Initialize SQLite database with the FIR schema."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS firs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fir_number TEXT,
        police_station TEXT,
        district TEXT,
        fir_date TEXT,
        fir_time TEXT,
        incident_date TEXT,
        incident_time TEXT,
        legal_sections TEXT,
        complainant TEXT,
        complainant_father TEXT,
        address TEXT,
        accused TEXT,
        property TEXT,
        total_value TEXT,
        summary TEXT,
        ocr_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def save_fir_record(fir_number, police_station, district, fir_date, fir_time,
                    incident_date, incident_time, legal_sections,
                    complainant, complainant_father, address,
                    accused, property, total_value, summary, ocr_text):
    """Insert a new FIR record into the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO firs (
        fir_number, police_station, district, fir_date, fir_time,
        incident_date, incident_time, legal_sections,
        complainant, complainant_father, address,
        accused, property, total_value, summary, ocr_text
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (fir_number, police_station, district, fir_date, fir_time,
         incident_date, incident_time, legal_sections,
         complainant, complainant_father, address,
         accused, property, total_value, summary, ocr_text))
    conn.commit()
    conn.close()

# -------------------------------------------------------------
# 2. Legacy search functions (unchanged)
# -------------------------------------------------------------
def search_by_fir_number(fir_number):
    """Retrieve FIR records by FIR number (partial match)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM firs WHERE fir_number LIKE ?", (f'%{fir_number}%',))
    results = c.fetchall()
    conn.close()
    return results

def search_by_name(name):
    """Search FIRs by complainant, accused, or summary (partial match)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT * FROM firs 
        WHERE complainant LIKE ? 
           OR accused LIKE ? 
           OR summary LIKE ?
    """, (f'%{name}%', f'%{name}%', f'%{name}%'))
    results = c.fetchall()
    conn.close()
    return results

# -------------------------------------------------------------
# 3. Date normalisation (with logging)
# -------------------------------------------------------------
def normalise_date(date_str: Optional[str]) -> Optional[datetime.date]:
    """
    Convert a date string to a Python date object.
    Supports DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, etc.
    Returns None if parsing fails.
    """
    if not date_str:
        return None
    date_str = date_str.strip()
    if date_str.lower() in ('not explicitly stated', 'nan', 'null', ''):
        return None
    # Try common formats
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d.%m.%Y'):
        try:
            parsed = datetime.strptime(date_str, fmt).date()
            logger.debug(f"Parsed '{date_str}' as {parsed}")
            return parsed
        except ValueError:
            continue
    logger.warning(f"Could not parse date: '{date_str}'")
    return None

# -------------------------------------------------------------
# 4. Advanced filter – core of the new functionality
# -------------------------------------------------------------
def advanced_search(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Perform an advanced search with multiple optional filters.

    Supported filters:
        fir_number, police_station, district, complainant,
        complainant_father, accused, legal_sections, summary
        start_date, end_date, date_field ('incident_date' or 'fir_date')

    Returns a list of dictionaries (each record).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = "SELECT * FROM firs WHERE 1=1"
    params = []

    # Text filters (SQL LIKE)
    text_fields = ['fir_number', 'police_station', 'district',
                   'complainant', 'complainant_father', 'accused',
                   'legal_sections', 'summary']
    for field in text_fields:
        val = filters.get(field)
        if val:
            query += f" AND {field} LIKE ?"
            params.append(f"%{val}%")

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    # Convert rows to dicts
    columns = ["id", "fir_number", "police_station", "district", "fir_date", "fir_time",
               "incident_date", "incident_time", "legal_sections", "complainant",
               "complainant_father", "address", "accused", "property", "total_value",
               "summary", "ocr_text", "created_at"]
    records = [dict(zip(columns, row)) for row in rows]

    # Determine which date field to filter on
    date_field = filters.get('date_field', 'incident_date')
    if date_field not in ('incident_date', 'fir_date'):
        date_field = 'incident_date'

    start_date_str = filters.get('start_date')
    end_date_str = filters.get('end_date')
    start_date = normalise_date(start_date_str) if start_date_str else None
    end_date = normalise_date(end_date_str) if end_date_str else None

    # If no date filter, return all records
    if start_date is None and end_date is None:
        return records

    # Apply date filter in Python (robust with various formats)
    filtered = []
    for rec in records:
        rec_date_str = rec.get(date_field)
        rec_date = normalise_date(rec_date_str)
        if rec_date is None:
            # If a date filter is active, skip records with invalid/missing dates
            # because they cannot be compared meaningfully.
            if start_date or end_date:
                logger.warning(f"Record {rec.get('id')} has unparseable date '{rec_date_str}' – excluding it because date filter is active.")
                continue
            else:
                # If no date filter, keep it (this case is already handled above,
                # but kept for safety)
                filtered.append(rec)
                continue
        include = True
        if start_date and rec_date < start_date:
            include = False
        if end_date and rec_date > end_date:
            include = False
        if include:
            filtered.append(rec)
    logger.info(f"Date filter: start={start_date}, end={end_date}, kept {len(filtered)} of {len(records)} records")
    return filtered

# -------------------------------------------------------------
# 5. Backward‑compatible wrapper for the old filter_firs
# -------------------------------------------------------------
def filter_firs(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Backward‑compatible wrapper for advanced_search (used by /filter)."""
    return advanced_search(filters)