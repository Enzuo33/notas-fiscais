"""Interface gráfica: escolhe notas fiscais (PDF ou CSV), mostra os
itens extraídos numa tabela e salva tudo em CSV (formato do Excel em
português: separador ';', vírgula decimal)."""

import csv
import os
import queue
import sys
import threading
import tkinter as tk
import unicodedata
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from main import _processar_arquivo
from parsers.ocr import TesseractAusente

# Só arquivos PDF e CSV: fotos ficam de fora do app (o main.py ainda aceita).
EXTENSOES = (".pdf", ".csv")

VERDE = "#1f9d6b"
VERDE_ESCURO = "#17805a"
FUNDO = "#f4f6f8"
CARTAO = "#ffffff"
TEXTO = "#1d2733"
TEXTO_SUAVE = "#6b7785"

TIPOS_ARQUIVO = [
    ("Notas fiscais (PDF ou CSV)", "*.pdf *.csv"),
    ("PDF", "*.pdf"),
    ("CSV", "*.csv"),
]

CABECALHO = [
    "Arquivo de Origem",
    "Código",
    "Descrição",
    "Unidade",
    "Quantidade",
    "Valor Unitário",
    "Valor Total",
]


def recurso(nome):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nome)


def texto(item, campo):
    """Valor de texto numa linha só (quebras de linha bagunçam o CSV no Excel)."""
    return " ".join(str(item.get(campo) or "").split())


def formatar_numero(valor):
    """1234.5 -> '1.234,50' (padrão brasileiro)."""
    if valor is None or valor == "":
        return ""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_quantidade(valor):
    if valor is None or valor == "":
        return ""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if valor.is_integer():
        return str(int(valor))
    return f"{valor:.3f}".rstrip("0").replace(".", ",")


def chave_texto(valor):
    """Para ordenar texto ignorando acentos e maiúsculas ('Água' junto de 'AGUA')."""
    valor = unicodedata.normalize("NFKD", " ".join(str(valor or "").split()))
    return "".join(c for c in valor if not unicodedata.combining(c)).casefold()


COLUNAS_NUMERICAS = ("quantidade", "valor_unitario", "valor_total")


def ordenar(itens, coluna, decrescente):
    """Ordena pela coluna; itens sem valor nela vão sempre para o fim."""
    def valor(item):
        bruto = item.get(coluna)
        if coluna in COLUNAS_NUMERICAS:
            return bruto if isinstance(bruto, (int, float)) else None
        return chave_texto(bruto) or None

    com_valor = [i for i in itens if valor(i) is not None]
    sem_valor = [i for i in itens if valor(i) is None]
    # Desempate pela descrição, para a ordem ficar previsível.
    com_valor.sort(key=lambda i: chave_texto(i.get("descricao")))
    com_valor.sort(key=valor, reverse=decrescente)
    return com_valor + sem_valor


