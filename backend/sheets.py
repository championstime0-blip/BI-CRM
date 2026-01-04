import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

def connect_sheet(credentials_dict, spreadsheet_id, aba):

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        credentials_dict,
        scopes=scopes
    )

    # DEBUG CRÍTICO
    print("Service Account:", creds.service_account_email)

    client = gspread.authorize(creds)

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except Exception as e:
        raise RuntimeError(
            f"""
❌ Planilha NÃO acessível pela Service Account.

Service Account:
{creds.service_account_email}

Verifique:
✔ ID correto
✔ Planilha compartilhada com esse e-mail
✔ Permissão Editor
✔ Drive Compartilhado (se aplicável)

Erro original:
{e}
"""
        )

    try:
        worksheet = spreadsheet.worksheet(aba)
    except Exception:
        raise RuntimeError(f"Aba '{aba}' não encontrada.")

    df = pd.DataFrame(worksheet.get_all_records())
    return df, worksheet
