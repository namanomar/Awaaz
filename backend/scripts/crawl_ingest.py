#!/usr/bin/env python3
"""
scripts/crawl_ingest.py — Government scheme web crawler + multilingual FAQ generator

Flow:
  1. Fetch HTML from official scheme websites
  2. Find and download PDF links from those pages (up to 3 per scheme)
  3. Extract readable text from HTML + PDFs
  4. Use Gemini to summarize into 6-8 Q&A pairs per scheme
  5. Translate each Q&A set into all 8 supported languages
  6. Save as text files in data/faqs/ and upsert into Qdrant

Usage:
  python scripts/crawl_ingest.py                  # crawl all schemes, all languages
  python scripts/crawl_ingest.py --scheme pmjay   # single scheme
  python scripts/crawl_ingest.py --lang en hi     # specific languages only
  python scripts/crawl_ingest.py --skip-translate # English only, skip translation
  python scripts/crawl_ingest.py --skip-ingest    # save files but don't push to Qdrant
"""
import os
import re
import time
import uuid
import argparse
import textwrap
from pathlib import Path
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR = Path("data/faqs")
DATA_DIR.mkdir(parents=True, exist_ok=True)

COLLECTION = os.getenv("QDRANT_COLLECTION", "knowledge_base")

LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "bn": "Bengali",
    "ml": "Malayalam",
    "kn": "Kannada",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
}

# ── Scheme definitions ────────────────────────────────────────────────────────

@dataclass
class SchemeSource:
    id: str
    name: str
    domain: str
    helpline: str
    urls: list[str]          # HTML pages to crawl
    pdf_hints: list[str]     # keywords to find relevant PDF links on those pages
    context_hint: str        # extra context hint for Gemini summarization
    extra_context: str = ""  # hardcoded facts if website is JS-rendered / blocked


