import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from constants import *


class GSheet:
    gsheets_connection = None

    def __init__(self, sheet_id: int | str, sheet_range: str):
        self.sheet_id = str(sheet_id)
        self.sheet_range = sheet_range

    def __enter__(self):
        if not self.gsheets_connection:
            try:
                self.init_sheets_connection()
            except Exception as err:
                raise RuntimeError(f"Failed to connect to Google Sheets: {err}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def get_sheet_values(self):
        result = (
            self.gsheets_connection.spreadsheets().values()
            .get(spreadsheetId=self.sheet_id, range=self.sheet_range)
            .execute()
        )
        return result.get("values", [])

    @classmethod
    def init_sheets_connection(cls):
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SHEET_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SHEET_SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        cls.gsheets_connection = build("sheets", "v4", credentials=creds)

# Class GSheet
