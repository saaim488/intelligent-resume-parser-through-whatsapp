import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -----------------------------
# GOOGLE SHEETS SETUP
# -----------------------------
import os

scope = os.getenv("GOOGLE_SCOPES", "").split()

creds = Credentials.from_service_account_file(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
)

client = gspread.authorize(creds)

sheet = client.open("ResumeData").sheet1


# -----------------------------
# SAVE FUNCTION
# -----------------------------
def save_to_sheets(data):
    print("📊 Saving to Sheets")

    sheet.append_row([
        data.get("name", ""),
        data.get("phone", ""),
        data.get("email", ""),
        ", ".join(data.get("skills", []))
    ])

    print("✅ Saved successfully")