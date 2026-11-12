# NotasParaCSV

lê notas fiscais (PDF ou CSV), mostra os itens numa tabela e salva em planilha.

- tabela ordenável, com opção de juntar produtos repetidos
- salva em Excel (.xlsx) já formatado ou em CSV
- tenta achar a tabela de itens no PDF sozinho; se não acha, cai num padrão genérico
- PDF escaneado (sem texto) só funciona com o Tesseract instalado; sem ele o app avisa

## rodar

```
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## gerar .exe

```
.\venv\Scripts\pyinstaller.exe --noconfirm --onefile --windowed --name NotasParaCSV --icon icone.ico --add-data "icone.ico;." --collect-all customtkinter --collect-all pypdfium2 --collect-all pypdfium2_raw --exclude-module googleapiclient --exclude-module google --exclude-module pandas app.py
```
