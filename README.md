# Notas Fiscais → Google Sheets

## App com janela (Notas → CSV)

`dist\NotasParaCSV.exe` é a versão com interface: ao abrir, pede as notas
(PDF ou CSV do computador), mostra os itens numa tabela organizada
(ordenável, com opção de juntar produtos repetidos) e salva numa planilha
do Excel (.xlsx) já formatada — ou em CSV, se escolher no salvar. Não
precisa de Python, `config.json` nem credenciais — é só mandar o `.exe`.

- Fotos/imagens não são aceitas no app (só no `main.py`). PDF escaneado
  (sem texto) mostra um aviso em vez de tentar OCR, a não ser que o
  Tesseract esteja instalado no computador.
- Para rodar pelo código: `python app.py`.
- Para gerar o `.exe` de novo:

```powershell
.\venv\Scripts\pyinstaller.exe --noconfirm --onefile --windowed --name NotasParaCSV --icon icone.ico --add-data "icone.ico;." --collect-all customtkinter --collect-all pypdfium2 --collect-all pypdfium2_raw --exclude-module googleapiclient --exclude-module google --exclude-module pandas app.py
```

O resto deste README é sobre o `main.py` (linha de comando, envia para o
Google Sheets).

Lê notas fiscais em CSV, PDF ou imagem (foto/scan) de uma pasta, tenta extrair
os itens (descrição, quantidade, valor unitário, valor total) e envia tudo
para uma aba de uma planilha do Google Sheets.

> **Importante sobre precisão:** notas fiscais em PDF/imagem têm layouts
> muito diferentes entre emissores. O programa tenta identificar tabelas de
> itens automaticamente e, quando não consegue, usa um padrão genérico por
> regex. Sempre grava a **linha original** ao lado do item extraído na
> planilha, para você conferir e corrigir manualmente os casos que saírem
> errados.

## 1. Instalar dependências Python

```powershell
cd notas-fiscais-sheets
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Instalar o Tesseract OCR (necessário para imagens e PDFs escaneados)

Baixe e instale o Tesseract para Windows:
https://github.com/UB-Mannheim/tesseract/wiki

Durante a instalação, marque o pacote de idioma **Portuguese**. Depois de
instalado, anote o caminho do `tesseract.exe` (geralmente
`C:\Program Files\Tesseract-OCR\tesseract.exe`) — você vai colocar esse
caminho no `config.json` (passo 5).

## 3. (Não é mais necessário) Poppler

PDFs escaneados agora são convertidos em imagem pelo próprio pdfplumber; o
`poppler_path` do `config.json` é ignorado.

## 4. Criar a conta de serviço do Google e liberar a planilha

1. Acesse https://console.cloud.google.com/ e crie um projeto (ou use um
   existente).
2. Ative a **Google Sheets API** (menu "APIs e serviços" → "Biblioteca").
3. Vá em "APIs e serviços" → "Credenciais" → "Criar credenciais" →
   "Conta de serviço". Dê um nome qualquer e conclua.
4. Abra a conta de serviço criada, aba "Chaves" → "Adicionar chave" →
   "Criar nova chave" → tipo **JSON**. Um arquivo `.json` será baixado.
5. Renomeie esse arquivo para `credentials.json` e coloque na pasta deste
   projeto (`notas-fiscais-sheets\credentials.json`).
6. Abra o arquivo `credentials.json` e copie o valor de `"client_email"`
   (algo como `xxxx@xxxx.iam.gserviceaccount.com`).
7. Na sua planilha do Google Sheets, clique em "Compartilhar" e adicione
   esse e-mail como **Editor**.
8. Copie o **ID da planilha** — é o trecho da URL entre `/d/` e `/edit`:
   `https://docs.google.com/spreadsheets/d/ESTE_TRECHO_AQUI/edit`

## 5. Configurar o projeto

Copie `config.example.json` para `config.json` e preencha:

```json
{
  "spreadsheet_id": "ID_DA_SUA_PLANILHA",
  "sheet_name": "Itens",
  "credentials_path": "credentials.json",
  "tesseract_cmd": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
  "poppler_path": "C:\\caminho\\para\\poppler\\Library\\bin"
}
```

- `sheet_name`: nome da aba dentro da planilha onde os itens serão
  gravados (crie essa aba na planilha se ainda não existir).
- `poppler_path`: pode deixar `""` se você não for processar PDFs
  escaneados (sem texto).

## 6. Rodar

```powershell
python main.py "C:\caminho\para\pasta\com\notas"
```

Para incluir subpastas:

```powershell
python main.py "C:\caminho\para\pasta\com\notas" --recursivo
```

O programa imprime, para cada arquivo, quantos itens encontrou, e ao final
envia tudo de uma vez para a planilha (colunas: Arquivo de Origem,
Descrição, Quantidade, Valor Unitário, Valor Total, Linha Original,
Processado em).

## Formatos suportados

| Formato | Como é lido |
|---|---|
| `.csv` | Lê o cabeçalho e tenta reconhecer colunas de descrição/quantidade/valor. Se não reconhecer, joga a linha inteira na coluna Descrição para revisão. |
| `.pdf` | Tenta extrair tabelas de itens diretamente do PDF. Se não achar tabela, tenta um padrão de texto genérico. Se o PDF não tiver texto (é uma imagem escaneada), faz OCR página por página (requer Poppler). |
| `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff` | Faz OCR (Tesseract) e aplica o mesmo padrão de texto genérico usado no PDF. |

## Arquivos sensíveis

`credentials.json` e `config.json` contêm segredos/identificadores da sua
planilha — não compartilhe nem suba para repositórios públicos.
