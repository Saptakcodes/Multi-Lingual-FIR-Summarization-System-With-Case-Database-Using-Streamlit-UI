import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime, timedelta
import dateparser
from dateparser.search import search_dates
import calendar

# ==============================================================
# PAGE CONFIGURATION
# ==============================================================
st.set_page_config(
    page_title="FIR Sahayak | e-Police Summarization Desk",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND_URL = "http://localhost:8000"

LANG_NAMES = {
    "none": "English only",
    "bn": "বাংলা · Bengali",
    "hi": "हिन्दी · Hindi",
    "te": "తెలుగు · Telugu",
    "ta": "தமிழ் · Tamil",
    "or": "ଓଡ଼ିଆ · Odia",
    "mr": "मराठी · Marathi",
    "gu": "ગુજરાતી · Gujarati",
    "kn": "ಕನ್ನಡ · Kannada",
    "ml": "മലയാളം · Malayalam",
    "pa": "ਪੰਜਾਬੀ · Punjabi",
    "ur": "اردو · Urdu",
    "sa": "संस्कृतम् · Sanskrit",
}

TYPE_TAG = {"number": "🔢 NUMBER", "name": "👤 NAME", "all": "📋 REGISTER", "filter": "🔎 SMART"}

# ==============================================================
# SESSION STATE
# ==============================================================
defaults = {
    "messages": [],
    "summary_text": None,
    "translated_text": None,
    "processed_files": set(),
    "results_number": None,
    "results_name": None,
    "results_all": None,
    "results_filter": None,
    "search_history": [],
    "last_raw_response": None,
    "last_query": None,
    "last_search_type": None,
    "current_page": "💬 Duty Desk Chat",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==============================================================
# THEME — "Case File / Constabulary" design system (off-white)
# ==============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root{
    --ink:#0B2540;
    --ink-2:#123456;
    --ink-3:#1B4C78;
    --gold:#C6A15B;
    --gold-dark:#9C7C3B;
    --maroon:#7A1F2B;
    --maroon-dark:#5E141E;
    --paper:#F7F4EC;
    --paper-2:#EFEADB;
    --card:var(--paper-2);
    --text:#20262E;
    --muted:#5B6472;
    --hairline:#DBD3BE;
    --ok:#2F6D4F;
    --ok-bg:#E5F1EA;
    --err:#A3313C;
    --err-bg:#F7E6E7;
}

html, body, [class*="css"]{
    font-family:'Inter', sans-serif;
}
h1,h2,h3,h4, .dept-title, .page-title{
    font-family:'Roboto Slab', serif;
}
.mono, .fir-badge, .datetime, .history-item .time{
    font-family:'JetBrains Mono', monospace;
}

.stApp{
    background: var(--paper);
    color: var(--text);
}
header[data-testid="stHeader"]{ background: transparent; }
#MainMenu, footer {visibility:hidden;}

/* ---------- SIDEBAR ---------- */
section[data-testid="stSidebar"]{
    background: linear-gradient(180deg, var(--ink) 0%, var(--ink-2) 100%);
    color:#EDEFF2;
    border-right: 3px solid var(--gold);
}
section[data-testid="stSidebar"] *{ color:#EDEFF2 !important; }
section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small{
    color:#9FB1C6 !important;
}
.sb-crest{
    display:flex; align-items:center; gap:10px;
    padding:6px 0 2px 0;
}
.sb-crest .badge{
    width:42px;height:42px;border-radius:50%;
    background: radial-gradient(circle, var(--gold) 0%, var(--gold-dark) 100%);
    display:flex;align-items:center;justify-content:center;
    font-size:20px; box-shadow: 0 0 0 3px rgba(198,161,91,0.25);
}
.sb-crest .txt{ line-height:1.15; }
.sb-crest .txt .t1{ font-family:'Roboto Slab',serif; font-weight:700; font-size:15px; letter-spacing:0.5px;}
.sb-crest .txt .t2{ font-size:10.5px; color:#9FB1C6 !important; letter-spacing:1px; text-transform:uppercase;}

.sb-eyebrow{
    font-size:11px; letter-spacing:1.5px; text-transform:uppercase;
    color: var(--gold) !important; font-weight:600; margin: 14px 0 6px 0;
    border-bottom: 1px solid rgba(198,161,91,0.35); padding-bottom:5px;
}

/* Sidebar radio buttons */
section[data-testid="stSidebar"] div[role="radiogroup"] label{
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 8px 10px !important;
    margin-bottom: 6px;
    width: 100%;
    transition: all 0.15s ease;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover{
    background: rgba(198,161,91,0.18);
    border-color: var(--gold);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child{
    border-color:#9FB1C6 !important;
}

/* Sidebar selectbox (Translation Language) */
section[data-testid="stSidebar"] .stSelectbox > div > div{
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 8px !important;
    color: #EDEFF2 !important;
}
section[data-testid="stSidebar"] .stSelectbox > div > div > div{
    background: transparent !important;
    color: #EDEFF2 !important;
}
section[data-testid="stSidebar"] .stSelectbox > div > div > div input{
    color: #EDEFF2 !important;
}
/* Dropdown options (the popup) */
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="popover"]{
    background: var(--ink-2) !important;
    border: 1px solid var(--gold) !important;
}
section[data-testid="stSidebar"] .stSelectbox ul li{
    color: #EDEFF2 !important;
    background: transparent !important;
}
section[data-testid="stSidebar"] .stSelectbox ul li:hover{
    background: rgba(198,161,91,0.2) !important;
}

.status-pill{
    display:inline-flex; align-items:center; gap:6px;
    font-size:11.5px; font-weight:600; letter-spacing:0.3px;
    padding:4px 10px; border-radius:20px;
    font-family:'JetBrains Mono', monospace;
}
.status-pill.ok{ background: var(--ok-bg); color: var(--ok) !important; }
.status-pill.err{ background: var(--err-bg); color: var(--err) !important; }
.status-pill.ok::before{ content:"●"; }
.status-pill.err::before{ content:"●"; }

.history-item{
    background: rgba(255,255,255,0.06);
    border-left: 3px solid var(--gold);
    border-radius: 4px;
    padding: 6px 10px;
    margin-bottom: 6px;
}
.history-item.type-number{ border-left-color: var(--gold); }
.history-item.type-name{ border-left-color: #6E9BC7; }
.history-item.type-all{ border-left-color: var(--maroon); }
.history-item.type-filter{ border-left-color: #F4A460; }
.history-item .query{ font-weight:600; font-size:13px; display:block;}
.history-item .time{ font-size:10.5px; color:#9FB1C6 !important; }

section[data-testid="stSidebar"] .stButton button{
    background: rgba(198,161,91,0.14) !important;
    color:#F3E9D2 !important;
    border: 1px solid var(--gold) !important;
    border-radius: 20px !important;
    font-size:12.5px !important;
    font-weight:600 !important;
    padding: 5px 12px !important;
    box-shadow:none !important;
}
section[data-testid="stSidebar"] .stButton button:hover{
    background: var(--gold) !important;
    color: var(--ink) !important;
}
.clear-history-btn .stButton button{
    background: rgba(122,31,43,0.25) !important;
    border-color: var(--maroon) !important;
    color:#F3D6D9 !important;
}
.clear-history-btn .stButton button:hover{
    background: var(--maroon) !important;
    color:#fff !important;
}

/* ---------- LETTERHEAD ---------- */
.letterhead{
    display:flex; justify-content:space-between; align-items:center;
    background: linear-gradient(90deg, var(--ink) 0%, var(--ink-3) 100%);
    border-radius: 14px;
    padding: 18px 26px;
    box-shadow: 0 4px 18px rgba(11,37,64,0.25);
    border: 1px solid var(--gold);
}
.letterhead-left{ display:flex; align-items:center; gap:16px; }
.letterhead .crest{
    width:54px; height:54px; border-radius:50%;
    background: radial-gradient(circle, var(--gold) 0%, var(--gold-dark) 100%);
    display:flex; align-items:center; justify-content:center;
    font-size:28px; flex-shrink:0;
    box-shadow: 0 0 0 4px rgba(198,161,91,0.25);
}
.dept-title{ color:#fff; font-size:23px; font-weight:700; letter-spacing:1px; margin:0;}
.dept-subtitle{ color:#C9D4E0; font-size:12.5px; letter-spacing:0.3px; margin-top:2px;}
.letterhead-right{ text-align:right; }
.letterhead-right .datetime{ color:#C9D4E0; font-size:12px; margin-top:6px;}

/* ---------- PAGE HEADER ---------- */
.page-eyebrow{
    font-size:12px; letter-spacing:2px; text-transform:uppercase;
    color: var(--maroon); font-weight:700; margin-top:22px;
}
.page-title{
    font-size:26px; font-weight:700; color: var(--ink); margin: 2px 0 16px 0;
    border-bottom: 2px solid var(--hairline); padding-bottom:12px;
}

/* ---------- GENERIC WIDGETS ---------- */
.stButton button{
    background: linear-gradient(180deg, var(--ink-3) 0%, var(--ink) 100%);
    color: white !important;
    border: 1px solid var(--gold-dark);
    border-radius: 8px;
    font-weight: 600;
    padding: 9px 22px;
    transition: all 0.15s ease;
}
.stButton button:hover{
    background: var(--maroon);
    border-color: var(--maroon-dark);
    color:white !important;
    transform: translateY(-1px);
}
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div, .stNumberInput input{
    background: var(--paper) !important;
    color: var(--text) !important;
    border: 1px solid var(--hairline) !important;
    border-radius: 8px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus{
    border-color: var(--gold-dark) !important;
    box-shadow: 0 0 0 2px rgba(198,161,91,0.25) !important;
}
div[data-testid="stFileUploaderDropzone"]{
    background: var(--paper) !important;
    border: 2px dashed var(--gold-dark) !important;
    border-radius: 12px !important;
}
.dataframe{
    background: var(--paper) !important;
    border: 1px solid var(--hairline) !important;
    border-radius: 10px !important;
}
.dataframe th{ background: var(--ink) !important; color:white !important; }
.stAlert{
    background: var(--paper) !important;
    border: 1px solid var(--hairline) !important;
    border-radius: 10px !important;
}
div[data-testid="stExpander"]{
    background: var(--paper);
    border: 1px solid var(--hairline);
    border-radius: 10px;
}
[data-testid="stMetric"]{
    background: var(--paper);
    border: 1px solid var(--hairline);
    border-left: 4px solid var(--gold-dark);
    border-radius: 10px;
    padding: 12px 16px;
}

/* ---------- WORKFLOW RAIL ---------- */
.rail{ display:flex; gap:10px; margin: 4px 0 22px 0; }
.rail .step{
    flex:1; text-align:center; padding: 10px 6px; border-radius:10px;
    background: var(--paper); border:1px dashed var(--hairline);
    font-size:12.5px; font-weight:600; color: var(--muted);
}
.rail .step.done{
    background: var(--ok-bg); border: 1px solid var(--ok); color: var(--ok);
}
.rail .step .n{ display:block; font-family:'JetBrains Mono',monospace; font-size:11px; opacity:0.8;}

/* ---------- CHAT ---------- */
.chat-container{ padding: 6px 0; }
.msg-row{ display:flex; align-items:flex-start; gap:10px; margin: 12px 0; }
.msg-row.user{ flex-direction: row-reverse; }
.avatar{
    width:34px; height:34px; border-radius:50%; flex-shrink:0;
    display:flex; align-items:center; justify-content:center; font-size:16px;
}
.avatar.bot{ background: var(--ink); color: var(--gold); border:1px solid var(--gold-dark); }
.avatar.user{ background: var(--gold); color: var(--ink); }
.bubble{
    max-width: 68%; padding: 13px 17px; line-height:1.75; font-size:14.5px;
}
.bubble.bot{
    background: var(--paper); border:1px solid var(--hairline);
    border-radius: 4px 16px 16px 16px; color: var(--text);
}
.bubble.user{
    background: linear-gradient(135deg, var(--ink-3), var(--ink));
    color:white; border-radius:16px 4px 16px 16px;
}
.bubble strong{ color: var(--maroon); font-size:15px; display:block; margin: 8px 0 4px 0;}
.bubble.user strong{ color: var(--gold); }
.bubble strong:first-of-type{ margin-top:0; }

/* ---------- CASE CARDS ---------- */
.case-card{
    background: var(--paper);
    border: 1px solid var(--hairline);
    border-left: 5px solid var(--gold-dark);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 14px;
    position: relative;
}
.case-card .fir-badge{
    display:inline-block; background: var(--ink); color: var(--gold);
    font-weight:700; font-size:13px; padding: 3px 10px; border-radius:5px;
    letter-spacing:0.5px;
}
.case-card .stamp{
    position:absolute; top:14px; right:18px;
    border:2px solid var(--ok); color:var(--ok);
    font-family:'JetBrains Mono',monospace; font-weight:700; font-size:10.5px;
    padding:3px 9px; border-radius:6px; transform: rotate(6deg);
    letter-spacing:1px; opacity:0.85;
}
.case-card .field{ margin-top:8px; font-size:13.5px; }
.case-card .field b{ color: var(--ink); }

.summary-box{
    background: var(--paper);
    border: 1px solid var(--hairline);
    border-left: 5px solid var(--maroon);
    border-radius: 10px;
    padding: 18px 22px;
    margin: 10px 0;
    line-height:1.8; font-size:14.5px;
}
.summary-box strong{ color: var(--maroon); font-size:17px; display:block; margin-bottom:6px;}

.disclaimer{
    font-size:11.5px; color: var(--muted); text-align:center;
    margin-top: 30px; padding-top:14px; border-top:1px solid var(--hairline);
    letter-spacing:0.3px;
}
</style>
""", unsafe_allow_html=True)


# ==============================================================
# HELPERS
# ==============================================================
def now_str():
    return datetime.now().strftime("%H:%M")

def add_message(role, content):
    st.session_state.messages.append({"role": role, "content": content, "time": now_str()})

def check_backend():
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False

def extract_results(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "results" in data and isinstance(data["results"], list):
            return data["results"]
        for key in ["data", "firs", "items", "records"]:
            if key in data and isinstance(data[key], list):
                return data[key]
    return []

def safe(row, key):
    val = row.get(key, "Not available")
    return val if val not in (None, "", "nan") else "Not available"


# ==============================================================
# NATURAL LANGUAGE PARSER — ROBUST EDGE‑CASE HANDLING
# ==============================================================
def parse_natural_query(text):
    """
    Extract filters from natural language query.
    Supports all realistic date forms:
    - Explicit ranges: "between 1 Jan 2025 and 15 June 2025", "from June 2025 to Aug 2025"
    - Single dates: "15 June 2025", "June 2025", "2025"
    - Relative: "last week", "today", etc.
    - Mixed year presence: inherits year from the other date when missing.
    Defaults to 2025 for month-only or year-omitted dates.
    """
    text_lower = text.lower()
    filters = {}

    # --- FIR Number ---
    num_match = re.search(r'fir\s*(?:no\.?|number)?\s*[#:]?\s*([\w\-/]+)', text_lower)
    if num_match:
        candidate = num_match.group(1).strip()
        if re.search(r'\d', candidate):
            filters['fir_number'] = candidate

    # --- Complainant / Accused / Name ---
    comp_match = re.search(r'complainant\s+([\w\s]+?)(?:\s+and|\s+from|\s+between|$)', text_lower)
    if comp_match:
        filters['complainant'] = comp_match.group(1).strip()
    acc_match = re.search(r'accused\s+([\w\s]+?)(?:\s+and|\s+from|\s+between|$)', text_lower)
    if acc_match:
        filters['accused'] = acc_match.group(1).strip()
    name_match = re.search(r'name\s+([\w\s]+?)(?:\s+and|\s+from|\s+between|$)', text_lower)
    if name_match and 'complainant' not in filters and 'accused' not in filters:
        filters['complainant'] = name_match.group(1).strip()

    # --- Date Extraction ---
    start_date = None
    end_date = None
    default_year = 2025

    # 1. Try all possible range patterns using generic date part extraction
    range_patterns = [
        r'between\s+(.+?)\s+and\s+(.+?)(?:\s|$)',
        r'between\s+(.+?)\s+to\s+(.+?)(?:\s|$)',
        r'from\s+(.+?)\s+to\s+(.+?)(?:\s|$)',
        r'from\s+(.+?)\s+until\s+(.+?)(?:\s|$)',
        r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\s+(?:to|and)\s+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'(\d{1,2}\s+[a-z]+\s+\d{4})\s+(?:to|and)\s+(\d{1,2}\s+[a-z]+\s+\d{4})',
        r'(\d{1,2}\s+[a-z]+)\s+(?:to|and)\s+(\d{1,2}\s+[a-z]+\s+\d{4})',
        r'(\d{1,2}\s+[a-z]+\s+\d{4})\s+(?:to|and)\s+(\d{1,2}\s+[a-z]+)',
        r'([a-z]+\s+\d{4})\s+(?:to|and)\s+([a-z]+\s+\d{4})',
        r'([a-z]+)\s+(?:to|and)\s+([a-z]+\s+\d{4})',
        r'([a-z]+\s+\d{4})\s+(?:to|and)\s+([a-z]+)',
        r'([a-z]+)\s+(?:to|and)\s+([a-z]+)',
    ]
    for pat in range_patterns:
        match = re.search(pat, text_lower)
        if match:
            date_str1 = match.group(1).strip()
            date_str2 = match.group(2).strip()
            # Try parsing with dateparser; if year missing, default to 2025 (or inherit from other)
            parsed1 = dateparser.parse(date_str1, settings={'PREFER_DATES_FROM': 'past'})
            parsed2 = dateparser.parse(date_str2, settings={'PREFER_DATES_FROM': 'past'})
            if parsed1 and parsed2:
                start_date = parsed1.strftime('%Y-%m-%d')
                end_date = parsed2.strftime('%Y-%m-%d')
                if start_date > end_date:
                    start_date, end_date = end_date, start_date
                break
            # If one failed, try to repair by inheriting year from the other
            elif parsed1 and not parsed2:
                # Try parsing date2 with year from date1
                yr = parsed1.year
                date2_with_year = re.sub(r'\b(\d{4})\b', str(yr), date_str2, 1)
                if not re.search(r'\b\d{4}\b', date2_with_year):
                    # If no year pattern, append the year
                    date2_with_year = f"{date_str2} {yr}"
                parsed2 = dateparser.parse(date2_with_year, settings={'PREFER_DATES_FROM': 'past'})
                if parsed2:
                    start_date = parsed1.strftime('%Y-%m-%d')
                    end_date = parsed2.strftime('%Y-%m-%d')
                    if start_date > end_date:
                        start_date, end_date = end_date, start_date
                    break
            elif not parsed1 and parsed2:
                yr = parsed2.year
                date1_with_year = re.sub(r'\b(\d{4})\b', str(yr), date_str1, 1)
                if not re.search(r'\b\d{4}\b', date1_with_year):
                    date1_with_year = f"{date_str1} {yr}"
                parsed1 = dateparser.parse(date1_with_year, settings={'PREFER_DATES_FROM': 'past'})
                if parsed1:
                    start_date = parsed1.strftime('%Y-%m-%d')
                    end_date = parsed2.strftime('%Y-%m-%d')
                    if start_date > end_date:
                        start_date, end_date = end_date, start_date
                    break

    # 2. If no range, try bare year (e.g., "2025")
    if not start_date or not end_date:
        year_only = re.search(r'\b(\d{4})\b', text_lower)
        if year_only:
            yr = int(year_only.group(1))
            start_date = datetime(yr, 1, 1).strftime('%Y-%m-%d')
            end_date = datetime(yr, 12, 31).strftime('%Y-%m-%d')

    # 3. If still no date, try month name + optional year
    if not start_date or not end_date:
        month_names = ['january','february','march','april','may','june','july',
                       'august','september','october','november','december',
                       'jan','feb','mar','apr','jun','jul','aug','sep','oct','nov','dec']
        found_month = None
        found_year = None

        for mon in month_names:
            if mon in text_lower:
                found_month = mon
                break

        if found_month:
            year_match = re.search(r'\b(\d{4})\b', text_lower)
            if year_match:
                found_year = int(year_match.group(1))
            else:
                found_year = default_year

            month_map = {
                'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
                'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
                'jan':1,'feb':2,'mar':3,'apr':4,'jun':6,'jul':7,'aug':8,
                'sep':9,'oct':10,'nov':11,'dec':12
            }
            month_num = month_map.get(found_month)
            if month_num and found_year:
                first_day = datetime(found_year, month_num, 1).strftime('%Y-%m-%d')
                last_day_num = calendar.monthrange(found_year, month_num)[1]
                last_day = datetime(found_year, month_num, last_day_num).strftime('%Y-%m-%d')
                start_date = first_day
                end_date = last_day

    # 4. Fallback to dateparser.search for any remaining dates (e.g., relative)
    if not start_date or not end_date:
        try:
            parsed_dates = search_dates(text)
            if parsed_dates:
                date_objs = [dt for _, dt in parsed_dates]
                if len(date_objs) >= 2:
                    start_dt = min(date_objs)
                    end_dt = max(date_objs)
                    start_date = start_dt.strftime('%Y-%m-%d')
                    end_date = end_dt.strftime('%Y-%m-%d')
                elif len(date_objs) == 1:
                    dt = date_objs[0]
                    start_date = dt.strftime('%Y-%m-%d')
                    end_date = dt.strftime('%Y-%m-%d')
        except Exception:
            pass

    # 5. Relative dates (last week, today, etc.) – if still nothing
    if not start_date and not end_date:
        if 'last week' in text_lower or 'past week' in text_lower:
            end = datetime.now()
            start = end - timedelta(weeks=1)
            start_date = start.strftime('%Y-%m-%d')
            end_date = end.strftime('%Y-%m-%d')
        elif 'last month' in text_lower or 'past month' in text_lower:
            end = datetime.now()
            start = end - timedelta(days=30)
            start_date = start.strftime('%Y-%m-%d')
            end_date = end.strftime('%Y-%m-%d')
        elif 'today' in text_lower:
            today = datetime.now().strftime('%Y-%m-%d')
            start_date = today
            end_date = today
        elif 'yesterday' in text_lower:
            yest = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            start_date = yest
            end_date = yest

    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date

    # Choose date field
    if 'fir date' in text_lower or 'fir_date' in text_lower:
        filters['date_field'] = 'fir_date'
    else:
        filters['date_field'] = 'incident_date'

    return filters


# ==============================================================
# CORE LOGIC (backend calls) — all debug messages removed
# ==============================================================
def process_command(cmd, lang):
    cmd_lower = cmd.lower()
    if "upload" in cmd_lower:
        add_message("bot", "📎 Please use the <strong>Case Intake</strong> tab to upload a FIR file for OCR and summarization.")
        return
    elif "search" in cmd_lower and "number" in cmd_lower:
        nums = re.findall(r'\d+', cmd)
        if nums:
            fir_num = nums[0]
            add_message("bot", f"🔎 Searching case register for FIR number <strong>{fir_num}</strong>...")
            search_by_number(fir_num)
            return
        else:
            add_message("bot", "Please provide a FIR number, e.g. <em>'search 0114'</em>.")
            return
    elif "search" in cmd_lower and "name" in cmd_lower:
        parts = cmd.split("name")
        if len(parts) > 1:
            name = parts[1].strip()
            add_message("bot", f"🔎 Searching case register for name <strong>{name}</strong>...")
            search_by_name(name)
            return
        else:
            add_message("bot", "Please specify a name, e.g. <em>'search name Pranab'</em>.")
            return
    elif "show all" in cmd_lower or "view all" in cmd_lower:
        view_all_firs()
        return
    else:
        filters = parse_natural_query(cmd)
        if filters and (filters.get('start_date') or filters.get('end_date') or filters.get('complainant') or filters.get('accused') or filters.get('fir_number')):
            filter_firs_frontend(filters)
            return
        else:
            add_message("bot", "I can assist with: <em>'upload FIR'</em>, <em>'search 0114'</em>, <em>'search name Pranab'</em>, <em>'show all FIRs'</em>, or natural queries like <em>'show FIRs between 1 Jan 2025 and 15 Jan 2025'</em> or <em>'show me all FIRs in the month of June 2025'</em>.")


def process_upload(file, lang):
    file_key = f"{file.name}_{file.size}"
    if file_key in st.session_state.processed_files:
        return
    st.session_state.processed_files.add(file_key)

    with st.spinner("Reading document, extracting text and generating summary..."):
        try:
            health = requests.get(f"{BACKEND_URL}/health", timeout=5)
            if health.status_code != 200:
                add_message("bot", "❌ The summarization backend is not reachable. Please contact system support.")
                return
            response = requests.post(
                f"{BACKEND_URL}/summarize",
                files={"file": (file.name, file.getvalue(), file.type)},
                data={"translate_to": lang},
                timeout=180
            )
            if response.status_code == 200:
                result = response.json()
                summary = result.get("summary", "No summary generated.")
                translated = result.get("translated_summary")
                msg = f"<strong>📝 Case Summary Generated</strong>{summary}"
                if translated:
                    lang_name = LANG_NAMES.get(lang, lang.upper())
                    msg += f"<strong>🌐 {lang_name} Translation</strong>{translated}"
                st.session_state.summary_text = summary
                st.session_state.translated_text = translated
                add_message("bot", msg)
            else:
                add_message("bot", f"❌ Backend returned an error (status {response.status_code}).")
        except requests.exceptions.Timeout:
            add_message("bot", "❌ The request timed out. Please try again.")
        except Exception as e:
            add_message("bot", f"❌ Error: {str(e)}")


def search_by_number(fir_num):
    try:
        st.session_state.last_query = fir_num
        st.session_state.last_search_type = "number"
        response = requests.get(f"{BACKEND_URL}/fir/{fir_num}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            st.session_state.last_raw_response = data
            firs = data.get("firs", [])
            if firs:
                df = pd.DataFrame(firs)
                st.session_state.results_number = df
                st.session_state.results_name = None
                st.session_state.results_all = None
                st.session_state.results_filter = None
                st.session_state.search_history.append({
                    "type": "number", "query": fir_num, "timestamp": now_str(), "results_df": df.copy()
                })
                add_message("bot", f"✅ Found {len(firs)} matching record(s).")
            else:
                st.session_state.results_number = None
                add_message("bot", f"ℹ️ No FIR found with number '{fir_num}'.")
        elif response.status_code == 404:
            st.session_state.results_number = None
            add_message("bot", "ℹ️ FIR not found in the register.")
        else:
            st.session_state.results_number = None
            add_message("bot", f"❌ Error: {response.status_code}")
    except Exception as e:
        st.session_state.results_number = None
        add_message("bot", f"❌ Error: {str(e)}")


def search_by_name(name):
    try:
        response = requests.post(f"{BACKEND_URL}/search", params={"name": name}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            st.session_state.last_raw_response = data
            st.session_state.last_query = name
            st.session_state.last_search_type = "name"
            results = extract_results(data)
            if results:
                df = pd.DataFrame(results)
                st.session_state.results_name = df
                st.session_state.results_number = None
                st.session_state.results_all = None
                st.session_state.results_filter = None
                st.session_state.search_history.append({
                    "type": "name", "query": name, "timestamp": now_str(), "results_df": df.copy()
                })
                add_message("bot", f"✅ Found {len(results)} matching record(s) for '{name}'.")
            else:
                st.session_state.results_name = None
                add_message("bot", f"ℹ️ No matching FIRs found for '{name}'.")
        else:
            st.session_state.results_name = None
            add_message("bot", f"❌ Error: {response.status_code}")
    except Exception as e:
        st.session_state.results_name = None
        add_message("bot", f"❌ Error: {str(e)}")


def view_all_firs():
    try:
        response = requests.post(f"{BACKEND_URL}/search", params={"name": ""}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            st.session_state.last_raw_response = data
            st.session_state.last_query = "All FIRs"
            st.session_state.last_search_type = "all"
            results = extract_results(data)
            if results:
                df = pd.DataFrame(results)
                st.session_state.results_all = df
                st.session_state.results_number = None
                st.session_state.results_name = None
                st.session_state.results_filter = None
                st.session_state.search_history.append({
                    "type": "all", "query": "All FIRs", "timestamp": now_str(), "results_df": df.copy()
                })
                add_message("bot", f"📋 Loaded {len(results)} records from the case register.")
            else:
                st.session_state.results_all = None
                add_message("bot", "ℹ️ No FIRs found in the database.")
        else:
            st.session_state.results_all = None
            add_message("bot", f"❌ Error: {response.status_code}")
    except Exception as e:
        st.session_state.results_all = None
        add_message("bot", f"❌ Error: {str(e)}")


# --------------------------------------------------------------
# filter_firs_frontend — all debug removed, silent header cleaning
# --------------------------------------------------------------
def filter_firs_frontend(filters):
    try:
        response = requests.post(f"{BACKEND_URL}/filter", json=filters, timeout=10)
        if response.status_code == 200:
            data = response.json()
            st.session_state.last_raw_response = data
            results = data.get("results", [])
            if results:
                results = [r for r in results if str(r.get('id', '')).lstrip('-').isdigit()]
            if results:
                df = pd.DataFrame(results)
                st.session_state.results_filter = df
                st.session_state.results_number = None
                st.session_state.results_name = None
                st.session_state.results_all = None
                st.session_state.search_history.append({
                    "type": "filter",
                    "query": "Custom filter",
                    "timestamp": now_str(),
                    "results_df": df.copy()
                })
                add_message("bot", f"✅ Found {len(results)} matching record(s).")
            else:
                st.session_state.results_filter = None
                add_message("bot", "ℹ️ No records matched your filters.")
        else:
            st.session_state.results_filter = None
            add_message("bot", f"❌ Error: {response.status_code}")
    except Exception as e:
        st.session_state.results_filter = None
        add_message("bot", f"❌ Error: {str(e)}")


# ==============================================================
# BACKEND STATUS
# ==============================================================
backend_online = check_backend()

# ==============================================================
# SIDEBAR — Control Desk
# ==============================================================
with st.sidebar:
    st.markdown("""
    <div class="sb-crest">
        <div class="badge">🛡️</div>
        <div class="txt">
            <div class="t1">FIR SAHAYAK</div>
            <div class="t2">Control Desk</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    pill_class = "ok" if backend_online else "err"
    pill_text = "Backend Online" if backend_online else "Backend Offline"
    st.markdown(f'<div class="status-pill {pill_class}">{pill_text}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-eyebrow">Translation Language</div>', unsafe_allow_html=True)
    target_lang = st.selectbox(
        "Translation Language", options=list(LANG_NAMES.keys()),
        format_func=lambda x: LANG_NAMES[x], key="lang_select", label_visibility="collapsed"
    )

    st.markdown('<div class="sb-eyebrow">Navigation</div>', unsafe_allow_html=True)
    page_names = ["💬 Duty Desk Chat", "📄 Case Intake", "🔍 Lookup by Number", "👤 Lookup by Name", "📋 Case Register"]

    def update_page():
        st.session_state.current_page = st.session_state.nav_radio

    current_idx = page_names.index(st.session_state.current_page) if st.session_state.current_page in page_names else 0
    st.radio("Navigate", page_names, index=current_idx, key="nav_radio", on_change=update_page, label_visibility="collapsed")

    st.markdown('<div class="sb-eyebrow">Case Log (this session)</div>', unsafe_allow_html=True)
    if st.session_state.search_history:
        for idx, item in enumerate(reversed(st.session_state.search_history[-15:])):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(
                    f'<div class="history-item type-{item["type"]}">'
                    f'<span class="query">{item["query"]}</span><br>'
                    f'<span class="time">{TYPE_TAG.get(item["type"], "")} · {item["timestamp"]}</span></div>',
                    unsafe_allow_html=True
                )
            with col2:
                if st.button("Open", key=f"hist_{idx}"):
                    if item["type"] == "number":
                        st.session_state.results_number = item["results_df"]
                        st.session_state.results_name = None
                        st.session_state.results_all = None
                        st.session_state.results_filter = None
                        st.session_state.current_page = "🔍 Lookup by Number"
                    elif item["type"] == "name":
                        st.session_state.results_name = item["results_df"]
                        st.session_state.results_number = None
                        st.session_state.results_all = None
                        st.session_state.results_filter = None
                        st.session_state.current_page = "👤 Lookup by Name"
                    elif item["type"] == "all":
                        st.session_state.results_all = item["results_df"]
                        st.session_state.results_number = None
                        st.session_state.results_name = None
                        st.session_state.results_filter = None
                        st.session_state.current_page = "📋 Case Register"
                    elif item["type"] == "filter":
                        st.session_state.results_filter = item["results_df"]
                        st.session_state.results_number = None
                        st.session_state.results_name = None
                        st.session_state.results_all = None
                        st.session_state.current_page = "💬 Duty Desk Chat"
                    st.rerun()
        st.markdown('<div class="clear-history-btn">', unsafe_allow_html=True)
        if st.button("🗑️ Clear Case Log", use_container_width=True):
            st.session_state.search_history = []
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.caption("No searches logged yet this session.")

    st.markdown('<div class="sb-eyebrow">System</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Recheck", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("🧹 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.processed_files = set()
            st.rerun()

    st.caption(f"Endpoint: `{BACKEND_URL}`")
    st.caption("🔒 Restricted — authorized personnel only.")

# ==============================================================
# LETTERHEAD
# ==============================================================
now = datetime.now()
st.markdown(f"""
<div class="letterhead">
    <div class="letterhead-left">
        <div class="crest">⚖️</div>
        <div>
            <div class="dept-title">FIR SAHAYAK — e-Police Summarization Desk</div>
            <div class="dept-subtitle">AI-assisted multilingual FIR intake, OCR, summarization &amp; case lookup</div>
        </div>
    </div>
    <div class="letterhead-right">
        <div class="status-pill {'ok' if backend_online else 'err'}">{'Backend Online' if backend_online else 'Backend Offline'}</div>
        <div class="datetime">{now.strftime('%A, %d %b %Y')} · {now.strftime('%H:%M')} IST</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================
# PAGE ROUTER
# ==============================================================
page = st.session_state.current_page

# ---------------------------------------------------------------
if page == "💬 Duty Desk Chat":
    st.markdown('<div class="page-eyebrow">Duty Desk</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Conversational Assistant</div>', unsafe_allow_html=True)

    chat_html = '<div class="chat-container">'
    for msg in st.session_state.messages:
        t = msg.get("time", "")
        if msg["role"] == "user":
            chat_html += (
                f'<div class="msg-row user"><div class="avatar user">🧑‍💼</div>'
                f'<div class="bubble user">{msg["content"]}<div style="opacity:0.7;font-size:10.5px;margin-top:6px;">{t}</div></div></div>'
            )
        else:
            chat_html += (
                f'<div class="msg-row bot"><div class="avatar bot">👮</div>'
                f'<div class="bubble bot">{msg["content"]}<div style="opacity:0.6;font-size:10.5px;margin-top:6px;">{t}</div></div></div>'
            )
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    if not st.session_state.messages:
        st.info("No messages yet. Try: **'search 0114'**, **'search name Pranab'**, **'show all FIRs'**, or natural queries like **'show FIRs between 1 Jan 2025 and 15 Jan 2025'** or **'show me all FIRs in the month of June 2025'**.")

    # Display filter results if any
    if st.session_state.results_filter is not None:
        st.markdown("### 🔍 Filter Results")
        with st.expander("📄 Raw response (debug)"):
            st.json(st.session_state.last_raw_response)
        st.dataframe(st.session_state.results_filter, use_container_width=True)
        if st.button("Clear Filter Results"):
            st.session_state.results_filter = None
            st.rerun()

    st.markdown("---")
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            "Type your message or command", key="chat_input",
            placeholder="e.g. 'search 0114' · 'search name Pranab' · 'show FIRs between 1 Jan 2025 and 15 Jan 2025'",
            label_visibility="collapsed"
        )
    with col2:
        send_clicked = st.button("Send ➤", use_container_width=True)

    if send_clicked and user_input:
        add_message("user", user_input)
        process_command(user_input, target_lang)
        st.rerun()

# ---------------------------------------------------------------
elif page == "📄 Case Intake":
    st.markdown('<div class="page-eyebrow">Case Intake</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Upload &amp; Summarize FIR</div>', unsafe_allow_html=True)

    has_summary = st.session_state.summary_text is not None
    st.markdown(f"""
    <div class="rail">
        <div class="step {'done' if True else ''}"><span class="n">01</span>Upload Document</div>
        <div class="step {'done' if has_summary else ''}"><span class="n">02</span>OCR Extraction</div>
        <div class="step {'done' if has_summary else ''}"><span class="n">03</span>AI Summarization</div>
        <div class="step {'done' if st.session_state.translated_text else ''}"><span class="n">04</span>Translation</div>
    </div>
    """, unsafe_allow_html=True)

    st.caption("Accepted formats: PDF, PNG, JPG · Summary language: English · Optional translation set from the sidebar.")
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "png", "jpg", "jpeg"], key="upload_page")

    if uploaded_file is not None:
        file_key = f"{uploaded_file.name}_{uploaded_file.size}"
        if file_key in st.session_state.processed_files:
            st.info("This file has already been processed in this session.")
            if st.button("🔄 Re-process this file"):
                st.session_state.processed_files.remove(file_key)
                st.rerun()
        else:
            add_message("user", f"📄 Uploaded: {uploaded_file.name}")
            process_upload(uploaded_file, target_lang)
            st.rerun()

    if st.session_state.summary_text:
        st.markdown(f'<div class="summary-box"><strong>📝 Case Summary</strong>{st.session_state.summary_text}</div>', unsafe_allow_html=True)
        if st.session_state.translated_text:
            lang_name = LANG_NAMES.get(target_lang, target_lang.upper())
            st.markdown(
                f'<div class="summary-box"><strong>🌐 {lang_name} Translation</strong>{st.session_state.translated_text}</div>',
                unsafe_allow_html=True
            )

# ---------------------------------------------------------------
elif page == "🔍 Lookup by Number":
    st.markdown('<div class="page-eyebrow">Lookup</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Search by FIR Number</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([4, 1])
    with col1:
        fir_num_input = st.text_input("Enter FIR number", placeholder="e.g. 0114", key="fir_num_page", label_visibility="collapsed")
    with col2:
        search_clicked = st.button("Search", key="search_fir_page", use_container_width=True)

    if search_clicked:
        if fir_num_input.strip():
            add_message("user", f"🔍 Search FIR: {fir_num_input}")
            search_by_number(fir_num_input.strip())
            st.rerun()
        else:
            st.warning("Please enter a FIR number.")

    if st.session_state.results_number is not None:
        df = st.session_state.results_number
        st.markdown(f"**{len(df)} record(s) found**")
        for _, row in df.iterrows():
            st.markdown(f"""
            <div class="case-card">
                <span class="fir-badge">FIR #{safe(row, 'fir_number')}</span>
                <span class="stamp">✔ ON RECORD</span>
                <div class="field"><b>Police Station:</b> {safe(row, 'police_station')}</div>
                <div class="field"><b>Complainant:</b> {safe(row, 'complainant')}</div>
                <div class="field"><b>Accused:</b> {safe(row, 'accused')}</div>
                <div class="field"><b>Summary:</b> {safe(row, 'summary')}</div>
            </div>
            """, unsafe_allow_html=True)
    elif st.session_state.last_search_type == "number":
        st.info(f"ℹ️ No FIR found with number '{st.session_state.last_query}'.")
    else:
        st.info("No results to display. Perform a search above.")

    if st.session_state.last_raw_response is not None:
        with st.expander("🔎 Debug: raw backend response"):
            st.json(st.session_state.last_raw_response)

# ---------------------------------------------------------------
elif page == "👤 Lookup by Name":
    st.markdown('<div class="page-eyebrow">Lookup</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Search by Name</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([4, 1])
    with col1:
        name_input = st.text_input("Enter complainant or accused name", placeholder="e.g. Pranab", key="name_page", label_visibility="collapsed")
    with col2:
        search_clicked = st.button("Search", key="search_name_page", use_container_width=True)

    if search_clicked:
        if name_input.strip():
            add_message("user", f"👤 Search name: {name_input}")
            search_by_name(name_input.strip())
            st.rerun()
        else:
            st.warning("Please enter a name.")

    if st.session_state.results_name is not None:
        df = st.session_state.results_name
        st.markdown(f"**{len(df)} record(s) found**")
        for _, row in df.iterrows():
            st.markdown(f"""
            <div class="case-card">
                <span class="fir-badge">FIR #{safe(row, 'fir_number')}</span>
                <span class="stamp">✔ ON RECORD</span>
                <div class="field"><b>Complainant:</b> {safe(row, 'complainant')}</div>
                <div class="field"><b>Accused:</b> {safe(row, 'accused')}</div>
                <div class="field"><b>Summary:</b> {safe(row, 'summary')}</div>
            </div>
            """, unsafe_allow_html=True)
    elif st.session_state.last_search_type == "name":
        st.info(f"ℹ️ No matching FIRs found for '{st.session_state.last_query}'.")
    else:
        st.info("No results to display. Perform a search above.")

    if st.session_state.last_raw_response is not None:
        with st.expander("🔎 Debug: raw backend response"):
            st.json(st.session_state.last_raw_response)

# ---------------------------------------------------------------
elif page == "📋 Case Register":
    st.markdown('<div class="page-eyebrow">Register</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">All FIRs on Record</div>', unsafe_allow_html=True)

    if st.button("📥 Load All FIRs", key="view_all_page"):
        add_message("user", "📋 Show all FIRs")
        view_all_firs()
        st.rerun()

    if st.session_state.results_all is not None:
        df = st.session_state.results_all
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Records", len(df))
        c2.metric("Unique Stations", df["police_station"].nunique() if "police_station" in df else "—")
        c3.metric("This Session's Searches", len(st.session_state.search_history))
        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
    elif st.session_state.last_search_type == "all":
        st.info("ℹ️ No FIRs found in database.")
    else:
        st.info("No FIRs loaded. Click 'Load All FIRs' above.")

# ==============================================================
# FOOTER
# ==============================================================
st.markdown(
    '<div class="disclaimer">FIR Sahayak is an AI-assisted drafting aid. '
    'All generated summaries and translations must be verified by an authorized officer before being entered into official records. '
    'Confidential — for internal police use only.</div>',
    unsafe_allow_html=True
)