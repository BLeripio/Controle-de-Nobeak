"""
Interface gráfica (janela) para o controle de nobreaks — feita para o
pessoal da manutenção usar sem precisar mexer no terminal.

Para rodar: python interface.py
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from models import Local, Nobreak, StatusNobreak, ANDARES_VALIDOS, nome_andar
from gerenciador import GerenciadorNobreaks, NumeroSerieJaExisteError

# --- Paleta de cores (visual mais moderno, flat) ---
COR_FUNDO_JANELA = "#eef1f6"
COR_FUNDO_CARTAO = "#ffffff"
COR_TEXTO = "#212529"
COR_TEXTO_SECUNDARIO = "#6c757d"
COR_BORDA_SUAVE = "#dfe3ea"
COR_DESTAQUE = "#2563eb"          # azul (seleção, botão principal)
COR_DESTAQUE_HOVER = "#1d4fd1"

COR_FUNCIONANDO = "#e6f6ec"       # fundo pastel da linha do nobreak
COR_DEFEITO = "#fdecea"
COR_MANUTENCAO = "#fff6e0"

COR_BOLINHA_FUNCIONANDO = "#22a35a"   # verde
COR_BOLINHA_DEFEITO = "#e5484d"       # vermelho
COR_BOLINHA_MANUTENCAO = "#f5a524"    # amarelo/laranja

COR_ALERTA_DOURADO = "#f0b429"        # "!" de pendência (sem número de série / duplicado)
COR_ALERTA_TEXTO = "#4a3300"

FONTE_PADRAO = ("Segoe UI", 10)
FONTE_TITULO_CARTAO = ("Segoe UI", 11, "bold")
FONTE_NEGRITO = ("Segoe UI", 10, "bold")

# Ícone da janela / barra de tarefas (precisa estar na mesma pasta deste arquivo)
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_ICONE = os.path.join(PASTA_ATUAL, "nobreak_icone.ico")


class DicaFerramenta:
    """Uma dica de texto simples que aparece ao passar o mouse sobre um widget."""

    def __init__(self, widget, texto: str):
        self.widget = widget
        self.texto = texto
        self.janela = None
        widget.bind("<Enter>", self._mostrar)
        widget.bind("<Leave>", self._esconder)

    def _mostrar(self, _evento=None):
        if self.janela or not self.texto:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.janela = tk.Toplevel(self.widget)
        self.janela.wm_overrideredirect(True)
        self.janela.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.janela, text=self.texto, bg="#333333", fg="white",
            font=("Segoe UI", 9), padx=8, pady=4, relief="solid", borderwidth=1,
        ).pack()

    def _esconder(self, _evento=None):
        if self.janela:
            self.janela.destroy()
            self.janela = None


def criar_campo_maiusculas(parent: tk.Frame, width: int = 30) -> ttk.Entry:
    """
    Cria um campo de texto (Entry) que converte tudo para maiúsculas
    automaticamente enquanto a pessoa digita, mesmo sem o Caps Lock ligado.
    Usado nos campos de setor, modelo e observação.
    """
    variavel = tk.StringVar()
    campo = ttk.Entry(parent, textvariable=variavel, width=width, font=FONTE_PADRAO)

    def _ao_digitar(*_args):
        texto_atual = variavel.get()
        texto_maiusculo = texto_atual.upper()
        if texto_atual != texto_maiusculo:
            posicao_cursor = campo.index(tk.INSERT)
            variavel.set(texto_maiusculo)
            campo.icursor(posicao_cursor)

    variavel.trace_add("write", _ao_digitar)
    return campo


class AppNobreaks(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Controle de Nobreaks - Hospital")
        self.geometry("1000x640")
        self.minsize(850, 480)
        self.configure(bg=COR_FUNDO_JANELA)

        if os.path.exists(CAMINHO_ICONE):
            # Pequeno atraso: no Windows, aplicar o ícone assim que a janela
            # ainda está sendo criada às vezes não reflete na barra de tarefas.
            self.after(150, self._aplicar_icone)

        self._configurar_estilo()

        self.gerenciador = GerenciadorNobreaks("nobreaks.db")

        # Estado da interface (o que está aberto/selecionado), mantido entre atualizações
        self.andares_abertos = {andar: False for andar in ANDARES_VALIDOS}
        self.numero_serie_selecionado = None
        self._widgets_nobreak = {}       # numero_serie -> widget da linha (para a busca rolar até ele)
        self._rolar_ate_pendente = None  # numero_serie a focar assim que a lista for redesenhada

        self._montar_resumo()
        self._montar_busca()
        self._montar_lista()
        self._montar_botoes()

        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self.atualizar_lista()
        self.after(400, self._verificar_pendencias_iniciais)

    def _aplicar_icone(self):
        try:
            self.iconbitmap(default=CAMINHO_ICONE)
        except tk.TclError:
            pass  # ícone incompatível com o sistema (ex: Linux/Mac) - ignora sem quebrar o app

    def _verificar_pendencias_iniciais(self):
        """Mostra um aviso, ao abrir o programa, se houver nobreaks sem número de
        série real ou possíveis duplicados - para lembrar de corrigir o cadastro."""
        sem_serie = self.gerenciador.buscar_sem_numero_serie_real()
        duplicados = self.gerenciador.buscar_possiveis_duplicados()

        if not sem_serie and not duplicados:
            return

        blocos = []

        if sem_serie:
            linhas = [f"• {nb.numero_serie} — {nome_andar(nb.local.andar)} / {nb.local.setor}" for nb in sem_serie]
            blocos.append(f"SEM NÚMERO DE SÉRIE ({len(sem_serie)}):\n" + "\n".join(linhas))

        if duplicados:
            linhas = [
                " x ".join(f"{nb.numero_serie} ({nb.local.setor})" for nb in grupo) for grupo in duplicados
            ]
            blocos.append("ESSES NOBREAKS ESTÃO DUPLICADOS:\n" + "\n".join(linhas))

        texto_completo = "\n\n".join(blocos) + "\n\nUse a opção 'Editar' para corrigir."
        JanelaPendencias(self, texto_completo)

    def _configurar_estilo(self):
        estilo = ttk.Style(self)
        # 'clam' permite personalizar cores dos botões em qualquer sistema operacional
        estilo.theme_use("clam")

        estilo.configure(
            "TButton", font=FONTE_PADRAO, padding=(12, 8), relief="flat", borderwidth=0
        )
        estilo.configure(
            "Primario.TButton", background=COR_DESTAQUE, foreground="white"
        )
        estilo.map("Primario.TButton", background=[("active", COR_DESTAQUE_HOVER)])

        estilo.configure(
            "Secundario.TButton", background="#e9ecef", foreground=COR_TEXTO
        )
        estilo.map("Secundario.TButton", background=[("active", "#dde1e6")])

        estilo.configure(
            "Perigo.TButton", background=COR_BOLINHA_DEFEITO, foreground="white"
        )
        estilo.map("Perigo.TButton", background=[("active", "#c53a3e")])

        estilo.configure("TEntry", padding=6)
        estilo.configure("TCombobox", padding=6, font=FONTE_PADRAO)
        self.option_add("*TCombobox*Listbox.font", FONTE_PADRAO)
        estilo.configure("Vertical.TScrollbar", background=COR_FUNDO_JANELA)

    # --- Montagem da interface ---

    def _montar_resumo(self):
        frame = tk.Frame(self, bg=COR_FUNDO_JANELA, pady=14, padx=16)
        frame.pack(fill="x")

        tk.Label(
            frame, text="Controle de Nobreaks", font=("Segoe UI", 15, "bold"),
            bg=COR_FUNDO_JANELA, fg=COR_TEXTO,
        ).pack(side="left")

        painel_pilulas = tk.Frame(frame, bg=COR_FUNDO_JANELA)
        painel_pilulas.pack(side="right")

        self.pilula_funcionando = self._criar_pilula(painel_pilulas, "Funcionando", COR_BOLINHA_FUNCIONANDO)
        self.pilula_defeito = self._criar_pilula(painel_pilulas, "Defeito", COR_BOLINHA_DEFEITO)
        self.pilula_manutencao = self._criar_pilula(painel_pilulas, "Manutenção", COR_BOLINHA_MANUTENCAO)

    def _criar_pilula(self, parent: tk.Frame, rotulo: str, cor: str) -> tk.Label:
        """Cria um 'selo' colorido com contagem (ex: uma bolinha + 'Funcionando: 3')."""
        caixa = tk.Frame(parent, bg=COR_FUNDO_CARTAO, padx=10, pady=6)
        caixa.pack(side="left", padx=6)

        bolinha = tk.Canvas(caixa, width=12, height=12, bg=COR_FUNDO_CARTAO, highlightthickness=0)
        bolinha.create_oval(1, 1, 11, 11, fill=cor, outline=cor)
        bolinha.pack(side="left")

        etiqueta = tk.Label(
            caixa, text=f"{rotulo}: 0", font=FONTE_NEGRITO, bg=COR_FUNDO_CARTAO, fg=COR_TEXTO
        )
        etiqueta.pack(side="left", padx=(6, 0))
        return etiqueta

    def _montar_busca(self):
        frame = tk.Frame(self, bg=COR_FUNDO_JANELA, padx=16)
        frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            frame, text="Buscar por número de série:", font=FONTE_PADRAO,
            bg=COR_FUNDO_JANELA, fg=COR_TEXTO,
        ).pack(side="left")

        self.entrada_busca = ttk.Entry(frame, width=28, font=FONTE_PADRAO)
        self.entrada_busca.pack(side="left", padx=8)
        self.entrada_busca.bind("<Return>", lambda evento: self._pesquisar())

        ttk.Button(frame, text="Pesquisar", style="Primario.TButton", command=self._pesquisar).pack(
            side="left"
        )

    def _montar_lista(self):
        """Área com rolagem onde os andares (pastas) e os nobreaks aparecem."""
        container = tk.Frame(self, bg=COR_FUNDO_JANELA)
        container.pack(fill="both", expand=True, padx=16, pady=5)

        self.canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0, bg=COR_FUNDO_JANELA)
        barra_rolagem = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=barra_rolagem.set)

        barra_rolagem.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.frame_lista = tk.Frame(self.canvas, bg=COR_FUNDO_JANELA)
        self.janela_no_canvas = self.canvas.create_window((0, 0), window=self.frame_lista, anchor="nw")

        self.frame_lista.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind(
            "<Configure>", lambda e: self.canvas.itemconfig(self.janela_no_canvas, width=e.width)
        )
        # Rolagem com a rodinha do mouse
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))

    def _montar_botoes(self):
        frame = tk.Frame(self, bg=COR_FUNDO_JANELA, pady=14, padx=16)
        frame.pack(fill="x")

        ttk.Button(
            frame, text="Adicionar", style="Primario.TButton", command=self._abrir_form_adicionar
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            frame, text="Atualizar Status", style="Secundario.TButton", command=self._abrir_form_status
        ).pack(side="left", padx=8)
        ttk.Button(
            frame, text="Editar", style="Secundario.TButton", command=self._abrir_form_editar
        ).pack(side="left", padx=8)
        ttk.Button(
            frame, text="Transferir", style="Secundario.TButton", command=self._abrir_form_transferir
        ).pack(side="left", padx=8)
        ttk.Button(
            frame, text="Remover", style="Perigo.TButton", command=self._remover_selecionado
        ).pack(side="left", padx=8)
        ttk.Button(
            frame, text="Atualizar Lista", style="Secundario.TButton", command=self.atualizar_lista
        ).pack(side="right")

    # --- Construção da lista (pastas por andar + nobreaks dentro) ---

    def atualizar_lista(self):
        for widget in self.frame_lista.winfo_children():
            widget.destroy()
        self._widgets_nobreak = {}

        # Descobre quais nobreaks têm pendência, para desenhar o "!" dourado.
        self._conjunto_sem_serie = {
            nb.numero_serie for nb in self.gerenciador.buscar_sem_numero_serie_real()
        }
        self._mapa_par_duplicado = {}
        for grupo in self.gerenciador.buscar_possiveis_duplicados():
            for nb in grupo:
                outros = [outro for outro in grupo if outro.numero_serie != nb.numero_serie]
                if outros:
                    self._mapa_par_duplicado[nb.numero_serie] = outros[0]
        self._andares_com_pendencia = set()
        for nb in self.gerenciador.todos():
            if nb.numero_serie in self._conjunto_sem_serie or nb.numero_serie in self._mapa_par_duplicado:
                self._andares_com_pendencia.add(nb.local.andar)

        for andar in ANDARES_VALIDOS:
            self._criar_cabecalho_andar(andar)
            if self.andares_abertos[andar]:
                self._criar_nobreaks_do_andar(andar)

        contagem_total = self.gerenciador.contar_por_status()
        self.pilula_funcionando.config(text=f"Funcionando: {contagem_total.get(StatusNobreak.FUNCIONANDO, 0)}")
        self.pilula_defeito.config(text=f"Defeito: {contagem_total.get(StatusNobreak.DEFEITO, 0)}")
        self.pilula_manutencao.config(text=f"Manutenção: {contagem_total.get(StatusNobreak.MANUTENCAO, 0)}")

        # Recalcula a área de rolagem agora, na hora - sem esperar pelo evento
        # <Configure>, que às vezes atrasa e deixa um espaço vazio ao rolar.
        self.frame_lista.update_idletasks()
        area_conteudo = self.canvas.bbox("all")
        self.canvas.configure(scrollregion=area_conteudo)

        altura_conteudo = area_conteudo[3] if area_conteudo else 0
        altura_visivel = self.canvas.winfo_height()
        if altura_conteudo <= altura_visivel:
            # Todo o conteúdo já cabe na tela: garante que fique no topo, sem "sobra".
            self.canvas.yview_moveto(0)

        if self._rolar_ate_pendente:
            self.after(30, self._rolar_ate_widget, self._rolar_ate_pendente)
            self._rolar_ate_pendente = None

    def _criar_selo_alerta(self, parent: tk.Frame, cor_fundo: str, texto_dica: str, ao_clicar=None) -> tk.Canvas:
        """Desenha um '!' dourado (usado tanto na pasta do andar quanto na linha do
        nobreak). Mostra uma dica com o texto do erro ao passar o mouse, e executa
        ao_clicar() se for informado (usado para navegar até o nobreak duplicado)."""
        selo = tk.Canvas(
            parent, width=18, height=18, bg=cor_fundo, highlightthickness=0,
            cursor="hand2" if ao_clicar else "arrow",
        )
        selo.create_oval(1, 1, 17, 17, fill=COR_ALERTA_DOURADO, outline=COR_ALERTA_DOURADO)
        selo.create_text(9, 9, text="!", fill=COR_ALERTA_TEXTO, font=("Segoe UI", 10, "bold"))
        DicaFerramenta(selo, texto_dica)
        if ao_clicar:
            selo.bind("<Button-1>", lambda evento: ao_clicar())
        return selo

    def _navegar_para(self, numero_serie: str):
        """Abre a pasta do andar certo, seleciona e rola até o nobreak indicado."""
        nobreak = self.gerenciador.buscar(numero_serie)
        if not nobreak:
            return
        self.andares_abertos[nobreak.local.andar] = True
        self.numero_serie_selecionado = numero_serie
        self._rolar_ate_pendente = numero_serie
        self.atualizar_lista()

    def _criar_cabecalho_andar(self, andar: str):
        contagem = self.gerenciador.contar_por_andar(andar)
        qtd_funcionando = contagem.get(StatusNobreak.FUNCIONANDO, 0)
        qtd_defeito = contagem.get(StatusNobreak.DEFEITO, 0)
        qtd_manutencao = contagem.get(StatusNobreak.MANUTENCAO, 0)

        cabecalho = tk.Frame(self.frame_lista, bg=COR_FUNDO_CARTAO, cursor="hand2")
        cabecalho.pack(fill="x", pady=(0, 6))

        conteudo = tk.Frame(cabecalho, bg=COR_FUNDO_CARTAO, padx=14, pady=10)
        conteudo.pack(fill="x")

        seta = "▾" if self.andares_abertos[andar] else "▸"
        lbl_seta = tk.Label(
            conteudo, text=seta, bg=COR_FUNDO_CARTAO, font=("Segoe UI", 11, "bold"),
            fg=COR_TEXTO_SECUNDARIO, width=2,
        )
        lbl_seta.pack(side="left")

        if andar in self._andares_com_pendencia:
            selo_andar = self._criar_selo_alerta(
                conteudo, COR_FUNDO_CARTAO,
                "Este andar tem nobreak(s) com pendência (sem número de série ou duplicado)",
            )
            selo_andar.pack(side="left", padx=(4, 0))

        lbl_nome = tk.Label(
            conteudo, text=f"📁  {nome_andar(andar)}", bg=COR_FUNDO_CARTAO,
            font=FONTE_TITULO_CARTAO, fg=COR_TEXTO, anchor="w",
        )
        lbl_nome.pack(side="left", fill="x", expand=True, padx=(2, 0))

        frame_bolinhas = tk.Frame(conteudo, bg=COR_FUNDO_CARTAO)
        frame_bolinhas.pack(side="right")

        self._criar_bolinha_contagem(frame_bolinhas, COR_BOLINHA_FUNCIONANDO, qtd_funcionando)
        self._criar_bolinha_contagem(frame_bolinhas, COR_BOLINHA_DEFEITO, qtd_defeito)
        self._criar_bolinha_contagem(frame_bolinhas, COR_BOLINHA_MANUTENCAO, qtd_manutencao)

        # Linha fina embaixo do cartão, para separar do próximo
        tk.Frame(cabecalho, bg=COR_BORDA_SUAVE, height=1).pack(fill="x", side="bottom")

        # Clicar em qualquer parte do cabeçalho abre/fecha a pasta do andar
        for widget in (cabecalho, conteudo, lbl_seta, lbl_nome, frame_bolinhas):
            widget.bind("<Button-1>", lambda evento, a=andar: self._alternar_andar(a))

    def _criar_bolinha_contagem(self, parent: tk.Frame, cor: str, quantidade: int):
        grupo = tk.Frame(parent, bg=COR_FUNDO_CARTAO)
        grupo.pack(side="left", padx=8)

        bolinha = tk.Canvas(grupo, width=14, height=14, bg=COR_FUNDO_CARTAO, highlightthickness=0)
        bolinha.create_oval(2, 2, 13, 13, fill=cor, outline=cor)
        bolinha.pack(side="left")

        tk.Label(
            grupo, text=str(quantidade), bg=COR_FUNDO_CARTAO, font=FONTE_NEGRITO, fg=COR_TEXTO
        ).pack(side="left", padx=(4, 0))

    def _criar_nobreaks_do_andar(self, andar: str):
        nobreaks = self.gerenciador.listar_por_andar(andar)

        if not nobreaks:
            tk.Label(
                self.frame_lista,
                text="Nenhum nobreak cadastrado neste andar.",
                fg=COR_TEXTO_SECUNDARIO,
                bg=COR_FUNDO_JANELA,
                font=FONTE_PADRAO,
                anchor="w",
                padx=40,
                pady=4,
            ).pack(fill="x")
            return

        cores_status = {
            StatusNobreak.FUNCIONANDO: COR_FUNCIONANDO,
            StatusNobreak.DEFEITO: COR_DEFEITO,
            StatusNobreak.MANUTENCAO: COR_MANUTENCAO,
        }
        bolinhas_status = {
            StatusNobreak.FUNCIONANDO: COR_BOLINHA_FUNCIONANDO,
            StatusNobreak.DEFEITO: COR_BOLINHA_DEFEITO,
            StatusNobreak.MANUTENCAO: COR_BOLINHA_MANUTENCAO,
        }

        for nb in nobreaks:
            cor_fundo = cores_status[nb.status]
            selecionado = nb.numero_serie == self.numero_serie_selecionado

            linha = tk.Frame(
                self.frame_lista,
                bg=cor_fundo,
                cursor="hand2",
                highlightbackground=COR_DESTAQUE if selecionado else cor_fundo,
                highlightcolor=COR_DESTAQUE if selecionado else cor_fundo,
                highlightthickness=2 if selecionado else 0,
            )
            linha.pack(fill="x", padx=(34, 2), pady=3)
            self._widgets_nobreak[nb.numero_serie] = linha

            conteudo = tk.Frame(linha, bg=cor_fundo, padx=10, pady=8)
            conteudo.pack(fill="x")

            bolinha = tk.Canvas(conteudo, width=10, height=10, bg=cor_fundo, highlightthickness=0)
            bolinha.create_oval(1, 1, 9, 9, fill=bolinhas_status[nb.status], outline=bolinhas_status[nb.status])
            bolinha.pack(side="left", padx=(0, 8))

            lbl_serie = tk.Label(
                conteudo, text=nb.numero_serie, bg=cor_fundo, font=FONTE_NEGRITO, fg=COR_TEXTO
            )
            lbl_serie.pack(side="left")

            if nb.numero_serie in self._conjunto_sem_serie:
                selo_erro = self._criar_selo_alerta(conteudo, cor_fundo, "SEM NÚMERO DE SÉRIE")
                selo_erro.pack(side="left", padx=(6, 0))
            elif nb.numero_serie in self._mapa_par_duplicado:
                par = self._mapa_par_duplicado[nb.numero_serie]
                selo_erro = self._criar_selo_alerta(
                    conteudo, cor_fundo, "NÚMERO DE SÉRIE REPETIDO (clique para ver o outro)",
                    ao_clicar=lambda ns=par.numero_serie: self._navegar_para(ns),
                )
                selo_erro.pack(side="left", padx=(6, 0))

            detalhes = [nb.local.setor, nb.status.value.capitalize()]
            if nb.va:
                detalhes.append(nb.va)
            if nb.marca or nb.modelo:
                detalhes.append(" ".join(filter(None, [nb.marca, nb.modelo])))
            if nb.observacao:
                detalhes.append(nb.observacao)
            texto_detalhes = "   •   ".join(detalhes)

            lbl_detalhes = tk.Label(
                conteudo, text=texto_detalhes, bg=cor_fundo, font=FONTE_PADRAO, fg=COR_TEXTO_SECUNDARIO
            )
            lbl_detalhes.pack(side="left", padx=(10, 0))

            for widget in (linha, conteudo, bolinha, lbl_serie, lbl_detalhes):
                widget.bind("<Button-1>", lambda evento, ns=nb.numero_serie: self._selecionar_nobreak(ns))

    # --- Busca ---

    def _pesquisar(self):
        numero_serie = self.entrada_busca.get().strip()
        if not numero_serie:
            return

        nobreak = self.gerenciador.buscar(numero_serie)
        if not nobreak:
            messagebox.showinfo("Não encontrado", f"Nenhum nobreak com o número de série '{numero_serie}'.")
            return

        self._navegar_para(nobreak.numero_serie)

    def _rolar_ate_widget(self, numero_serie: str):
        widget = self._widgets_nobreak.get(numero_serie)
        if not widget:
            return
        self.canvas.update_idletasks()
        total = self.canvas.bbox("all")
        if not total or total[3] == 0:
            return
        fracao = max(0, (widget.winfo_y() - 40) / total[3])
        self.canvas.yview_moveto(fracao)

    # --- Ações da interface ---

    def _alternar_andar(self, andar: str):
        self.andares_abertos[andar] = not self.andares_abertos[andar]
        self.atualizar_lista()

    def _selecionar_nobreak(self, numero_serie: str):
        self.numero_serie_selecionado = numero_serie
        self.atualizar_lista()

    def _nobreak_selecionado(self):
        if not self.numero_serie_selecionado:
            messagebox.showwarning("Nenhuma seleção", "Clique em um nobreak na lista primeiro.")
            return None
        return self.numero_serie_selecionado

    def _remover_selecionado(self):
        numero_serie = self._nobreak_selecionado()
        if not numero_serie:
            return
        confirmar = messagebox.askyesno(
            "Confirmar remoção", f"Remover o nobreak {numero_serie}?"
        )
        if confirmar:
            self.gerenciador.remover(numero_serie)
            self.numero_serie_selecionado = None
            self.atualizar_lista()

    def _abrir_form_adicionar(self):
        FormAdicionar(self)

    def _abrir_form_status(self):
        numero_serie = self._nobreak_selecionado()
        if not numero_serie:
            return
        FormStatus(self, numero_serie)

    def _abrir_form_editar(self):
        numero_serie = self._nobreak_selecionado()
        if not numero_serie:
            return
        nobreak = self.gerenciador.buscar(numero_serie)
        if not nobreak:
            messagebox.showwarning("Não encontrado", "Esse nobreak não existe mais. Atualize a lista.")
            return
        FormEditar(self, nobreak)

    def _abrir_form_transferir(self):
        numero_serie = self._nobreak_selecionado()
        if not numero_serie:
            return
        FormTransferir(self, numero_serie)

    def _ao_fechar(self):
        self.gerenciador.fechar()
        self.destroy()


class JanelaPendencias(tk.Toplevel):
    """
    Janela que lista as pendências do cadastro (sem número de série / duplicados).
    Diferente de uma caixa de aviso comum, o texto aqui pode ser selecionado com o
    mouse e copiado (ex: para colar num Bloco de Notas ou mandar no WhatsApp),
    e tem rolagem, então nunca corta a lista com "...e mais X".
    """

    def __init__(self, app: "AppNobreaks", texto_completo: str):
        super().__init__(app)
        self.title("Pendências no cadastro")
        self.geometry("560x440")
        self.configure(bg=COR_FUNDO_CARTAO)
        self.transient(app)

        tk.Label(
            self,
            text="⚠️  Pendências encontradas no cadastro",
            font=("Segoe UI", 12, "bold"),
            bg=COR_FUNDO_CARTAO,
            fg=COR_TEXTO,
            anchor="w",
            padx=16,
            pady=12,
        ).pack(fill="x")

        area_texto = tk.Frame(self, bg=COR_FUNDO_CARTAO, padx=16)
        area_texto.pack(fill="both", expand=True)

        barra_rolagem = ttk.Scrollbar(area_texto, orient="vertical")
        self.caixa_texto = tk.Text(
            area_texto,
            wrap="word",
            font=FONTE_PADRAO,
            yscrollcommand=barra_rolagem.set,
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=10,
        )
        barra_rolagem.config(command=self.caixa_texto.yview)
        barra_rolagem.pack(side="right", fill="y")
        self.caixa_texto.pack(side="left", fill="both", expand=True, pady=(0, 10))

        self.caixa_texto.insert("1.0", texto_completo)
        # Deixa o texto selecionável/copiável, mas impede que a pessoa edite o conteúdo.
        self.caixa_texto.bind("<Key>", self._bloquear_digitacao)
        self.caixa_texto.bind("<Control-a>", self._selecionar_tudo)
        self.caixa_texto.focus_set()

        rodape = tk.Frame(self, bg=COR_FUNDO_CARTAO, padx=16, pady=12)
        rodape.pack(fill="x")

        ttk.Button(
            rodape, text="Copiar tudo", style="Secundario.TButton",
            command=lambda: self._copiar_tudo(texto_completo),
        ).pack(side="left")
        ttk.Button(rodape, text="Fechar", style="Primario.TButton", command=self.destroy).pack(side="right")

    def _bloquear_digitacao(self, evento):
        """Permite copiar (Ctrl+C), selecionar tudo (Ctrl+A) e navegar com as setas,
        mas bloqueia qualquer tecla que tentaria alterar o texto."""
        eh_atalho_permitido = (evento.state & 0x4) and evento.keysym.lower() in ("c", "a")
        eh_tecla_navegacao = evento.keysym in (
            "Up", "Down", "Left", "Right", "Prior", "Next", "Home", "End"
        )
        if eh_atalho_permitido or eh_tecla_navegacao:
            return None
        return "break"

    def _selecionar_tudo(self, evento):
        self.caixa_texto.tag_add("sel", "1.0", "end")
        return "break"

    def _copiar_tudo(self, texto: str):
        self.clipboard_clear()
        self.clipboard_append(texto)


class _FormBase(tk.Toplevel):
    """Janela auxiliar simples, centralizada sobre a janela principal."""

    def __init__(self, app: AppNobreaks, titulo: str):
        super().__init__(app)
        self.app = app
        self.title(titulo)
        self.configure(bg=COR_FUNDO_CARTAO)
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()


class FormAdicionar(_FormBase):
    def __init__(self, app: AppNobreaks):
        super().__init__(app, "Adicionar Nobreak")

        campos = tk.Frame(self, padx=18, pady=18, bg=COR_FUNDO_CARTAO)
        campos.pack()

        tk.Label(campos, text="Número de série:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.entrada_serie = ttk.Entry(campos, width=30, font=FONTE_PADRAO)
        self.entrada_serie.grid(row=0, column=1, pady=5)

        tk.Label(campos, text="Andar:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.combo_andar = ttk.Combobox(
            campos, values=[nome_andar(a) for a in ANDARES_VALIDOS], state="readonly", width=27, font=FONTE_PADRAO
        )
        self.combo_andar.current(0)
        self.combo_andar.grid(row=1, column=1, pady=5)

        tk.Label(campos, text="Setor:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.entrada_setor = criar_campo_maiusculas(campos, width=30)
        self.entrada_setor.grid(row=2, column=1, pady=5)

        tk.Label(campos, text="Status:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=3, column=0, sticky="w", pady=5
        )
        self.combo_status = ttk.Combobox(
            campos,
            values=[s.value.capitalize() for s in StatusNobreak],
            state="readonly",
            width=27,
            font=FONTE_PADRAO,
        )
        self.combo_status.current(0)
        self.combo_status.grid(row=3, column=1, pady=5)

        tk.Label(campos, text="Marca (opcional):", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=4, column=0, sticky="w", pady=5
        )
        self.entrada_marca = criar_campo_maiusculas(campos, width=30)
        self.entrada_marca.grid(row=4, column=1, pady=5)

        tk.Label(campos, text="Potência em VA (opcional):", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=5, column=0, sticky="w", pady=5
        )
        self.entrada_va = ttk.Entry(campos, width=30, font=FONTE_PADRAO)
        self.entrada_va.grid(row=5, column=1, pady=5)

        tk.Label(campos, text="Modelo (opcional):", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=6, column=0, sticky="w", pady=5
        )
        self.entrada_modelo = criar_campo_maiusculas(campos, width=30)
        self.entrada_modelo.grid(row=6, column=1, pady=5)

        tk.Label(campos, text="Observação (opcional):", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=7, column=0, sticky="w", pady=5
        )
        self.entrada_observacao = criar_campo_maiusculas(campos, width=30)
        self.entrada_observacao.grid(row=7, column=1, pady=5)

        ttk.Button(campos, text="Salvar", style="Primario.TButton", command=self._salvar).grid(
            row=8, column=0, columnspan=2, pady=(14, 0), sticky="ew"
        )

    def _salvar(self):
        numero_serie = self.entrada_serie.get().strip()
        setor = self.entrada_setor.get().strip()

        if not numero_serie or not setor:
            messagebox.showerror("Campos obrigatórios", "Preencha o número de série e o setor.")
            return

        ja_existente = self.app.gerenciador.buscar_ignorando_caixa(numero_serie)
        if ja_existente:
            messagebox.showerror(
                "Número de série já existe",
                f"Já existe um nobreak cadastrado com o número de série '{numero_serie}':\n\n"
                f"Localização atual: {nome_andar(ja_existente.local.andar)} / {ja_existente.local.setor}\n\n"
                "Se quiser corrigir os dados dele, use a opção 'Editar' em vez de 'Adicionar'.",
            )
            return

        andar = ANDARES_VALIDOS[self.combo_andar.current()]
        status = list(StatusNobreak)[self.combo_status.current()]
        marca = self.entrada_marca.get().strip()
        va = self.entrada_va.get().strip()
        modelo = self.entrada_modelo.get().strip()
        observacao = self.entrada_observacao.get().strip()

        self.app.gerenciador.adicionar(
            Nobreak(numero_serie, Local(andar, setor), status, modelo, observacao, va, marca)
        )
        self.app.atualizar_lista()
        self.destroy()


class FormStatus(_FormBase):
    def __init__(self, app: AppNobreaks, numero_serie: str):
        super().__init__(app, f"Atualizar Status - {numero_serie}")
        self.numero_serie = numero_serie

        campos = tk.Frame(self, padx=18, pady=18, bg=COR_FUNDO_CARTAO)
        campos.pack()

        tk.Label(
            campos, text=f"Novo status para {numero_serie}:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.combo_status = ttk.Combobox(
            campos,
            values=[s.value.capitalize() for s in StatusNobreak],
            state="readonly",
            width=27,
            font=FONTE_PADRAO,
        )
        self.combo_status.current(0)
        self.combo_status.grid(row=1, column=0, columnspan=2, pady=5)

        ttk.Button(campos, text="Salvar", style="Primario.TButton", command=self._salvar).grid(
            row=2, column=0, columnspan=2, pady=(14, 0), sticky="ew"
        )

    def _salvar(self):
        novo_status = list(StatusNobreak)[self.combo_status.current()]
        self.app.gerenciador.atualizar_status(self.numero_serie, novo_status)
        self.app.atualizar_lista()
        self.destroy()


class FormEditar(_FormBase):
    """Formulário para corrigir qualquer dado de um nobreak já cadastrado
    (inclusive o próprio número de série, se foi digitado errado)."""

    def __init__(self, app: AppNobreaks, nobreak: Nobreak):
        super().__init__(app, f"Editar - {nobreak.numero_serie}")
        self.numero_serie_original = nobreak.numero_serie

        campos = tk.Frame(self, padx=18, pady=18, bg=COR_FUNDO_CARTAO)
        campos.pack()

        tk.Label(campos, text="Número de série:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.entrada_serie = ttk.Entry(campos, width=30, font=FONTE_PADRAO)
        self.entrada_serie.insert(0, nobreak.numero_serie)
        self.entrada_serie.grid(row=0, column=1, pady=5)

        tk.Label(campos, text="Andar:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.combo_andar = ttk.Combobox(
            campos, values=[nome_andar(a) for a in ANDARES_VALIDOS], state="readonly", width=27, font=FONTE_PADRAO
        )
        self.combo_andar.current(ANDARES_VALIDOS.index(nobreak.local.andar))
        self.combo_andar.grid(row=1, column=1, pady=5)

        tk.Label(campos, text="Setor:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.entrada_setor = criar_campo_maiusculas(campos, width=30)
        self.entrada_setor.insert(0, nobreak.local.setor)
        self.entrada_setor.grid(row=2, column=1, pady=5)

        tk.Label(campos, text="Status:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=3, column=0, sticky="w", pady=5
        )
        self.combo_status = ttk.Combobox(
            campos,
            values=[s.value.capitalize() for s in StatusNobreak],
            state="readonly",
            width=27,
            font=FONTE_PADRAO,
        )
        self.combo_status.current(list(StatusNobreak).index(nobreak.status))
        self.combo_status.grid(row=3, column=1, pady=5)

        tk.Label(campos, text="Marca (opcional):", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=4, column=0, sticky="w", pady=5
        )
        self.entrada_marca = criar_campo_maiusculas(campos, width=30)
        self.entrada_marca.insert(0, nobreak.marca)
        self.entrada_marca.grid(row=4, column=1, pady=5)

        tk.Label(campos, text="Potência em VA (opcional):", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=5, column=0, sticky="w", pady=5
        )
        self.entrada_va = ttk.Entry(campos, width=30, font=FONTE_PADRAO)
        self.entrada_va.insert(0, nobreak.va)
        self.entrada_va.grid(row=5, column=1, pady=5)

        tk.Label(campos, text="Modelo (opcional):", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=6, column=0, sticky="w", pady=5
        )
        self.entrada_modelo = criar_campo_maiusculas(campos, width=30)
        self.entrada_modelo.insert(0, nobreak.modelo)
        self.entrada_modelo.grid(row=6, column=1, pady=5)

        tk.Label(campos, text="Observação (opcional):", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=7, column=0, sticky="w", pady=5
        )
        self.entrada_observacao = criar_campo_maiusculas(campos, width=30)
        self.entrada_observacao.insert(0, nobreak.observacao)
        self.entrada_observacao.grid(row=7, column=1, pady=5)

        ttk.Button(campos, text="Salvar correção", style="Primario.TButton", command=self._salvar).grid(
            row=8, column=0, columnspan=2, pady=(14, 0), sticky="ew"
        )

    def _salvar(self):
        novo_numero_serie = self.entrada_serie.get().strip()
        setor = self.entrada_setor.get().strip()

        if not novo_numero_serie or not setor:
            messagebox.showerror("Campos obrigatórios", "Preencha o número de série e o setor.")
            return

        andar = ANDARES_VALIDOS[self.combo_andar.current()]
        status = list(StatusNobreak)[self.combo_status.current()]
        marca = self.entrada_marca.get().strip()
        va = self.entrada_va.get().strip()
        modelo = self.entrada_modelo.get().strip()
        observacao = self.entrada_observacao.get().strip()

        nobreak_atualizado = Nobreak(novo_numero_serie, Local(andar, setor), status, modelo, observacao, va, marca)

        try:
            self.app.gerenciador.editar(self.numero_serie_original, nobreak_atualizado)
        except NumeroSerieJaExisteError as erro:
            messagebox.showerror("Número de série já existe", str(erro))
            return

        if novo_numero_serie != self.numero_serie_original:
            self.app.numero_serie_selecionado = novo_numero_serie
        self.app.atualizar_lista()
        self.destroy()


class FormTransferir(_FormBase):
    def __init__(self, app: AppNobreaks, numero_serie: str):
        super().__init__(app, f"Transferir - {numero_serie}")
        self.numero_serie = numero_serie

        campos = tk.Frame(self, padx=18, pady=18, bg=COR_FUNDO_CARTAO)
        campos.pack()

        tk.Label(
            campos, text=f"Novo local para {numero_serie}:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        tk.Label(campos, text="Andar:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.combo_andar = ttk.Combobox(
            campos, values=[nome_andar(a) for a in ANDARES_VALIDOS], state="readonly", width=27, font=FONTE_PADRAO
        )
        self.combo_andar.current(0)
        self.combo_andar.grid(row=1, column=1, pady=5)

        tk.Label(campos, text="Setor:", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.entrada_setor = criar_campo_maiusculas(campos, width=30)
        self.entrada_setor.grid(row=2, column=1, pady=5)

        tk.Label(campos, text="Observação (opcional):", bg=COR_FUNDO_CARTAO, font=FONTE_PADRAO).grid(
            row=3, column=0, sticky="w", pady=5
        )
        self.entrada_observacao = criar_campo_maiusculas(campos, width=30)
        self.entrada_observacao.grid(row=3, column=1, pady=5)

        ttk.Button(campos, text="Salvar", style="Primario.TButton", command=self._salvar).grid(
            row=4, column=0, columnspan=2, pady=(14, 0), sticky="ew"
        )

    def _salvar(self):
        setor = self.entrada_setor.get().strip()
        if not setor:
            messagebox.showerror("Campo obrigatório", "Preencha o novo setor.")
            return

        andar = ANDARES_VALIDOS[self.combo_andar.current()]
        observacao = self.entrada_observacao.get().strip()
        self.app.gerenciador.mover_local(self.numero_serie, Local(andar, setor), observacao or None)
        self.app.atualizar_lista()
        self.destroy()


if __name__ == "__main__":
    app = AppNobreaks()
    app.mainloop()
