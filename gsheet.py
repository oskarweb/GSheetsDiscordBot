import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2 import service_account

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

    def update_values(self, new_values: list):
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': new_values
        }
        try:
            result = (
                self.gsheets_connection.spreadsheets().values()
                .batchUpdate(spreadsheetId=self.sheet_id, body=body)
                .execute()
            )
        except Exception as err:
            raise RuntimeError(f"Failed to update spreadsheet: {err}")
        else:
            return result

    @classmethod
    def init_sheets_connection(cls):
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
        cls.gsheets_connection = build("sheets", "v4", credentials=creds)

# Class GSheet
