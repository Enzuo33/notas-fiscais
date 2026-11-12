import json
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_BASE_DIR, "config.json")


def _load():
    if not os.path.exists(_CONFIG_PATH):
        raise FileNotFoundError(
            "config.json não encontrado. Copie config.example.json para "
            "config.json e preencha os valores (veja o README.md)."
        )
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_cfg = _load()

SPREADSHEET_ID = _cfg.get("spreadsheet_id", "")
SHEET_NAME = _cfg.get("sheet_name", "Itens")

_credentials_path = _cfg.get("credentials_path", "credentials.json")
CREDENTIALS_PATH = (
    _credentials_path
    if os.path.isabs(_credentials_path)
    else os.path.join(_BASE_DIR, _credentials_path)
)

TESSERACT_CMD = _cfg.get("tesseract_cmd") or None
POPPLER_PATH = _cfg.get("poppler_path") or None

if not SPREADSHEET_ID or SPREADSHEET_ID == "COLE_AQUI_O_ID_DA_SUA_PLANILHA":
    raise ValueError(
        "Preencha 'spreadsheet_id' em config.json com o ID da sua planilha "
        "do Google Sheets (está na URL da planilha)."
    )
