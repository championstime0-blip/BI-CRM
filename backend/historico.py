from datetime import datetime

def salvar_snapshot(sheet, marca, kpis):
    snapshot = {
        "data": datetime.now().strftime("%Y-%m-%d"),
        "marca": marca,
        "total": kpis["total"],
        "perdidos": kpis["perdidos"],
        "andamento": kpis["andamento"],
        "aguardando": kpis["aguardando"]
    }
    sheet.append_row(list(snapshot.values()), value_input_option="USER_ENTERED")
