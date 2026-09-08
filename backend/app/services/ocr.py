import os
import re
import logging
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

# Absolute paths
BASE_DIR = r"C:\Multi-lingual-FIR-Summarizer-System\backend\tessaract_ocr"
TESSERACT_PATH = os.path.join(BASE_DIR, "tesseract.exe")
TESSDATA_DIR = os.path.join(BASE_DIR, "tessdata")
POPPLER_PATH = r"C:\Multi-lingual-FIR-Summarizer-System\backend\poppler\poppler-26.02.0\Library\bin"

# ------------------------------------------------------------------
# 1. OCR Extraction (Tesseract) – your working version
# ------------------------------------------------------------------
def extract_text(file_path):
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    try:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

        # Set environment variable for Tesseract data
        os.environ['TESSDATA_PREFIX'] = BASE_DIR  # parent of tessdata

        if file_ext == '.pdf':
            images = convert_from_path(file_path, poppler_path=POPPLER_PATH)
        else:
            images = [Image.open(file_path)]

        full_text = []
        for img in images:
            # Explicitly set tessdata-dir in config (no quotes)
            config = f"--tessdata-dir {TESSDATA_DIR}"
            text = pytesseract.image_to_string(img, lang='ben+hin+eng', config=config)
            full_text.append(text.strip())
        return "\n".join(full_text)

    except Exception as e:
        logger.error(f"OCR error: {e}")
        return f"[OCR Error: {str(e)}]"

