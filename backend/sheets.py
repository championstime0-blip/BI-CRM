import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# ===============================
# GOOGLE SHEETS CONNECTOR
# ===============================
def connect_sheet(credentials_dict, spreadsheet_id, aba):
    """
    Conecta a uma aba específica do Google Sheets
    usando ID da planilha (recomendado para produção).
    """

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        credentials_dict,
        scopes=scopes
    )

    client = gspread.authorize(creds)

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except Exception as e:
        raise RuntimeError(
            f"Planilha não encontrada. Verifique:\n"
            f"- ID correto\n"
            f"- Permissão da Service Account\n\n"
            f"Erro original: {e}"
        )

    try:
        worksheet = spreadsheet.worksheet(aba)
    except Exception:
        raise RuntimeError(
            f"Aba '{aba}' não encontrada na planilha."
        )

    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    return df, worksheet