def juntar_repetidos(itens):
    """Mesmo produto (descrição + unidade) em várias linhas/notas vira uma
    linha só, somando quantidade e valor total."""
    grupos = {}
    for item in itens:
        chave = (chave_texto(item.get("descricao")), chave_texto(item.get("unidade")))
        grupos.setdefault(chave, []).append(item)

    resultado = []
    for grupo in grupos.values():
        if len(grupo) == 1:
            resultado.append(grupo[0])
            continue

        def unicos(campo):
            vistos = []
            for i in grupo:
                v = texto(i, campo)
                if v and v not in vistos:
                    vistos.append(v)
            return ", ".join(vistos)

        def soma(campo):
            valores = [i.get(campo) for i in grupo if isinstance(i.get(campo), (int, float))]
            return sum(valores) if valores else None

        quantidade, total = soma("quantidade"), soma("valor_total")
        resultado.append({
            "arquivo": unicos("arquivo"),
            "codigo": unicos("codigo"),
            "descricao": texto(grupo[0], "descricao"),
            "unidade": texto(grupo[0], "unidade"),
            "quantidade": quantidade,
            "valor_unitario": (
                total / quantidade if quantidade and total is not None
                else grupo[0].get("valor_unitario")
            ),
            "valor_total": total,
        })
    return resultado


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title("Notas Fiscais → CSV")
        self.geometry("1060x680")
        self.minsize(820, 520)
        self.configure(fg_color=FUNDO)
        try:
            self.iconbitmap(recurso("icone.ico"))
        except tk.TclError:
            pass

        self.itens = []
        self.fila = queue.Queue()
        self.processando = False
        # Já começa organizado em ordem alfabética de descrição.
        self.ordem_coluna = "descricao"
        self.ordem_decrescente = False
        self.juntar = tk.BooleanVar(value=False)

        self._montar_cabecalho()
        self._montar_barra_organizar()
        self._montar_tabela()
        self._montar_rodape()
        self._atualizar_estado()

        # Pede o arquivo logo ao abrir.
        self.after(400, self._abrir_na_frente)

    def _abrir_na_frente(self):
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        self.after(300, lambda: self.attributes("-topmost", False))
        self.escolher_arquivos()

    # ---------- layout ----------

    def _montar_cabecalho(self):
        topo = ctk.CTkFrame(self, fg_color=FUNDO)
        topo.pack(fill="x", padx=28, pady=(24, 12))

        textos = ctk.CTkFrame(topo, fg_color=FUNDO)
        textos.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            textos, text="Notas Fiscais → CSV", text_color=TEXTO,
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            textos,
            text="Escolha notas em PDF ou CSV do seu computador. Os itens aparecem abaixo e você salva tudo numa planilha do Excel.",
            text_color=TEXTO_SUAVE, font=ctk.CTkFont(size=13),
        ).pack(anchor="w", pady=(2, 0))

        self.botao_escolher = ctk.CTkButton(
            topo, text="＋  Escolher notas", command=self.escolher_arquivos,
            fg_color=VERDE, hover_color=VERDE_ESCURO, height=42, corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.botao_escolher.pack(side="right")

    def _montar_barra_organizar(self):
        barra = ctk.CTkFrame(self, fg_color=FUNDO)
        barra.pack(fill="x", padx=30, pady=(0, 4))
        ctk.CTkLabel(
            barra, text="Clique no título de uma coluna para ordenar por ela (clique de novo para inverter).",
            text_color=TEXTO_SUAVE, font=ctk.CTkFont(size=12),
        ).pack(side="left")
        ctk.CTkSwitch(
            barra, text="Juntar produtos repetidos", variable=self.juntar,
            command=self._renderizar, progress_color=VERDE, text_color=TEXTO,
            font=ctk.CTkFont(size=13),
        ).pack(side="right")

    def _montar_tabela(self):
        cartao = ctk.CTkFrame(self, fg_color=CARTAO, corner_radius=14)
        cartao.pack(fill="both", expand=True, padx=28, pady=6)

        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure(
            "Notas.Treeview", background=CARTAO, fieldbackground=CARTAO,
            foreground=TEXTO, rowheight=30, borderwidth=0, font=("Segoe UI", 10),
        )
        estilo.configure(
            "Notas.Treeview.Heading", background="#eef1f4", foreground=TEXTO,
            relief="flat", font=("Segoe UI", 10, "bold"), padding=(8, 8),
        )
        estilo.map("Notas.Treeview.Heading", background=[("active", "#e2e7ec")])
        estilo.map(
            "Notas.Treeview", background=[("selected", "#d6f1e5")],
            foreground=[("selected", TEXTO)],
        )
        estilo.layout("Notas.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        colunas = ("arquivo", "codigo", "descricao", "unidade", "quantidade", "valor_unitario", "valor_total")
        self.tabela = ttk.Treeview(
            cartao, columns=colunas, show="headings", style="Notas.Treeview",
        )
        self.titulos = {}
        for coluna, titulo, largura, ancora in [
            ("arquivo", "Arquivo", 150, "w"),
            ("codigo", "Código", 80, "w"),
            ("descricao", "Descrição", 380, "w"),
            ("unidade", "Un.", 50, "center"),
            ("quantidade", "Qtd.", 70, "e"),
            ("valor_unitario", "Valor unit.", 110, "e"),
            ("valor_total", "Valor total", 120, "e"),
        ]:
            self.titulos[coluna] = titulo
            self.tabela.heading(
                coluna, text=titulo, anchor=ancora,
                command=lambda c=coluna: self.ordenar_por(c),
            )
            self.tabela.column(coluna, width=largura, anchor=ancora, stretch=coluna == "descricao")
        self._atualizar_titulos()
        self.tabela.tag_configure("par", background="#f8fafb")

        rolagem = ctk.CTkScrollbar(cartao, command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=rolagem.set)
        rolagem.pack(side="right", fill="y", padx=(0, 6), pady=10)
        self.tabela.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=14)

        self.vazio = ctk.CTkLabel(
            cartao, text="Nenhuma nota carregada ainda.\nClique em “Escolher notas” para começar.",
            text_color=TEXTO_SUAVE, font=ctk.CTkFont(size=15), fg_color=CARTAO,
        )

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color=FUNDO)
        rodape.pack(fill="x", padx=28, pady=(10, 22))

        esquerda = ctk.CTkFrame(rodape, fg_color=FUNDO)
        esquerda.pack(side="left", fill="x", expand=True)
        self.resumo = ctk.CTkLabel(
            esquerda, text="", text_color=TEXTO, font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.resumo.pack(anchor="w")
        self.status = ctk.CTkLabel(
            esquerda, text="", text_color=TEXTO_SUAVE, font=ctk.CTkFont(size=12),
            justify="left", wraplength=560,
        )
        self.status.pack(anchor="w")
        self.progresso = ctk.CTkProgressBar(esquerda, progress_color=VERDE, width=320)

        self.botao_salvar = ctk.CTkButton(
            rodape, text="Salvar planilha", command=self.salvar,
            fg_color=VERDE, hover_color=VERDE_ESCURO, height=42, width=170,
            corner_radius=10, font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.botao_salvar.pack(side="right")
        self.botao_limpar = ctk.CTkButton(
            rodape, text="Limpar", command=self.limpar,
            fg_color="transparent", border_width=1, border_color="#cfd6dd",
            text_color=TEXTO, hover_color="#e9edf1", height=42, width=100, corner_radius=10,
        )
        self.botao_limpar.pack(side="right", padx=10)

    # ---------- ações ----------

    def escolher_arquivos(self):
        if self.processando:
            return
        caminhos = filedialog.askopenfilenames(
            parent=self, title="Escolha as notas fiscais", filetypes=TIPOS_ARQUIVO,
        )
        if caminhos:
            self._processar(list(caminhos))

    def _processar(self, caminhos):
        self.processando = True
        self.erros = []
        self.progresso.set(0)
        self.progresso.pack(anchor="w", pady=(6, 0))
        self._atualizar_estado()
        threading.Thread(target=self._trabalhar, args=(caminhos,), daemon=True).start()
        self.after(100, self._verificar_fila)

    def _trabalhar(self, caminhos):
        for i, caminho in enumerate(caminhos):
            nome = os.path.basename(caminho)
            self.fila.put(("status", f"Lendo {nome}…  ({i + 1} de {len(caminhos)})", i / len(caminhos)))
            if os.path.splitext(caminho)[1].lower() not in EXTENSOES:
                self.fila.put(("erro", f"{nome}: formato não suportado (use PDF ou CSV)"))
                continue
            try:
                itens = _processar_arquivo(caminho) or []
            except TesseractAusente:
                self.fila.put(("erro", f"{nome}: é um PDF escaneado (foto), sem texto para converter"))
                continue
            except Exception as e:  # um arquivo ruim não derruba os outros
                self.fila.put(("erro", f"{nome}: {e}"))
                continue
            if not itens:
                self.fila.put(("erro", f"{nome}: nenhum item reconhecido"))
            self.fila.put(("itens", itens))
        self.fila.put(("fim",))

    def _verificar_fila(self):
        try:
            while True:
                msg = self.fila.get_nowait()
                if msg[0] == "status":
                    self.status.configure(text=msg[1])
                    self.progresso.set(msg[2])
                elif msg[0] == "erro":
                    self.erros.append(msg[1])
                elif msg[0] == "itens":
                    self._adicionar_itens(msg[1])
                elif msg[0] == "fim":
                    self._finalizar()
                    return
        except queue.Empty:
            pass
        self.after(100, self._verificar_fila)

    def _adicionar_itens(self, itens):
        self.itens.extend(itens)
        self._renderizar()

    def itens_organizados(self):
        """O que aparece na tela e vai para o CSV: juntado (se ligado) e ordenado."""
        itens = juntar_repetidos(self.itens) if self.juntar.get() else self.itens
        return ordenar(itens, self.ordem_coluna, self.ordem_decrescente)

    def ordenar_por(self, coluna):
        if coluna == self.ordem_coluna:
            self.ordem_decrescente = not self.ordem_decrescente
        else:
            self.ordem_coluna = coluna
            # Valores costumam interessar do maior para o menor.
            self.ordem_decrescente = coluna in COLUNAS_NUMERICAS
        self._atualizar_titulos()
        self._renderizar()

    def _atualizar_titulos(self):
        for coluna, titulo in self.titulos.items():
            if coluna == self.ordem_coluna:
                titulo += "  ▼" if self.ordem_decrescente else "  ▲"
            self.tabela.heading(coluna, text=titulo)

    def _renderizar(self):
        self.tabela.delete(*self.tabela.get_children())
        for indice, item in enumerate(self.itens_organizados()):
            self.tabela.insert(
                "", "end", tags=("par",) if indice % 2 else (),
                values=(
                    texto(item, "arquivo"),
                    texto(item, "codigo"),
                    texto(item, "descricao"),
                    texto(item, "unidade"),
                    formatar_quantidade(item.get("quantidade")),
                    formatar_numero(item.get("valor_unitario")),
                    formatar_numero(item.get("valor_total")),
                ),
            )
        self._atualizar_estado()

    def _finalizar(self):
        self.processando = False
        self.progresso.pack_forget()
        if self.erros:
            self.status.configure(text="Atenção: " + " • ".join(self.erros))
        else:
            self.status.configure(text="Pronto! Confira os itens e clique em “Salvar planilha”.")
        self._atualizar_estado()
        if self.erros and not self.itens:
            messagebox.showwarning(
                "Nenhum item encontrado",
                "Não consegui extrair itens desses arquivos:\n\n" + "\n".join(self.erros),
                parent=self,
            )

    def _atualizar_estado(self):
        if self.itens:
            self.vazio.place_forget()
            total = sum(i.get("valor_total") or 0 for i in self.itens if isinstance(i.get("valor_total"), (int, float)))
            arquivos = len({i.get("arquivo") for i in self.itens})
            quantos = f"{len(self.itens)} item(ns)"
            if self.juntar.get():
                quantos = f"{len(juntar_repetidos(self.itens))} produto(s) ({len(self.itens)} itens)"
            self.resumo.configure(
                text=f"{quantos} de {arquivos} nota(s)  •  Total R$ {formatar_numero(total)}"
            )
        else:
            self.vazio.place(relx=0.5, rely=0.5, anchor="center")
            self.resumo.configure(text="")
        ocupado = "disabled" if self.processando else "normal"
        self.botao_escolher.configure(state=ocupado)
        self.botao_limpar.configure(state=ocupado if self.itens else "disabled")
        self.botao_salvar.configure(state=ocupado if self.itens else "disabled")

    def limpar(self):
        self.itens = []
        self.status.configure(text="")
        self._renderizar()

    def salvar(self):
        primeiro = self.itens[0].get("arquivo", "notas") if self.itens else "notas"
        caminho = filedialog.asksaveasfilename(
            parent=self, title="Salvar planilha", defaultextension=".xlsx",
            initialfile=os.path.splitext(primeiro)[0] + ".xlsx",
            filetypes=[("Planilha do Excel", "*.xlsx"), ("CSV (texto simples)", "*.csv")],
        )
        if not caminho:
            return
        try:
            if caminho.lower().endswith(".csv"):
                escrever_csv(caminho, self.itens_organizados())
            else:
                escrever_xlsx(caminho, self.itens_organizados())
        except OSError as e:
            messagebox.showerror(
                "Não deu pra salvar",
                f"Não consegui salvar o arquivo.\nSe ele estiver aberto no Excel, feche e tente de novo.\n\n{e}",
                parent=self,
            )
            return
        if messagebox.askyesno("Planilha salva!", f"Arquivo salvo em:\n{caminho}\n\nQuer abrir agora?", parent=self):
            os.startfile(caminho)


def escrever_csv(caminho, itens):
    # utf-8-sig + ';' + vírgula decimal: abre certinho no Excel em português.
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(CABECALHO)
        for item in itens:
            escritor.writerow([
                texto(item, "arquivo"),
                texto(item, "codigo"),
                texto(item, "descricao"),
                texto(item, "unidade"),
                formatar_quantidade(item.get("quantidade")),
                formatar_numero(item.get("valor_unitario")).replace(".", ""),
                formatar_numero(item.get("valor_total")).replace(".", ""),
            ])


def escrever_xlsx(caminho, itens):
    """Planilha do Excel já formatada: cabeçalho destacado e fixo, filtro,
    larguras certas, valores em R$ (como número, dá pra somar/ordenar) e
    linha de total no fim."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    livro = Workbook()
    aba = livro.active
    aba.title = "Itens"
    aba.append(CABECALHO)

    def numero(valor):
        if not isinstance(valor, (int, float)):
            return None
        return int(valor) if float(valor).is_integer() else valor

    def codigo(item):
        # Código só com dígitos vira número (evita o aviso verde do Excel),
        # a não ser que comece com zero, que se perderia.
        valor = texto(item, "codigo")
        return int(valor) if valor.isdigit() and not valor.startswith("0") else valor

    for item in itens:
        aba.append([
            texto(item, "arquivo"),
            codigo(item),
            texto(item, "descricao"),
            texto(item, "unidade"),
            numero(item.get("quantidade")),
            numero(item.get("valor_unitario")),
            numero(item.get("valor_total")),
        ])

    ultima = aba.max_row
    borda = Border(bottom=Side(style="thin", color="E2E7EC"))
    for celula in aba[1]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor=VERDE.lstrip("#"))
        celula.alignment = Alignment(vertical="center", horizontal="center")
    aba.row_dimensions[1].height = 24

    zebra = PatternFill("solid", fgColor="F4F7F9")
    for linha in range(2, ultima + 1):
        for coluna in range(1, len(CABECALHO) + 1):
            celula = aba.cell(linha, coluna)
            celula.border = borda
            if linha % 2 == 1:
                celula.fill = zebra
        aba.cell(linha, 6).number_format = '"R$" #,##0.00'
        aba.cell(linha, 7).number_format = '"R$" #,##0.00'

    if itens:
        total = ultima + 1
        aba.cell(total, 6, "TOTAL").font = Font(bold=True)
        aba.cell(total, 6).alignment = Alignment(horizontal="right")
        aba.cell(total, 7, f"=SUM(G2:G{ultima})").font = Font(bold=True)
        aba.cell(total, 7).number_format = '"R$" #,##0.00'
        aba.cell(total, 7).border = Border(top=Side(style="medium", color=VERDE.lstrip("#")))

    for celula in aba["B"][1:]:
        celula.alignment = Alignment(horizontal="left")
    for indice, largura in enumerate([24, 13, 48, 12, 15, 18, 17], start=1):
        aba.column_dimensions[get_column_letter(indice)].width = largura
    aba.freeze_panes = "A2"
    aba.auto_filter.ref = f"A1:{get_column_letter(len(CABECALHO))}{ultima}"
    livro.save(caminho)


if __name__ == "__main__":
    App().mainloop()