# ------------------------------------------------------------------
# 2. Metadata Extraction (Regex) – for database storage
# ------------------------------------------------------------------
def extract_metadata(text):
    """Extract structured fields from OCR text using regex."""
    metadata = {}
    
    def clean(val):
        return val.strip() if val else "Not explicitly stated"

    # FIR Number
    match = re.search(r'FIR\s*(?:No\.?|Number)\s*[:.]?\s*([A-Za-z0-9\-/]+)', text, re.IGNORECASE)
    if not match:
        match = re.search(r'FIR\s*No\.?\s*\(प्र\.सू\.रि\.\s*सं\.\)\s*:\s*(\d+)', text, re.IGNORECASE)
    metadata["FIR Number"] = clean(match.group(1)) if match else "Not explicitly stated"

    # Police Station
    match = re.search(r'Police\s*Station\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:Year|Date|FIR|\d))', text, re.IGNORECASE)
    if not match:
        match = re.search(r'P\.?S\.?\s*\(थाना\)\s*:\s*([A-Za-z\s]+?)(?=\s*(?:Year|Date|FIR|\d))', text, re.IGNORECASE)
    metadata["Police Station"] = clean(match.group(1)) if match else "Not explicitly stated"

    # District
    match = re.search(r'District\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*P\.?S\.?)', text, re.IGNORECASE)
    if not match:
        match = re.search(r'District\s*\(जिला\)\s*:\s*([A-Za-z\s]+?)(?=\s*P\.?S\.?)', text, re.IGNORECASE)
    metadata["District"] = clean(match.group(1)) if match else "Not explicitly stated"

    # FIR Date & Time
    match = re.search(r'Date and Time of FIR.*?[:.]?\s*([\d/]+\s+[\d:]+\s*hrs?)', text, re.IGNORECASE | re.DOTALL)
    if not match:
        match = re.search(r'Date and Time of FIR\s*\(प्र\.सू\.रि\.\s*की\s*दिनांक और समय\)\s*:\s*([\d/]+\s+[\d:]+\s*hrs)', text, re.IGNORECASE | re.DOTALL)
    if match:
        parts = match.group(1).split()
        metadata["FIR Date"] = clean(parts[0]) if parts else "Not explicitly stated"
        metadata["FIR Time"] = clean(" ".join(parts[1:])) if len(parts) > 1 else "Not explicitly stated"
    else:
        metadata["FIR Date"] = "Not explicitly stated"
        metadata["FIR Time"] = "Not explicitly stated"

    # Incident Date & Time
    match = re.search(r'Date from\s*[:.]?\s*([\d/]+)', text, re.IGNORECASE)
    if not match:
        match = re.search(r'Date from\s*\(दिनांक से\)\s*:\s*([\d/]+)', text, re.IGNORECASE)
    metadata["Incident Date"] = clean(match.group(1)) if match else "Not explicitly stated"

    match = re.search(r'Time From\s*[:.]?\s*([\d:]+\s*hrs?)', text, re.IGNORECASE)
    if not match:
        match = re.search(r'Time From\s*\(समय से\)\s*:\s*([\d:]+\s*hrs)', text, re.IGNORECASE)
    metadata["Incident Time"] = clean(match.group(1)) if match else "Not explicitly stated"

    # Legal Sections
    match = re.search(r'(?:THE\s+BHARATIYA\s+NYAYA\s+SANHITA|IPC|BNS)\s*([\d(\)]+)', text, re.IGNORECASE)
    if not match:
        match = re.search(r'u/s\s*([\d(\)]+)', text, re.IGNORECASE)
    metadata["Legal Sections"] = clean(match.group(1)) if match else "Not explicitly stated"

    # Complainant Name
    match = re.search(r'Complainant\s*[:.]?\s*([^\n]+?)(?=\s*(?:Father|Address|\d))', text, re.IGNORECASE)
    if not match:
        match = re.search(r'Name\s*\(नाम\)\s*:\s*([^F]+?)(?=\s*Father)', text, re.IGNORECASE)
    metadata["Complainant Name"] = clean(match.group(1)) if match else "Not explicitly stated"

    # Complainant Father
    match = re.search(r'(?:Father\'?s Name|Father)\s*[:.]?\s*([A-Za-z\.\s]+?)(?=\s*(?:Nationality|Address|$))', text, re.IGNORECASE)
    if not match:
        match = re.search(r'Father\'?s Name\s*\(पिताका नाम\)\s*:\s*([A-Za-z\.\s]+?)(?=\s*\(d\)|Nationality|$)', text, re.IGNORECASE)
    metadata["Complainant Father"] = clean(match.group(1)) if match else "Not explicitly stated"

    # Address
    match = re.search(r'Address\s*[:.]?\s*([^,]+?,\s*[A-Z0-9\s\-]+?)(?=\s*(?:$|\d))', text, re.IGNORECASE)
    if not match:
        match = re.search(r'Address\s*\(पता\)\s*:\s*([^,]+?,\s*[A-Z0-9\s\-]+?)(?=\s*\(c\)|$)', text, re.IGNORECASE)
    metadata["Address"] = clean(match.group(1)) if match else "Not explicitly stated"

    # Accused
    match = re.search(r'Accused\s*[:.]?\s*([A-Za-z\.\s]+?)(?=\s*(?:Alias|Address|$))', text, re.IGNORECASE)
    if not match:
        match = re.search(r'Name\s*\(नाम\)\s*:\s*([A-Za-z\.\s]+)', text.split("7.")[-1] if "7." in text else text, re.IGNORECASE)
    metadata["Accused"] = clean(match.group(1)) if match else "Not explicitly stated"

    # Property
    props = re.findall(r'(?:INVOLVED IN A\s+)([A-Z\s]+?)(?=\s*\.?\d|\s*CASE/CRIME|$)', text, re.IGNORECASE)
    if not props:
        props = re.findall(r'(Gold|Silver|Jewellery|Currency|Coin|Property)', text, re.IGNORECASE)
    metadata["Property"] = ", ".join([p.strip() for p in props]) if props else "Not explicitly stated"

    # Total Value
    match = re.search(r'Total value.*?[:.]?\s*([\d,]+)', text, re.IGNORECASE | re.DOTALL)
    if not match:
        match = re.search(r'Rs\s*([\d,]+)/?', text, re.IGNORECASE)
    metadata["Total Value (Rs)"] = clean(match.group(1)) if match else "Not explicitly stated"

    return metadata