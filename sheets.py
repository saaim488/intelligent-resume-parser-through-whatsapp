import os
import gspread
from google.oauth2.service_account import Credentials

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    scopes=scope
)
client = gspread.authorize(creds)
sheet = client.open("ResumeData").sheet1


def save_to_sheets(data):
    print("📊 Saving to Sheets")

    sheet.append_row([
        data.get("name", ""),
        data.get("phone", ""),
        data.get("email", ""),
        ", ".join(data.get("skills", []))
    ])

    print("✅ Saved successfully")
