import os
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def get_service():
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            "token.json이 없습니다. 먼저 'python google_auth.py'를 실행해 Google 인증을 완료하세요."
        )
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def create_event(event_data: dict) -> dict:
    service = get_service()

    body = {
        "summary": event_data["title"],
        "start": {"dateTime": event_data["start_datetime"], "timeZone": "Asia/Seoul"},
        "end": {"dateTime": event_data["end_datetime"], "timeZone": "Asia/Seoul"},
    }
    if event_data.get("location"):
        body["location"] = event_data["location"]
    if event_data.get("description"):
        body["description"] = event_data["description"]
    if event_data.get("recurrence"):
        body["recurrence"] = [event_data["recurrence"]]

    return service.events().insert(calendarId="primary", body=body).execute()


def list_today_events() -> list:
    service = get_service()
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "+09:00"
    end = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat() + "+09:00"

    result = service.events().list(
        calendarId="primary",
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return result.get("items", [])


def list_week_events() -> list:
    service = get_service()
    now = datetime.now()
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    start = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "+09:00"
    end = end_of_week.replace(hour=23, minute=59, second=59, microsecond=0).isoformat() + "+09:00"

    result = service.events().list(
        calendarId="primary",
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return result.get("items", [])


def delete_event(event_id: str):
    service = get_service()
    service.events().delete(calendarId="primary", eventId=event_id).execute()
