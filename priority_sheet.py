from gsheet import GSheet
from constants import *


class PrioritySheet(GSheet):
    def __init__(self, sheet_id: int | str, sheet_range: str):
        super().__init__(sheet_id, sheet_range)
        self.sheet_name = sheet_range.split('!')[0]

    def get_priority_from_nickname(self, nickname: str) -> tuple[str, str] | None:
        for row in self.get_sheet_values():
            if row[0].lower() == nickname.lower():
                return row[0], row[3]
        return None

    def update_priority_from_activity(self, names: str, activity: str):
        names_set = set([name.lower() for name in names.split(",")])
        updated_values = []
        for idx, row in enumerate(self.get_sheet_values()):
            if row[0].lower() in names_set:
                new_value = str(float(row[1]) + ACTIVITIES[activity])
                updated_values.append({
                    'range': f"{self.sheet_range.split('!')[0]}!B{idx + 1}",
                    'values': [[new_value]]
                })
        if len(names_set) != len(updated_values):
            raise ValueError("Invalid name.")
        try:
            self.update_values(updated_values)
        except Exception as err:
            raise RuntimeError(f"Failed to update spreadsheet: {err}")

    def wb_update(self, names_values: list[tuple[str, float]], point_coefficient: float, value_id: dict):
        updated_values = []
        for name, foods in names_values:
            for idx, row in enumerate(self.get_sheet_values()):
                if row[0].lower() == name.lower():
                    new_value = str(float(row[value_id['row']]) + (foods * point_coefficient))
                    updated_values.append({
                        'range': f"{self.sheet_name}!{value_id['column']}{idx + 1}",
                        'values': [[new_value]]
                    })
        if not updated_values:
            return None
        try:
            self.update_values(updated_values)
        except Exception as err:
            raise RuntimeError(f"Failed to update spreadsheet: {err}")

