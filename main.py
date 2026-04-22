from fastapi import FastAPI, Request, Response
import requests
from requests.auth import HTTPBasicAuth
import PyPDF2
import re
import spacy
from sentence_transformers import SentenceTransformer, util

from sheets import save_to_sheets

app = FastAPI()

print("🚀 AI RESUME PARSER RUNNING")

# -----------------------------
# TWILIO CREDENTIALS
# -----------------------------
from dotenv import load_dotenv
import os

load_dotenv()

account_sid = os.getenv("TWILIO_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")

# -----------------------------
# AI MODELS (FREE)
# -----------------------------
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer("all-MiniLM-L6-v2")

SKILLS_DB = [
    "python", "java", "c", "c++", "sql",
    "machine learning", "ai", "data science",
    "deep learning", "nlp",
    "html", "css", "javascript",
    "react", "nodejs", "django", "flask",
    "mongodb", "mysql", "git", "docker"
]

skill_embeddings = model.encode(SKILLS_DB, convert_to_tensor=True)


# -----------------------------
# PDF TEXT EXTRACTION
# -----------------------------
def extract_text(pdf_path):
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text()
    return text


# -----------------------------
# FIXED NAME EXTRACTION (IMPORTANT)
# -----------------------------
def extract_name_ai(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    candidates = []

    ignore_words = [
        "resume", "objective", "summary", "profile",
        "education", "skills", "experience", "projects",
        "college", "university", "institute", "email",
        "phone", "contact"
    ]

    # 1. spaCy PERSON detection (main AI)
    for line in lines[:10]:
        doc = nlp(line)
        persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]

        for p in persons:
            if len(p.split()) >= 2 and len(p.split()) <= 4:
                candidates.append(p)

    # 2. fallback: top header lines
    for line in lines[:5]:
        clean = line.lower()

        if any(w in clean for w in ignore_words):
            continue

        if re.search(r"[0-9@:/|]", line):
            continue

        if 2 <= len(line.split()) <= 4:
            candidates.append(line)

    return candidates[0] if candidates else "Unknown"


# -----------------------------
# FIXED SKILL EXTRACTION
# -----------------------------
def extract_skills_ai(text):
    text = text.lower().replace("\n", " ")

    # keyword match (important)
    keyword_hits = [s for s in SKILLS_DB if s in text]

    # AI semantic match
    text_embedding = model.encode(text, convert_to_tensor=True)
    scores = util.cos_sim(text_embedding, skill_embeddings)[0]

    ai_hits = [
        SKILLS_DB[i]
        for i, score in enumerate(scores)
        if score > 0.30
    ]

    return list(set(keyword_hits + ai_hits))


# -----------------------------
# CONTACT EXTRACTION
# -----------------------------
def extract_contact(text):
    email = re.findall(r'\S+@\S+', text)
    phone = re.findall(r'\d{10}', text)

    return {
        "email": email[0] if email else "",
        "phone": phone[0] if phone else ""
    }


# -----------------------------
# FULL PARSER
# -----------------------------
def parse_resume(text):
    name = extract_name_ai(text)
    skills = extract_skills_ai(text)
    contact = extract_contact(text)

    return {
        "name": name,
        "email": contact["email"],
        "phone": contact["phone"],
        "skills": skills
    }


# -----------------------------
# HOME
# -----------------------------
@app.get("/")
async def home():
    return {"message": "AI Resume Parser Running"}


# -----------------------------
# WEBHOOK (TWILIO)
# -----------------------------
@app.post("/webhook")
async def webhook(request: Request):
    print("🔥 WEBHOOK HIT")

    form = await request.form()
    num_media = int(form.get("NumMedia", 0))

    if num_media > 0:

        media_url = form.get("MediaUrl0")

        try:
            # DOWNLOAD FILE
            response = requests.get(
                media_url,
                auth=HTTPBasicAuth(account_sid, auth_token),
                allow_redirects=True
            )

            file_path = "resume.pdf"

            with open(file_path, "wb") as f:
                f.write(response.content)

            print("📄 PDF downloaded")

            # EXTRACT TEXT
            text = extract_text(file_path)

            # PARSE AI DATA
            data = parse_resume(text)

            print("🧠 Parsed:", data)

            # SAVE TO SHEETS
            save_to_sheets(data)

            msg = f"✅ Resume saved: {data['name']}"

        except Exception as e:
            print("❌ ERROR:", e)
            msg = "⚠️ Processing failed"

        return Response(
            content=f"""
            <Response>
                <Message>{msg}</Message>
            </Response>
            """,
            media_type="application/xml"
        )

    return Response(
        content="""
        <Response>
            <Message>📄 Send PDF resume</Message>
        </Response>
        """,
        media_type="application/xml"
    )