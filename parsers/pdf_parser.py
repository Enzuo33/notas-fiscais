import os

import pdfplumber

from parsers import danfe
from parsers.common import mapear_cabecalho, normalizar, numero_para_valor, parse_linhas_genericas
from parsers.ocr import texto_da_imagem


def _itens_de_tabela(tabela, nome_arquivo):
    if not tabela or len(tabela) < 2:
        return None
    mapa = mapear_cabecalho(tabela[0])
    # Exige descrição + pelo menos uma coluna de número, senão qualquer
    # quadro com "produto" no título (ex.: "V. TOTAL PRODUTOS") vira item.
    if "descricao" not in mapa.values() or len(mapa) < 2:
        return None

    itens = []
    for linha in tabela[1:]:
        if not linha or not any((c or "").strip() for c in linha):
            continue
        item = {
            "arquivo": nome_arquivo,
            "linha_original": " | ".join((c or "").strip() for c in linha),
        }
        for idx, campo in mapa.items():
            if idx < len(linha):
                valor = (linha[idx] or "").strip()
                if campo in ("quantidade", "valor_unitario", "valor_total"):
                    valor = numero_para_valor(valor)
                item[campo] = valor
        item.setdefault("descricao", "")
        item.setdefault("quantidade", None)
        item.setdefault("valor_unitario", None)
        item.setdefault("valor_total", None)
        if item["descricao"]:
            itens.append(item)
    return itens or None


def _itens_de_celulas_rotuladas(tabela, nome_arquivo):
    """Notas de serviço (NFS-e, ex.: Barueri) trazem rótulo e valor na mesma
    célula ("Qtde\\n1", "Valor Total\\n14.004,29"), sem linha de cabeçalho
    separada: cada linha da tabela com esses rótulos vira um item."""
    itens = []
    for linha in tabela or []:
        celulas = [(c or "").strip() for c in linha]
        rotulos = [c.split("\n", 1)[0] if "\n" in c else "" for c in celulas]
        mapa = mapear_cabecalho(rotulos)
        # Descrição + pelo menos dois campos, para não pegar quadros soltos
        # como "DISCRIMINAÇÃO DOS SERVIÇOS".
        if "descricao" not in mapa.values() or len(mapa) < 3:
            continue
        item = {
            "arquivo": nome_arquivo,
            "linha_original": " | ".join(" ".join(c.split()) for c in celulas if c),
        }
        for idx, campo in mapa.items():
            valor = " ".join(celulas[idx].split("\n", 1)[1].split())
            if campo in ("quantidade", "valor_unitario", "valor_total"):
                valor = numero_para_valor(valor)
            item[campo] = valor
        for idx, rotulo in enumerate(rotulos):
            if idx not in mapa and normalizar(rotulo).startswith("codigo"):
                item["codigo"] = " ".join(celulas[idx].split("\n", 1)[1].split())
                break
        item.setdefault("quantidade", None)
        item.setdefault("valor_unitario", None)
        item.setdefault("valor_total", None)
        if item["descricao"]:
            itens.append(item)
    return itens or None


def _ocr_paginas(caminho: str, nome_arquivo: str):
    """PDF escaneado (imagem, sem texto/tabela extraível): renderiza cada
    página como imagem (pdfplumber já faz isso, sem Poppler) e aplica OCR.
    Requer o Tesseract instalado."""
    itens = []
    with pdfplumber.open(caminho) as pdf:
        for pagina in pdf.pages:
            imagem = pagina.to_image(resolution=300).original
            texto = texto_da_imagem(imagem)
            itens.extend(
                danfe.parse_texto(texto, nome_arquivo)
                or parse_linhas_genericas(texto, nome_arquivo)
            )
    return itens


def parse(caminho: str):
    nome_arquivo = os.path.basename(caminho)
    itens = []
    texto_total = []

    with pdfplumber.open(caminho) as pdf:
        for pagina in pdf.pages:
            for tabela in pagina.extract_tables() or []:
                encontrados = (
                    _itens_de_tabela(tabela, nome_arquivo)
                    or _itens_de_celulas_rotuladas(tabela, nome_arquivo)
                )
                if encontrados:
                    itens.extend(encontrados)
            texto_pagina = pagina.extract_text() or ""
            texto_total.append(texto_pagina)

    texto_completo = "\n".join(texto_total).strip()

    # DANFE (NF-e) tem layout padrão: quando reconhecido, é o mais confiável.
    itens_danfe = danfe.parse_texto(texto_completo, nome_arquivo)
    if itens_danfe:
        return itens_danfe

    if itens:
        return itens

    if texto_completo:
        return parse_linhas_genericas(texto_completo, nome_arquivo)

    # Sem texto e sem tabela: provavelmente é um PDF escaneado (imagem).
    return _ocr_paginas(caminho, nome_arquivo)
