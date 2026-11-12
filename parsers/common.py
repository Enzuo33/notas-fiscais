"""Funções compartilhadas pelos parsers: normalização de texto, mapeamento
de colunas/cabeçalhos e um parser genérico de linhas por regex, usado como
último recurso quando não é possível achar uma tabela estruturada (PDFs
sem tabela e texto vindo de OCR)."""

import re
import unicodedata

COLUNAS = ["descricao", "quantidade", "valor_unitario", "valor_total"]

_KEYWORDS = {
    "descricao": ["descricao", "produto", "discriminacao", "item", "mercadoria"],
    "quantidade": ["quantidade", "qtde", "qtd", "quant"],
    "valor_unitario": ["valorunitario", "valorunit", "vlunit", "unitario", "precounitario", "preco"],
    "valor_total": ["valortotal", "vltotal", "total"],
}

# Ordem importa: valor_total precisa ser checado antes de algo genérico
# demais, e valor_unitario antes de "total" para não confundir "vl. unit."
_ORDEM_CHECAGEM = ["valor_unitario", "valor_total", "quantidade", "descricao"]


def normalizar(texto: str) -> str:
    """Remove acentos, baixa a caixa e tira espaços/pontuação para comparar
    cabeçalhos de forma tolerante (ex.: 'Vl. Unitário' == 'valor unitario')."""
    if texto is None:
        return ""
    texto = str(texto)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]", "", texto)
    return texto


def mapear_cabecalho(celulas):
    """Recebe uma lista de células de cabeçalho (linha de uma tabela/CSV) e
    devolve um dict {indice_da_coluna: nome_campo} para os campos que
    conseguiu identificar (descricao, quantidade, valor_unitario, valor_total).
    """
    mapa = {}
    for idx, celula in enumerate(celulas):
        norm = normalizar(celula)
        if not norm:
            continue
        for campo in _ORDEM_CHECAGEM:
            if campo in mapa.values():
                continue
            if any(chave in norm for chave in _KEYWORDS[campo]):
                mapa[idx] = campo
                break
    return mapa


def numero_para_valor(texto: str):
    """Converte '1.234,56' ou '1,00' ou '10' em float. Retorna None se não
    conseguir reconhecer um número no texto."""
    if texto is None:
        return None
    texto = str(texto).strip().replace("R$", "").strip()
    if not texto:
        return None
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


_LINHA_ITEM_RE = re.compile(
    r"^(?P<descricao>.{3,80}?)\s+"
    r"(?P<quantidade>\d{1,5}(?:[.,]\d{1,3})?)\s*"
    r"(?:UN|UND|UNID|PC|PCT|KG|CX|LT|L)?\s+"
    r"(?:R\$)?\s*(?P<valor_unitario>\d{1,3}(?:\.\d{3})+,\d{2}|\d{1,6}[.,]\d{2})\s+"
    r"(?:R\$)?\s*(?P<valor_total>\d{1,3}(?:\.\d{3})+,\d{2}|\d{1,7}[.,]\d{2})\s*$",
    re.IGNORECASE,
)


def parse_linhas_genericas(texto: str, arquivo: str):
    """Fallback heurístico: varre linha a linha um texto solto (extraído de
    PDF sem tabela, ou de OCR) procurando o padrão comum
    'descrição  quantidade  valor unitário  valor total'.

    Não é garantido funcionar em todo layout de nota — por isso sempre
    devolve também a linha bruta, para conferência manual na planilha."""
    itens = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        m = _LINHA_ITEM_RE.match(linha)
        # Descrição sem nenhuma letra é linha de números (ex.: impostos
        # "0,00 0,00 0,00 0,00"), não um item.
        if not m or not re.search(r"[^\W\d_]", m.group("descricao")):
            continue
        itens.append(
            {
                "arquivo": arquivo,
                "descricao": m.group("descricao").strip(" -.:"),
                "quantidade": numero_para_valor(m.group("quantidade")),
                "valor_unitario": numero_para_valor(m.group("valor_unitario")),
                "valor_total": numero_para_valor(m.group("valor_total")),
                "linha_original": linha,
            }
        )
    return itens