SCHEMES: list[SchemeSource] = [
    SchemeSource(
        id="pmjay",
        name="Ayushman Bharat PMJAY",
        domain="healthcare",
        helpline="14555",
        urls=[
            "https://pmjay.gov.in/about/pmjay",
            "https://pmjay.gov.in/beneficiary",
            "https://pmjay.gov.in/node/439",
        ],
        pdf_hints=["operational", "guidelines", "beneficiary", "hospital"],
        context_hint="Focus on: eligibility (SECC 2011, income below Rs 2.5 lakh), coverage (Rs 5 lakh/year per family), how to check eligibility, how to get health card (golden card), list of empanelled hospitals, what diseases/treatments are covered, documents needed (Aadhaar, ration card), and helpline 14555.",
        extra_context="""
Ayushman Bharat PMJAY provides health coverage of Rs 5 lakh per year to over 10 crore poor and vulnerable families.
Eligibility is based on SECC 2011 database — families must be in the database. No income cut-off for rural families; for urban, 11 occupational criteria apply.
Coverage: 1,949+ treatment packages including surgery, medical, day care. Covers pre and post hospitalisation costs.
How to get card: Visit nearest Common Service Centre or empanelled hospital with Aadhaar and ration card. Card is free.
Empanelled hospitals: Both government and private. Over 25,000 hospitals across India. Check pmjay.gov.in/empanelledHospitals.
Documents needed: Aadhaar card, ration card (for rural), voter ID (alternative).
Helpline: 14555 (toll-free), available 24x7.
No premium/registration fee required from beneficiary.
Pre-existing conditions are covered from day one.
""",
    ),
    SchemeSource(
        id="cghs",
        name="CGHS Central Government Health Scheme",
        domain="healthcare",
        helpline="1800-11-4477",
        urls=[
            "https://cghs.gov.in/showfile.php?lid=5027",
            "https://cghs.gov.in/index1.php?lang=1&level=2&sublinkid=5027&lid=5027",
        ],
        pdf_hints=["circular", "beneficiary", "wellness", "rate list"],
        context_hint="Focus on: who is eligible (central govt employees, pensioners, families), how to get CGHS card, how to use CGHS wellness centres, referral system, contribution rates, empanelled hospitals, how to register.",
        extra_context="""
CGHS (Central Government Health Scheme) covers central government employees, pensioners, and their family members.
Eligibility: Serving employees of central government, retired pensioners drawing pension from central civil estimates, autonomous body employees (where extended), widows of central govt employees.
CGHS Card: Apply through your department/office. Pensioners apply at CGHS office in their city.
Contribution rates: Based on pay band/pension level. Ranges from Rs 250/month to Rs 1,000/month.
CGHS Wellness Centres: Over 330 centres in 79 cities. OPD consultation, medicines, diagnostic tests available.
Referral: For specialist or hospital treatment, get referral from CGHS Medical Officer.
Private empanelled hospitals: Listed on cghs.gov.in. Cashless treatment at empanelled hospitals.
Helpline: 1800-11-4477.
""",
    ),
    SchemeSource(
        id="pmkisan",
        name="PM Kisan Samman Nidhi",
        domain="agriculture",
        helpline="155261",
        urls=[
            "https://pmkisan.gov.in/Home.aspx",
            "https://pmkisan.gov.in/Documents/Pradhan_Mantri_Kisan_Samman_Nidhi_Scheme.pdf",
        ],
        pdf_hints=["guidelines", "circular", "scheme", "farmer"],
        context_hint="Focus on: eligibility (all landholding farmers, exclusions like government employees/income tax payers), benefit amount (Rs 6,000/year in 3 instalments), how to register (CSC or pmkisan.gov.in), documents (Aadhaar, land records, bank account), how to check status, instalments schedule, and helpline.",
        extra_context="""
PM Kisan Samman Nidhi provides Rs 6,000 per year to all farmer families in 3 instalments of Rs 2,000 each, every 4 months.
Eligibility: All landholding farmer families (land in name of self or family member). No minimum land size.
Exclusions: Constitutional post holders, current/former MPs/MLAs/Ministers, government employees, income tax payers, professionals like doctors/engineers/lawyers/CAs with professional practice.
Registration: Self-registration at pmkisan.gov.in/RegistrationForm.aspx OR visit Common Service Centre (CSC).
Documents: Aadhaar card (mandatory), bank account with IFSC code, land ownership records (khasra/khata number).
Status check: pmkisan.gov.in → Beneficiary Status → enter Aadhaar/mobile/account number.
eKYC: Mandatory. Do at pmkisan.gov.in or nearest CSC.
Helpline: 155261 or 011-23381092.
Payment: Direct to bank account via DBT.
""",
    ),
    SchemeSource(
        id="pmfby",
        name="PM Fasal Bima Yojana Crop Insurance",
        domain="agriculture",
        helpline="1800-180-1551",
        urls=[
            "https://pmfby.gov.in",
            "https://pmfby.gov.in/aboutFasal_Bima",
        ],
        pdf_hints=["operational", "guidelines", "premium", "notification"],
        context_hint="Focus on: eligibility (all farmers including sharecroppers), coverage types (standing crop, post-harvest losses, prevented sowing), premium rates (2% for Kharif, 1.5% for Rabi, 5% for commercial), how to enrol, deadline (7 days before sowing season ends), claim process.",
        extra_context="""
PM Fasal Bima Yojana (PMFBY) provides comprehensive crop insurance coverage.
Eligibility: All farmers including sharecroppers and tenant farmers growing notified crops in notified areas.
Premium: Kharif crops — 2% of sum insured. Rabi crops — 1.5%. Annual commercial/horticultural crops — 5% maximum. Balance premium paid by government.
Coverage: Prevented sowing/planting risk, standing crop losses (drought, flood, pest, disease), post-harvest losses (up to 14 days for drying), localised calamities (hailstorm, landslide, inundation).
Enrollment deadline: Must enrol within 7 days before end of sowing season. For loanee farmers, insurance is compulsory.
How to enrol: Contact nearest bank/PACS/CSC. Non-loanee farmers can also enrol directly.
Sum insured: Based on scale of finance for the area.
Claim: Report crop loss within 72 hours to insurer/state government/bank.
Helpline: 1800-180-1551.
""",
    ),
    SchemeSource(
        id="scholarship",
        name="National Scholarship Portal NSP",
        domain="education",
        helpline="0120-6619540",
        urls=[
            "https://scholarships.gov.in",
            "https://scholarships.gov.in/fresh/newstdRegister",
        ],
        pdf_hints=["circular", "guidelines", "scholarship", "pre-matric", "post-matric"],
        context_hint="Focus on: types of scholarships (pre-matric Class 1-10, post-matric Class 11+), eligible categories (SC/ST/OBC/minorities/disabled), income limits (Rs 2.5 lakh for pre-matric, Rs 2 lakh for post-matric), how to apply (scholarships.gov.in), documents needed, application window (August-October), renewal, amounts.",
        extra_context="""
National Scholarship Portal (NSP) at scholarships.gov.in is a one-stop platform for all central and state government scholarships.
Types: Pre-Matric scholarships (Class 1-10), Post-Matric scholarships (Class 11, 12, graduation, post-graduation, PhD), merit-cum-means scholarships.
Eligible categories: SC, ST, OBC, Minority communities (Muslim, Christian, Sikh, Buddhist, Jain, Parsi), physically handicapped students.
Income limit: Pre-matric — family income below Rs 2.5 lakh/year. Post-matric — below Rs 2 lakh/year (varies by scheme).
Amount: Varies. SC post-matric maintenance allowance Rs 3,000-1,200/month depending on course. Study allowance also given.
Application: Register at scholarships.gov.in with Aadhaar. Fill application, upload documents, get institute verification.
Documents: Aadhaar card, income certificate from competent authority, caste certificate, previous marksheet, bank account (student's own), enrolment certificate from institution.
Application window: August to November each year. Check portal for exact dates.
Renewal: Existing scholars renew each year through the same portal.
Helpline: 0120-6619540.
""",
    ),
    SchemeSource(
        id="pmkvy",
        name="PM Kaushal Vikas Yojana Skill Training",
        domain="education",
        helpline="1800-123-9626",
        urls=[
            "https://www.pmkvyofficial.org",
            "https://www.pmkvyofficial.org/pm-kvy-4.0",
        ],
        pdf_hints=["guidelines", "qualification", "training", "sector"],
        context_hint="Focus on: eligibility (Indian nationals, school/college dropouts, unemployed), free training (no fee), certification (NSDC-recognised), how to find training centre, sectors (IT, construction, beauty, healthcare, etc.), placement support, PMKVY 4.0 features.",
        extra_context="""
PM Kaushal Vikas Yojana (PMKVY) provides free skill training and industry-recognised certification to youth.
Eligibility: Indian citizens. School/college dropouts, unemployed, and currently employed seeking upskilling. No upper age limit in most sectors.
Cost: Completely free training. Government pays training cost directly to Training Centre.
Duration: 150-300 hours depending on course.
Sectors: IT, electronics, construction, beauty & wellness, healthcare, automotive, retail, BFSI, agriculture, hospitality — 300+ job roles across 37 sectors.
Certification: National Skills Qualifications Framework (NSQF) aligned. Recognised by industry.
How to find training centre: pmkvyofficial.org → Training Centre Locator → enter your district/state.
Placement: Training Centres provide placement assistance. Some have dedicated placement cells.
PMKVY 4.0: Focus on Industry 4.0 skills (AI, robotics, 3D printing, IoT), on-job training, hybrid learning.
Stipend: Some courses under Recognition of Prior Learning (RPL) provide Rs 500-2,000 assessment fee.
Helpline: 1800-123-9626.
""",
    ),
    SchemeSource(
        id="pmay",
        name="PM Awas Yojana Housing",
        domain="housing",
        helpline="1800-11-3377",
        urls=[
            "https://pmaymis.gov.in",
            "https://pmayg.nic.in",
            "https://mohua.gov.in/cms/pradhan-mantri-awas-yojana.php",
        ],
        pdf_hints=["guidelines", "circular", "operational", "gramin", "urban"],
        context_hint="Focus on: PMAY Urban vs Gramin, eligibility (EWS income up to Rs 3 lakh, LIG Rs 3-6 lakh, MIG I Rs 6-12 lakh, MIG II Rs 12-18 lakh), subsidy amounts (EWS/LIG Rs 2.67 lakh max, PMAY Gramin Rs 1.2-1.3 lakh), mandatory woman co-ownership, how to apply, documents needed.",
        extra_context="""
PMAY has two components: PMAY Urban (cities) and PMAY Gramin (villages).
PMAY Urban:
- EWS (income up to Rs 3 lakh): Interest subsidy 6.5% on loan up to Rs 6 lakh = max subsidy Rs 2.67 lakh.
- LIG (Rs 3-6 lakh income): Same subsidy as EWS.
- MIG-I (Rs 6-12 lakh): 4% subsidy on loan up to Rs 9 lakh = max Rs 2.35 lakh.
- MIG-II (Rs 12-18 lakh): 3% subsidy on loan up to Rs 12 lakh = max Rs 2.30 lakh.
- Apply: pmaymis.gov.in or Common Service Centre.
PMAY Gramin:
- Rs 1.2 lakh in plains, Rs 1.3 lakh in hilly/difficult areas for house construction.
- Selected from SECC 2011 data and Awaas+ survey.
- Apply: Local gram panchayat or block development office.
Mandatory: EWS/LIG houses must be in woman's name or joint ownership with woman.
No existing pucca house: Beneficiary family must not own a pucca house anywhere in India.
Documents: Aadhaar, income certificate, bank account, land documents (for Gramin), BPL certificate.
Helpline: 1800-11-3377 (Urban), 1800-11-6446 (Gramin).
""",
    ),
    SchemeSource(
        id="mgnrega",
        name="MGNREGA Rural Employment",
        domain="employment",
        helpline="1800-111-555",
        urls=[
            "https://nrega.nic.in/netnrega/home.aspx",
            "https://nrega.nic.in/netnrega/mpr_ht.aspx",
        ],
        pdf_hints=["act", "schedule II", "operational", "guidelines"],
        context_hint="Focus on: guarantee of 100 days work per year per household, eligibility (any rural adult willing to do unskilled manual work), how to get job card, how to demand work, payment (15 days into bank account), unemployment allowance if work not given within 15 days, wage rates by state, documents for registration.",
        extra_context="""
MGNREGA guarantees 100 days of wage employment per year to every rural household whose adult members want to do unskilled manual work.
Eligibility: Any adult (18+) member of a rural household. No income limit. No caste restriction.
Job Card: Apply at gram panchayat with Aadhaar and residence proof. Issued within 15 days free of cost. Photo on job card.
How to demand work: Submit written application to gram panchayat. Work must be provided within 15 days.
Unemployment allowance: If work not given within 15 days — 1/4 of wage rate for first 30 days, 1/2 for rest of year.
Payment: Wages paid within 15 days of work completion, directly to bank/post office account.
Wages: Vary by state (central notification). Ranges from approx Rs 200-350/day. 100% equal wages for men and women.
Work types: Construction of roads, water conservation, land development, sanitation, plantation within gram panchayat area.
Documents for registration: Aadhaar card, residence proof, photograph.
Helpline: 1800-111-555 (toll-free).
""",
    ),
    SchemeSource(
        id="nsap",
        name="NSAP National Social Assistance Pension",
        domain="social_welfare",
        helpline="1800-111-555",
        urls=[
            "https://nsap.nic.in",
            "https://nsap.nic.in/nsap/front/index.php",
        ],
        pdf_hints=["guidelines", "scheme", "circular", "pension"],
        context_hint="Focus on: components (old age pension IGNOAPS, widow pension IGNWPS, disability pension IGNDPS), eligibility for each (age, BPL, disability percentage), pension amounts by age group, how to apply, documents, timeline for first pension.",
        extra_context="""
NSAP (National Social Assistance Programme) has three pension components:
1. IGNOAPS (Old Age Pension): BPL persons aged 60-79 get Rs 200/month from centre; aged 80+ get Rs 500/month. States add top-up.
2. IGNWPS (Widow Pension): BPL widows aged 40-79 get Rs 300/month from centre.
3. IGNDPS (Disability Pension): BPL persons aged 18-79 with 80%+ disability get Rs 300/month.
How to apply: Gram panchayat (rural) OR ward office/municipality (urban) OR district social welfare office. Submit form with documents.
Documents: Aadhaar, age proof (birth certificate/school leaving/voter ID showing age), BPL card or income certificate from tehsildar/village officer, bank account, passport photo.
For IGNWPS: Husband's death certificate.
For IGNDPS: Disability certificate from government hospital (80% or more disability).
Timeline: Processing takes 60-90 days typically. Pension paid monthly directly to bank.
Check status: nsap.nic.in → Beneficiary Search.
Grievances: District collector or state nodal officer.
Helpline: Contact district social welfare office or state nodal department.
""",
    ),
    SchemeSource(
        id="ujjwala",
        name="PM Ujjwala Yojana Free LPG",
        domain="social_welfare",
        helpline="1906",
        urls=[
            "https://pmuy.gov.in",
            "https://www.pmuy.gov.in/ujjwala2.html",
        ],
        pdf_hints=["guidelines", "scheme", "form", "beneficiary"],
        context_hint="Focus on: eligibility (BPL women 18+, Ujjwala 2.0 expanded categories), what is free (connection, first refill, stove/regulator deposit), subsequent refill cost and subsidy via PAHAL/DBT, documents needed, how to apply at LPG agency.",
        extra_context="""
PM Ujjwala Yojana provides free LPG connections to women from poor households.
Eligibility (Ujjwala 2.0): BPL women 18+; SC/ST households; PMAY beneficiaries; Antyodaya Anna Yojana cardholders; forest dwellers; most backward classes; tea garden workers; river island communities; migrant workers' families. No existing LPG connection in household.
What is free: Connection deposit, first refill, pressure regulator, pipe, and stove deposit — all waived.
Subsequent refills: At market price, but LPG subsidy credited to Aadhaar-linked bank account via PAHAL scheme.
EMI option: Ujjwala beneficiaries can get first refill and stove on EMI, recovered from future subsidy.
How to apply: Visit nearest LPG distributor (IndianOil/HPCL/BPCL). Submit KYC form (Ujjwala form) with documents. Also available at pmuy.gov.in.
Documents: Aadhaar card (mandatory), bank account details, proof of address (ration card/voter ID), declaration that no LPG connection exists.
Helpline: 1906 or 18002333555.
Grievances: pgportal.gov.in.
""",
    ),
]

