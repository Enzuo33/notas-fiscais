import os

from PIL import Image

from parsers import danfe
from parsers.common import parse_linhas_genericas
from parsers.ocr import texto_da_imagem


def parse(caminho: str):
    nome_arquivo = os.path.basename(caminho)
    with Image.open(caminho) as imagem:
        texto = texto_da_imagem(imagem)
    itens = danfe.parse_texto(texto, nome_arquivo) or parse_linhas_genericas(texto, nome_arquivo)

    if not itens:
        print(
            f"  [aviso] Nenhum item reconhecido em '{nome_arquivo}' via OCR. "
            f"A imagem pode estar com baixa qualidade/ângulo ruim, ou o "
            f"layout da nota não bate com o padrão esperado."
        )
    return itens
