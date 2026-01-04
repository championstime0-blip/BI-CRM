import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def connect_sheet(credentials_dict, sheet_name, aba):
    creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).worksheet(aba)
    data = sheet.get_all_records()
    return pd.DataFrame(data), sheet


def append_row(sheet, data_dict):
    sheet.append_row(list(data_dict.values()), value_input_option="USER_ENTERED")
