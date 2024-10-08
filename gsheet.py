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

    def append_values(self, added_values: list[list]):
        body = {
            'values': added_values
        }
        try:
            result = (
                self.gsheets_connection.spreadsheets().values()
                .append(spreadsheetId=self.sheet_id, range=self.sheet_range, valueInputOption='USER_ENTERED', body=body)
                .execute()
            )
        except Exception as err:
            print(err)
            raise RuntimeError(f"Failed to append values to spreadsheet: {err}")
        else:
            return result

    async def add_dropdown(self, range_name: str, options: list[str], column_offset: int = 0):
        sheet_name, cell_range = range_name.split('!')
        start_cell = cell_range.split(':')[0]
        end_cell = cell_range.split(':')[1]

        sheet_metadata = self.gsheets_connection.spreadsheets().get(spreadsheetId=self.sheet_id).execute()
        sheet_id = next(sheet['properties']['sheetId'] for sheet in sheet_metadata['sheets'] if
                        sheet['properties']['title'] == sheet_name)

        start_row = int(start_cell[1:]) - 1
        end_row = int(end_cell[1:]) - 1
        start_column = ord(start_cell[0]) - ord('A') + column_offset

        rule = {
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row + 1,
                    "startColumnIndex": start_column,
                    "endColumnIndex": start_column + 1
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": value} for value in options]
                    },
                    "showCustomUi": True,
                    "strict": True
                }
            }
        }

        body = {
            "requests": [rule]
        }

        try:
            self.gsheets_connection.spreadsheets().batchUpdate(spreadsheetId=self.sheet_id, body=body).execute()
        except Exception as err:
            raise RuntimeError(f"Failed to add dropdown: {err}")

    @classmethod
    def init_sheets_connection(cls):
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
        cls.gsheets_connection = build("sheets", "v4", credentials=creds)

# Class GSheet