# ── Gemini client ─────────────────────────────────────────────────────────────

_gemini_client = None


def gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _gemini_client


def gemini_generate(prompt: str, retry: int = 3) -> str:
    """Try Gemini first; fall back to OpenRouter Nemotron on quota errors."""
    # Try Gemini
    for attempt in range(retry):
        try:
            response = gemini_client().models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"temperature": 0.1, "max_output_tokens": 2048},
            )
            return response.text.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower():
                if "PerDay" in err or "per_day" in err.lower():
                    # Daily quota exhausted — skip to fallback immediately
                    print("  [gemini] daily quota exhausted, using OpenRouter fallback...")
                    break
                wait = 20 * (attempt + 1)
                print(f"  [rate limit] waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  [gemini error] {e}")
                if attempt == retry - 1:
                    break
                time.sleep(5)

    # Fallback: OpenRouter Nemotron
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("  [error] no fallback API key available")
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        response = client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b:free",
            max_tokens=2048,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
            extra_headers={"HTTP-Referer": "https://awaaz.ai", "X-Title": "Awaaz"},
            timeout=60,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [openrouter error] {e}")
        return ""


# ── HTML crawler ──────────────────────────────────────────────────────────────

def fetch_page(url: str, timeout: int = 15) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  [fetch error] {url}: {e}")
        return None


