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

    def update_priority_from_activity(self, names: set, activity: float):
        updated_values = []
        for idx, row in enumerate(self.get_sheet_values()):
            if row[0].lower() in names:
                new_value = str(float(row[1]) + activity)
                updated_values.append({
                    'range': f"{self.sheet_range.split('!')[0]}!B{idx + 1}",
                    'values': [[new_value]]
                })
        try:
            self.update_values(updated_values)
        except Exception as err:
            raise RuntimeError(f"Failed to update spreadsheet: {err}")

    async def activity_update(self, act_type: str, names_values: list[tuple[str, float]], members_sheet, activities_sheet):
        if names_values:
            orig_sheet_id, orig_sheet_range = self.sheet_id, self.sheet_range
            self.sheet_id, self.sheet_range = members_sheet['id'], members_sheet['range_name']
            members = [row[0] for row in self.get_sheet_values()]
            self.sheet_id, self.sheet_range = activities_sheet['id'], activities_sheet['range_name']
            activities = [row[0] for row in self.get_sheet_values()]
            self.sheet_id, self.sheet_range = orig_sheet_id, orig_sheet_range

            prepared_values = [[name, act_type, value] for name, value in names_values]
            result = self.append_values(prepared_values)
            updates_range = result['updates']['updatedRange']
            await self.add_dropdown(updates_range, members)
            await self.add_dropdown(updates_range, activities, 1)
