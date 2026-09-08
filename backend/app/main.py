import os
import re
import shutil
import aiofiles
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from .services.summarizer import Summarizer
from .services.ocr import extract_text, extract_metadata
from .services.translator import translate_text
from .services.search import init_db, save_fir_record, search_by_fir_number, search_by_name
from .utils.file_cleanup import cleanup_temp
from .models import SummarizeResponse, SearchResponse, FilterRequest
import logging
from typing import Optional
from .services.search import filter_firs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FIR Summarizer API", version="1.0.0")

summarizer = None

def extract_narrative(ocr_text):
    patterns = [
        r'First\s+Information\s+contents\s*[:.]?\s*(.*?)(?=\s*Action\s+taken|\s*13\.|\s*14\.|$)',
        r'FIR\s+Contents\s*[:.]?\s*(.*?)(?=\s*Action\s+taken|\s*13\.|\s*14\.|$)',
        r'12\.\s*FIR\s+Contents\s*[:.]?\s*(.*?)(?=\s*Action\s+taken|\s*13\.|\s*14\.|$)',
        r'12\.\s*First\s+Information\s+contents\s*[:.]?\s*(.*?)(?=\s*Action\s+taken|\s*13\.|\s*14\.|$)',
        r'Contents\s*[:.]?\s*(.*?)(?=\s*Action\s+taken|\s*13\.|\s*14\.|$)',
        r'Complaint\s*[:.]?\s*(.*?)(?=\s*Action\s+taken|\s*13\.|\s*14\.|$)',
        r'Alleged\s*[:.]?\s*(.*?)(?=\s*Action\s+taken|\s*13\.|\s*14\.|$)',
        r'Narrative\s*[:.]?\s*(.*?)(?=\s*Action\s+taken|\s*13\.|\s*14\.|$)',
    ]
    for pat in patterns:
        match = re.search(pat, ocr_text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    return ocr_text[:1500]

@app.on_event("startup")
async def load_model():
    global summarizer
    model_path = os.getenv("MODEL_PATH", "./models/qwen-fir-summarizer-final")
    logger.info(f"Loading model from {model_path}...")
    summarizer = Summarizer(model_path)
    logger.info("✅ Summarizer loaded successfully.")
    init_db()

@app.get("/")
async def root():
    return {"message": "FIR Summarizer API is running"}

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": summarizer is not None}

@app.post("/summarize")
async def summarize_fir(
    file: UploadFile = File(...),
    translate_to: str = Form("none")
):
    if summarizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    temp_path = f"./tmp/{file.filename}"
    os.makedirs("./tmp", exist_ok=True)
    async with aiofiles.open(temp_path, "wb") as f:
        content = await file.read()
        await f.write(content)
    try:
        logger.info(f"Extracting text from {file.filename}...")
        ocr_text = extract_text(temp_path)
        if not ocr_text or len(ocr_text) < 10:
            raise HTTPException(status_code=400, detail="Could not extract text from file")
        narrative = extract_narrative(ocr_text)
        if not narrative or len(narrative) < 10:
            narrative = ocr_text[:1500]
            logger.warning("Narrative extraction failed – using raw OCR text.")
        logger.info("Generating summary...")
        summary = summarizer.generate(narrative)
        translated_summary = None
        lang_map = {
            "bn": "bn", "ben": "bn",
            "hi": "hi",
            "te": "te",
            "ta": "ta",
            "or": "or",
            "mr": "mr",
            "gu": "gu",
            "kn": "kn",
            "ml": "ml",
            "pa": "pa"
        }
        if translate_to in lang_map:
            target_lang = lang_map[translate_to]
            logger.info(f"Translating summary to {target_lang}...")
            try:
                translated_summary = translate_text(summary, target=target_lang)
                if translated_summary:
                    logger.info(f"Translation result (first 100 chars): {translated_summary[:100]}...")
                else:
                    logger.warning("Translation returned None")
            except Exception as e:
                logger.error(f"Translation error: {e}")
                translated_summary = None
        try:
            metadata = extract_metadata(ocr_text)
            save_fir_record(
                fir_number=metadata.get("FIR Number", "Not available"),
                police_station=metadata.get("Police Station", "Not available"),
                district=metadata.get("District", "Not available"),
                fir_date=metadata.get("FIR Date", "Not available"),
                fir_time=metadata.get("FIR Time", "Not available"),
                incident_date=metadata.get("Incident Date", "Not available"),
                incident_time=metadata.get("Incident Time", "Not available"),
                legal_sections=metadata.get("Legal Sections", "Not available"),
                complainant=metadata.get("Complainant Name", "Not available"),
                complainant_father=metadata.get("Complainant Father", "Not available"),
                address=metadata.get("Address", "Not available"),
                accused=metadata.get("Accused", "Not available"),
                property=metadata.get("Property", "Not available"),
                total_value=metadata.get("Total Value (Rs)", "Not available"),
                summary=summary,
                ocr_text=ocr_text
            )
            logger.info("✅ FIR record saved to database.")
        except Exception as e:
            logger.error(f"Failed to save to DB: {e}")
        return {
            "original_text": ocr_text,
            "narrative": narrative,
            "summary": summary,
            "translated_summary": translated_summary,
            "target_language": translate_to if translate_to != "none" else None
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cleanup_temp(temp_path)

# ----- CLEANING FUNCTION REMOVED / DISABLED -----
# The frontend now handles sanitisation, so we no longer filter rows here.
# If a stray header row exists, the frontend's sanitize_results will remove it.
# (Keeping this comment for clarity.)

@app.get("/fir/{fir_number}")
async def get_fir_by_number(fir_number: str):
    results = search_by_fir_number(fir_number)
    if not results:
        raise HTTPException(status_code=404, detail="FIR not found")
    columns = ["id", "fir_number", "police_station", "district", "fir_date", "fir_time",
               "incident_date", "incident_time", "legal_sections", "complainant",
               "complainant_father", "address", "accused", "property", "total_value",
               "summary", "ocr_text", "created_at"]
    firs = [dict(zip(columns, row)) for row in results]
    # No cleaning – frontend will handle any stray rows
    return {"firs": firs}

@app.post("/search")
async def search_firs(name: str):
    results = search_by_name(name)
    columns = ["id", "fir_number", "police_station", "district", "fir_date", "fir_time",
               "incident_date", "incident_time", "legal_sections", "complainant",
               "complainant_father", "address", "accused", "property", "total_value",
               "summary", "ocr_text", "created_at"]
    firs = [dict(zip(columns, row)) for row in results]
    # No cleaning – frontend will handle any stray rows
    return {"results": firs}

@app.post("/filter")
async def advanced_filter(filters: FilterRequest):
    """Advanced filter by number, name, and date range (JSON body)."""
    filters_dict = filters.dict()
    logger.info(f"Received filters: {filters_dict}")
    results = filter_firs(filters_dict)
    logger.info(f"Raw results from filter_firs: {len(results)} records")
    # results are already dicts – no cleaning applied
    logger.info(f"Returning {len(results)} records (no cleaning)")
    return {"results": results}