def extract_text_from_html(html: str, max_chars: int = 8000) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Remove nav, footer, scripts, styles
    for tag in soup(["nav", "footer", "script", "style", "header", "aside", "form"]):
        tag.decompose()
    # Get main content
    for main in soup.find_all(["main", "article", "section", "div"], limit=5):
        text = main.get_text(separator=" ", strip=True)
        if len(text) > 500:
            return text[:max_chars]
    return soup.get_text(separator=" ", strip=True)[:max_chars]


def find_pdf_links(html: str, base_url: str, hints: list[str]) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    pdf_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if ".pdf" in href:
            text = a.get_text(strip=True).lower()
            # Match if any hint keyword appears in link text or URL
            if any(h.lower() in href or h.lower() in text for h in hints):
                full_url = urljoin(base_url, a["href"])
                if full_url not in pdf_links:
                    pdf_links.append(full_url)
    return pdf_links[:3]  # max 3 PDFs per scheme


# ── PDF downloader and extractor ──────────────────────────────────────────────

def download_pdf(url: str, dest_dir: Path) -> Path | None:
    filename = urlparse(url).path.split("/")[-1]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    dest = dest_dir / filename
    if dest.exists():
        return dest
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  [pdf] downloaded: {filename}")
        return dest
    except Exception as e:
        print(f"  [pdf error] {url}: {e}")
        return None


