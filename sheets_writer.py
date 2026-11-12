from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

import config

_ESCOPOS = ["https://www.googleapis.com/auth/spreadsheets"]
_CABECALHO = [
    "Arquivo de Origem",
    "Descrição",
    "Quantidade",
    "Valor Unitário",
    "Valor Total",
    "Linha Original (conferência)",
    "Processado em",
]


def _get_service():
    credenciais = service_account.Credentials.from_service_account_file(
        config.CREDENTIALS_PATH, scopes=_ESCOPOS
    )
    return build("sheets", "v4", credentials=credenciais)


def _garantir_cabecalho(service):
    resultado = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=config.SPREADSHEET_ID, range=f"{config.SHEET_NAME}!A1:G1")
        .execute()
    )
    if not resultado.get("values"):
        service.spreadsheets().values().update(
            spreadsheetId=config.SPREADSHEET_ID,
            range=f"{config.SHEET_NAME}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [_CABECALHO]},
        ).execute()


def enviar_itens(itens: list[dict]):
    if not itens:
        print("Nenhum item para enviar à planilha.")
        return

    service = _get_service()
    _garantir_cabecalho(service)

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    linhas = []
    for item in itens:
        linhas.append(
            [
                item.get("arquivo", ""),
                item.get("descricao", ""),
                item.get("quantidade") if item.get("quantidade") is not None else "",
                item.get("valor_unitario") if item.get("valor_unitario") is not None else "",
                item.get("valor_total") if item.get("valor_total") is not None else "",
                item.get("linha_original", ""),
                agora,
            ]
        )

    service.spreadsheets().values().append(
        spreadsheetId=config.SPREADSHEET_ID,
        range=f"{config.SHEET_NAME}!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": linhas},
    ).execute()

    print(f"{len(linhas)} item(ns) enviados para a planilha com sucesso.")
