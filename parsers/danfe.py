"""Leitor do quadro "DADOS DOS PRODUTOS / SERVIÇOS" da DANFE (o PDF padrão
da NF-e). No texto extraído, cada produto vira uma linha do tipo:

    2263755 CAFE VACUO IGUACU TRAD 500G 09012100 0/20 5102 UN 4,0000 19,9000 79,60 0,00 ...
    código  descrição                   NCM      CST  CFOP UN quant  v.unit  v.total (impostos...)

Descrições longas quebram e continuam na linha seguinte ("C/100 UN"), e às
vezes vem uma linha de informação adicional ("Desconto de R$ 3,00")."""

import re

from parsers.common import numero_para_valor

_NUM = r"\d[\d.]*,\d+"

_ITEM_RE = re.compile(
    r"^(?P<codigo>\S+)\s+"
    r"(?P<descricao>.+?)\s*"
    r"(?P<ncm>\d{8})"
    r"(?:\s+\d[\d/]{1,5}){0,2}\s+"  # CST/CSOSN e CFOP
    rf"(?P<unidade>[A-Za-z]{{1,6}})\s+"
    rf"(?P<quantidade>{_NUM})\s+"
    rf"(?P<valor_unitario>{_NUM})\s+"
    r"(?P<valor_total>\d[\d.]*,\d{2})\b"
)

_FIM_DE_ITEM = ("DADOS", "IMPRESSO", "INFORMA", "CALCULO", "CÁLCULO", "TRANSPORT", "FOLHA", "RESERVADO")


def _continua_descricao(linha: str) -> bool:
    """Pedaço da descrição que quebrou de linha: curto e todo em maiúsculas
    (texto com minúsculas costuma ser informação adicional do item)."""
    return (
        len(linha) <= 25
        and not any(c.islower() for c in linha)
        and not any(p in linha.upper() for p in _FIM_DE_ITEM)
    )


def parse_texto(texto: str, arquivo: str):
    itens = []
    pode_continuar = False
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        m = _ITEM_RE.match(linha)
        if m:
            itens.append(
                {
                    "arquivo": arquivo,
                    "codigo": m.group("codigo"),
                    "descricao": m.group("descricao").strip(),
                    "unidade": m.group("unidade").upper(),
                    "quantidade": numero_para_valor(m.group("quantidade")),
                    "valor_unitario": numero_para_valor(m.group("valor_unitario")),
                    "valor_total": numero_para_valor(m.group("valor_total")),
                    "linha_original": linha,
                }
            )
            pode_continuar = True
        elif pode_continuar and _continua_descricao(linha):
            itens[-1]["descricao"] += " " + linha
            itens[-1]["linha_original"] += " " + linha
        else:
            pode_continuar = False
    return itens