def extract_text_from_pdf(pdf_path: Path, max_pages: int = 8, max_chars: int = 8000) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= max_pages:
                    break
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)[:max_chars]
    except Exception as e:
        print(f"  [pdf extract error] {pdf_path}: {e}")
        return ""


# ── Text to FAQ via Gemini ────────────────────────────────────────────────────

FAQ_PROMPT = """You are building a knowledge base for an Indian government services voice assistant called Awaaz.

Given the following information about the scheme "{scheme_name}", generate exactly 7 Q&A pairs in English.

Requirements:
- Questions must be what a common citizen would ask over the phone: "Who is eligible?", "How do I apply?", "What documents do I need?", "How much money is given?", "What is the helpline number?", etc.
- Answers must be factual, simple, and 2-4 sentences. No bullet points. Plain prose.
- Include the helpline number "{helpline}" in at least one answer.
- Do NOT invent details not present in the source text.
- Format strictly as:
Q: [question]
A: [answer]

Q: [question]
A: [answer]

(continue for all 7 pairs)

Source information about {scheme_name}:
{source_text}
"""

TRANSLATE_PROMPT = """Translate the following Q&A pairs about Indian government schemes into {target_language}.

Rules:
- Keep the Q: and A: format exactly, with a blank line between each pair.
- Keep scheme names (like "Ayushman Bharat", "PM Kisan"), amounts (Rs 6,000), website URLs, and helpline numbers unchanged.
- Use simple, everyday vocabulary — not bureaucratic or formal language.
- Ensure the translation sounds natural when spoken aloud.

Q&A pairs to translate:
{qa_text}
"""


