"""Localiza o Tesseract (OCR) sem exigir config.json: usa o caminho do
config.json se existir, senão o PATH e os locais padrão de instalação no
Windows. Assim os parsers funcionam tanto no main.py quanto no app."""

import json
import os
import shutil
import sys

_LOCAIS_PADRAO = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
]


class TesseractAusente(RuntimeError):
    pass


def _caminho_do_config():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    caminho = os.path.join(base, "config.json")
    if not os.path.exists(caminho):
        return None
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f).get("tesseract_cmd") or None
    except (OSError, ValueError):
        return None


def localizar_tesseract():
    candidatos = [_caminho_do_config(), shutil.which("tesseract"), *_LOCAIS_PADRAO]
    for caminho in candidatos:
        if caminho and os.path.exists(caminho):
            return caminho
    return None


def texto_da_imagem(imagem) -> str:
    import pytesseract

    caminho = localizar_tesseract()
    if not caminho:
        raise TesseractAusente(
            "Esse arquivo é uma imagem/scan e precisa do Tesseract OCR, que "
            "não está instalado. Baixe em "
            "https://github.com/UB-Mannheim/tesseract/wiki (marque o idioma "
            "Portuguese na instalação)."
        )
    pytesseract.pytesseract.tesseract_cmd = caminho
    try:
        return pytesseract.image_to_string(imagem, lang="por")
    except pytesseract.TesseractError:
        # Sem o pacote de português instalado: tenta o idioma padrão.
        return pytesseract.image_to_string(imagem)
