from gsheet import GSheet
from constants import *


class PrioritySheet(GSheet):
    def __init__(self, sheet_id: int | str, sheet_range: str):
        super().__init__(sheet_id, sheet_range)

    def update_priority_from_activity(self, names: str, activity: str):
        names_set = set(names.split(","))
        updated_values = []
        for idx, row in enumerate(self.get_sheet_values()):
            if row[0] in names_set:
                new_value = str(int(row[1]) + ACTIVITIES[activity])
                updated_values.append({
                    'range': f"{self.sheet_range.split('!')[0]}!B{idx + 1}",
                    'values': [[new_value]]
                })
        if not updated_values:
            return None

        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': updated_values
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

    def get_priority_from_nickname(self, nickname: str):
        for row in self.get_sheet_values():
            if row[0] == nickname:
                return row[3]
        return None