def generate_english_faqs(scheme: SchemeSource, crawled_text: str) -> str:
    source_text = f"{scheme.extra_context}\n\nAdditional crawled content:\n{crawled_text}".strip()
    prompt = FAQ_PROMPT.format(
        scheme_name=scheme.name,
        helpline=scheme.helpline,
        source_text=source_text[:6000],
    )
    print(f"  [llm] generating English Q&A for {scheme.id}...")
    result = gemini_generate(prompt)
    # Build clean Q/A blocks separated by blank lines for ingestion
    qa_blocks = []
    current = []
    for line in result.split("\n"):
        stripped = line.strip()
        if stripped.startswith("Q:") and current:
            qa_blocks.append("\n".join(current))
            current = [stripped]
        elif stripped.startswith("Q:") or stripped.startswith("A:"):
            current.append(stripped)
    if current:
        qa_blocks.append("\n".join(current))
    return "\n\n".join(qa_blocks) if qa_blocks else result


def translate_faqs(qa_text: str, lang_code: str, lang_name: str) -> str:
    if lang_code == "en":
        return qa_text
    prompt = TRANSLATE_PROMPT.format(target_language=lang_name, qa_text=qa_text)
    print(f"  [llm] translating to {lang_name}...")
    result = gemini_generate(prompt)
    time.sleep(5)  # rate limiting between translations (free tier: 15 req/min)
    return result


