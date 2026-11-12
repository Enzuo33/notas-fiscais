import argparse
import os
import sys

EXTENSOES = {
    ".csv": "csv",
    ".pdf": "pdf",
    ".png": "imagem",
    ".jpg": "imagem",
    ".jpeg": "imagem",
    ".bmp": "imagem",
    ".tif": "imagem",
    ".tiff": "imagem",
}


def _processar_arquivo(caminho: str):
    ext = os.path.splitext(caminho)[1].lower()
    tipo = EXTENSOES.get(ext)
    if tipo is None:
        return None

    if tipo == "csv":
        from parsers import csv_parser
        return csv_parser.parse(caminho)
    if tipo == "pdf":
        from parsers import pdf_parser
        return pdf_parser.parse(caminho)
    if tipo == "imagem":
        from parsers import image_parser
        return image_parser.parse(caminho)


def main():
    parser = argparse.ArgumentParser(
        description="Lê notas fiscais (CSV, PDF ou imagem) de uma pasta, "
        "extrai os itens e envia para uma planilha do Google Sheets."
    )
    parser.add_argument("pasta", help="Caminho da pasta com as notas fiscais")
    parser.add_argument(
        "--recursivo",
        action="store_true",
        help="Também processa subpastas dentro da pasta informada",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.pasta):
        print(f"Erro: a pasta '{args.pasta}' não existe.")
        sys.exit(1)

    # Import feito aqui para dar um erro de configuração claro antes de
    # começar a processar arquivos (evita gastar tempo com OCR só pra
    # falhar no final por falta de config.json).
    import sheets_writer

    if args.recursivo:
        arquivos = [
            os.path.join(raiz, nome)
            for raiz, _dirs, nomes in os.walk(args.pasta)
            for nome in nomes
        ]
    else:
        arquivos = [
            os.path.join(args.pasta, nome)
            for nome in os.listdir(args.pasta)
            if os.path.isfile(os.path.join(args.pasta, nome))
        ]

    todos_itens = []
    for caminho in sorted(arquivos):
        ext = os.path.splitext(caminho)[1].lower()
        if ext not in EXTENSOES:
            continue
        print(f"Processando: {os.path.basename(caminho)}")
        try:
            itens = _processar_arquivo(caminho) or []
        except Exception as e:
            print(f"  [erro] Falha ao processar este arquivo: {e}")
            continue
        print(f"  -> {len(itens)} item(ns) encontrado(s)")
        todos_itens.extend(itens)

    print(f"\nTotal de itens extraídos: {len(todos_itens)}")
    sheets_writer.enviar_itens(todos_itens)


if __name__ == "__main__":
    main()
