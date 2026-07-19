"""
Google Sheets API를 통한 명함 정보 저장
"""
import os
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_service():
    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    creds = service_account.Credentials.from_service_account_file(
        creds_file, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def save_to_sheet(card_info: dict, email_sent: bool = False):
    """명함 정보를 Google Sheets에 새 행으로 추가합니다."""
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID가 설정되지 않았습니다.")

    service = _get_service()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    row = [
        card_info.get("name", ""),
        card_info.get("company", ""),
        card_info.get("title", ""),
        card_info.get("email", ""),
        card_info.get("phone", ""),
        now,
        "성공" if email_sent else "실패",
    ]

    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range="Sheet1!A:G",
        valueInputOption="USER_ENTERED",
        body={"values": [row]},
    ).execute()


def setup_header():
    """스프레드시트 첫 행에 헤더를 추가합니다 (최초 1회 실행)."""
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    service = _get_service()

    headers = [["이름", "회사", "직책", "이메일", "전화번호", "등록일시", "발송여부"]]
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Sheet1!A1:G1",
        valueInputOption="USER_ENTERED",
        body={"values": headers},
    ).execute()
    print("헤더가 설정되었습니다.")


if __name__ == "__main__":
    setup_header()