# ── Save FAQ files ────────────────────────────────────────────────────────────

def save_faq_file(scheme_id: str, lang_code: str, content: str) -> Path:
    path = DATA_DIR / f"{lang_code}_{scheme_id}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"  [save] {path}")
    return path


# ── Qdrant ingestion ──────────────────────────────────────────────────────────

_embed_model = None
_qdrant = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        print("[embed] loading sentence-transformer model...")
        _embed_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _embed_model


def get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
    return _qdrant


def ingest_file(path: Path, scheme_id: str, lang_code: str, retries: int = 3):
    for attempt in range(retries):
        try:
            return _ingest_file_once(path, scheme_id, lang_code)
        except Exception as e:
            if attempt < retries - 1:
                wait = 10 * (attempt + 1)
                print(f"  [qdrant retry {attempt+1}] {e.__class__.__name__} — waiting {wait}s")
                time.sleep(wait)
            else:
                print(f"  [qdrant error] failed after {retries} attempts: {e}")


def _ingest_file_once(path: Path, scheme_id: str, lang_code: str):
    text = path.read_text(encoding="utf-8")
    # Try double-newline split first, then split on "Q:" boundaries
    blocks = [b.strip() for b in text.split("\n\n") if b.strip() and len(b.strip()) > 20]
    if len(blocks) <= 1:
        # Translated output may not use double newlines — split on "Q:" boundaries
        raw_blocks = re.split(r'\n(?=Q:)', text.strip())
        blocks = [b.strip() for b in raw_blocks if b.strip() and len(b.strip()) > 20]
    if not blocks:
        print(f"  [ingest] no blocks found in {path}")
        return

    model = get_embed_model()
    embeddings = model.encode(blocks, batch_size=16, show_progress_bar=False)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=emb.tolist(),
            payload={
                "text": block,
                "language": lang_code,
                "scheme": scheme_id,
                "source": path.name,
            },
        )
        for emb, block in zip(embeddings, blocks)
    ]
    get_qdrant().upsert(collection_name=COLLECTION, points=points)
    print(f"  [ingest] {len(points)} chunks from {path.name} → Qdrant")


# ── Translate-only helper (for schemes that already have English FAQs) ────────

def translate_missing(scheme: SchemeSource, languages: list[str], skip_ingest: bool):
    """Read existing en_{scheme}.txt, translate only missing language files."""
    en_path = DATA_DIR / f"en_{scheme.id}.txt"
    if not en_path.exists():
        print(f"\n[warn] {en_path} not found — run without --translate-only first")
        return

    print(f"\n{'='*60}")
    print(f"Translating missing: {scheme.name} [{scheme.id}]")
    print(f"{'='*60}")

    en_faqs = en_path.read_text(encoding="utf-8").strip()

    for lang_code in languages:
        if lang_code == "en":
            continue
        out_path = DATA_DIR / f"{lang_code}_{scheme.id}.txt"
        if out_path.exists():
            print(f"  [skip] {out_path.name} already exists")
            if not skip_ingest:
                ingest_file(out_path, scheme.id, lang_code)
            continue
        lang_name = LANGUAGES[lang_code]
        translated = translate_faqs(en_faqs, lang_code, lang_name)
        if translated.strip():
            save_faq_file(scheme.id, lang_code, translated)
            if not skip_ingest:
                ingest_file(out_path, scheme.id, lang_code)


# ── Main orchestrator ─────────────────────────────────────────────────────────

