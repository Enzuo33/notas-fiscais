import csv
import os

from parsers.common import mapear_cabecalho, numero_para_valor


def _detectar_delimitador(amostra: str) -> str:
    try:
        return csv.Sniffer().sniff(amostra, delimiters=",;\t").delimiter
    except csv.Error:
        return ","


def parse(caminho: str):
    nome_arquivo = os.path.basename(caminho)
    with open(caminho, "r", encoding="utf-8-sig", errors="replace") as f:
        amostra = f.read(4096)
        f.seek(0)
        delimitador = _detectar_delimitador(amostra)
        leitor = list(csv.reader(f, delimiter=delimitador))

    if not leitor:
        return []

    cabecalho = leitor[0]
    mapa = mapear_cabecalho(cabecalho)
    linhas = leitor[1:]

    itens = []
    if "descricao" in mapa.values():
        for linha in linhas:
            if not any(c.strip() for c in linha):
                continue
            item = {"arquivo": nome_arquivo, "linha_original": delimitador.join(linha)}
            for idx, campo in mapa.items():
                if idx < len(linha):
                    valor = linha[idx].strip()
                    if campo in ("quantidade", "valor_unitario", "valor_total"):
                        valor = numero_para_valor(valor)
                    item[campo] = valor
            item.setdefault("descricao", "")
            item.setdefault("quantidade", None)
            item.setdefault("valor_unitario", None)
            item.setdefault("valor_total", None)
            itens.append(item)
    else:
        # Não achou colunas reconhecíveis: guarda a linha inteira como
        # "descrição" para revisão manual na planilha, em vez de descartar.
        for linha in ([cabecalho] + linhas):
            if not any(c.strip() for c in linha):
                continue
            itens.append(
                {
                    "arquivo": nome_arquivo,
                    "descricao": delimitador.join(linha),
                    "quantidade": None,
                    "valor_unitario": None,
                    "valor_total": None,
                    "linha_original": delimitador.join(linha),
                }
            )

    return itens