def process_scheme(
    scheme: SchemeSource,
    languages: list[str],
    skip_translate: bool,
    skip_ingest: bool,
    pdf_dir: Path,
):
    print(f"\n{'='*60}")
    print(f"Scheme: {scheme.name} [{scheme.id}]")
    print(f"{'='*60}")

    # 1. Crawl HTML pages
    crawled_texts = []
    all_pdf_links = []

    for url in scheme.urls:
        print(f"  [crawl] {url}")
        html = fetch_page(url)
        if html:
            crawled_texts.append(extract_text_from_html(html))
            all_pdf_links.extend(find_pdf_links(html, url, scheme.pdf_hints))
        time.sleep(1)

    # 2. Download and extract PDFs
    for pdf_url in all_pdf_links[:3]:
        print(f"  [pdf] downloading: {pdf_url}")
        pdf_path = download_pdf(pdf_url, pdf_dir)
        if pdf_path:
            pdf_text = extract_text_from_pdf(pdf_path)
            if pdf_text:
                crawled_texts.append(pdf_text)
        time.sleep(1)

    combined_text = "\n\n".join(crawled_texts)[:8000]

    # 3. Generate English Q&A
    en_faqs = generate_english_faqs(scheme, combined_text)
    if not en_faqs.strip():
        print(f"  [warn] empty Q&A generated for {scheme.id}, skipping")
        return

    # Save English
    en_path = save_faq_file(scheme.id, "en", en_faqs)
    if not skip_ingest:
        ingest_file(en_path, scheme.id, "en")

    if skip_translate:
        print(f"  [skip] translation skipped")
        return

    # 4. Translate to each other language
    for lang_code in languages:
        if lang_code == "en":
            continue
        lang_name = LANGUAGES[lang_code]
        translated = translate_faqs(en_faqs, lang_code, lang_name)
        if translated.strip():
            lang_path = save_faq_file(scheme.id, lang_code, translated)
            if not skip_ingest:
                ingest_file(lang_path, scheme.id, lang_code)


def main():
    parser = argparse.ArgumentParser(description="Crawl government scheme sites → FAQ → Qdrant")
    parser.add_argument("--scheme", nargs="+", help="Scheme IDs to process (default: all)")
    parser.add_argument("--lang", nargs="+", default=list(LANGUAGES.keys()), help="Language codes (default: all 8)")
    parser.add_argument("--skip-translate", action="store_true", help="Generate English only")
    parser.add_argument("--skip-ingest", action="store_true", help="Save files but don't push to Qdrant")
    parser.add_argument("--translate-only", action="store_true", help="Read existing English FAQ files and translate missing languages only (no web crawl)")
    args = parser.parse_args()

    # Validate langs
    lang_codes = [l for l in args.lang if l in LANGUAGES]
    if not lang_codes:
        print(f"No valid languages. Choose from: {list(LANGUAGES.keys())}")
        return

    # Filter schemes
    schemes = SCHEMES
    if args.scheme:
        schemes = [s for s in SCHEMES if s.id in args.scheme]
        if not schemes:
            print(f"No schemes found. Available: {[s.id for s in SCHEMES]}")
            return

    # PDF temp dir
    pdf_dir = Path("data/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing {len(schemes)} scheme(s) in {len(lang_codes)} language(s)")
    print(f"Schemes: {[s.id for s in schemes]}")
    print(f"Languages: {[LANGUAGES[l] for l in lang_codes]}")
    print(f"Translate: {'no' if args.skip_translate else 'yes'}")
    print(f"Ingest to Qdrant: {'no' if args.skip_ingest else 'yes'}")

    for scheme in schemes:
        if args.translate_only:
            translate_missing(
                scheme=scheme,
                languages=lang_codes,
                skip_ingest=args.skip_ingest,
            )
        else:
            process_scheme(
                scheme=scheme,
                languages=lang_codes,
                skip_translate=args.skip_translate,
                skip_ingest=args.skip_ingest,
                pdf_dir=pdf_dir,
            )
        time.sleep(2)  # pause between schemes

    print(f"\n✓ Done. Files saved to {DATA_DIR}/")
    if not args.skip_ingest:
        print(f"✓ All chunks upserted to Qdrant collection: {COLLECTION}")


if __name__ == "__main__":
    main()
