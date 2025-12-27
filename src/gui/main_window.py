# src/gui/main_window.py
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.scrolled import ScrolledFrame
from tkinter.scrolledtext import ScrolledText
from tkinter import StringVar, VERTICAL, HORIZONTAL
import threading
import os
import sys
import webbrowser
import json
import traceback
import requests
import re

sys.path.append(os.getcwd())
from data.data_loader import DataLoader
from src.gui.review_window import ReviewWindow
from src.automation.orchestrator import Orchestrator

CONFIG_FILE = "user_settings.json"

# Lista de Áreas (Carreiras) conforme site do TEC
LISTA_AREAS_TEC = [
    "", # Opção vazia (sem filtro de área)
    "Agências Reguladoras",
    "Bancária e Financeira",
    "Conselhos de Fiscalização",
    "Diplomacia e Comércio Exterior",
    "Todo o conteúdo de 'Educação'",
    "Professores",
    "Servidores Administrativos de Educação",
    "ENEM e Vestibular",
    "EP e SEM",
    "Estágio",
    "Todo o conteúdo de 'Exames de Proficiência e Certificações'",
    "OAB",
    "CFC e Certificações Contábeis",
    "Demais Exames de Proficiência e Certificações",
    "Executivo (geral)",
    "Fiscal",
    "Todo o conteúdo de 'Forças Armadas'",
    "Oficiais",
    "Praças",
    "Todo o conteúdo de 'Gestão e Controle'",
    "Controladorias",
    "Tribunais de Contas",
    "Gestão Governamental",
    "Todo o conteúdo de 'Judiciária (Servidores)'",
    "Servidores da Justiça Federal (TRFs, STF e STJ)",
    "Servidores da Justiça Trabalhista (TRTs e TST)",
    "Servidores da Justiça Eleitoral (TREs e TSE)",
    "Servidores da Justiça Estadual (TJs)",
    "Servidores da Justiça Militar (TJMs e STM)",
    "Servidores de MPs",
    "Servidores de Defensorias",
    "Servidores de Procuradorias (AGU, PGEs e PGMs)",
    "Conselhos (CNMP e CNJ)",
    "Todo o conteúdo de 'Jurídica (Autoridades)'",
    "Magistratura",
    "Promotoria",
    "Defensoria",
    "Procuradoria",
    "Cartório",
    "Legislativo",
    "Todo o conteúdo de 'Policial'",
    "Delegados",
    "Peritos, Papiloscopistas e Auxiliares",
    "Agentes, Escrivães e Investigadores",
    "Guardas Civis",
    "Penitenciária",
    "Suporte Administrativo Policial",
    "Previdenciária",
    "Todo o conteúdo de 'Saúde'",
    "Servidores da Saúde",
    "Residência em Saúde"
]

class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="litera")
        self.title("Automação TEC - IA Inteligente + Integração Sheets")
        self.geometry("1200x800") # Tamanho inicial
        
        # Variáveis de Estado
        self.last_report_path = None
        self.last_results_data = None
        self.materia_selecionada = [] # Armazena a LISTA de matérias selecionadas
        
        # Inicialização do Loader
        try:
            self.loader = DataLoader(lambda x: None)
            self.lista_materias = sorted(self.loader.materias)
        except:
            self.loader = None
            self.lista_materias = []

        # --- CONFIGURAÇÃO DE SCROLL ---
        self._setup_scroll_system()

        # Layout e Configurações
        self.create_layout()
        self.load_settings()

    def _setup_scroll_system(self):
        """
        Configura o sistema de Canvas + Scrollbars (Vertical e Horizontal).
        """
        # 1. Container principal
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill=BOTH, expand=True)

        # Configura o Grid do container principal para acomodar as barras
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # 2. Canvas
        self.canvas = ttk.Canvas(self.main_container)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # 3. Scrollbar Vertical
        self.scrollbar_y = ttk.Scrollbar(self.main_container, orient=VERTICAL, command=self.canvas.yview)
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")

        # 4. Scrollbar Horizontal (NOVA)
        self.scrollbar_x = ttk.Scrollbar(self.main_container, orient=HORIZONTAL, command=self.canvas.xview)
        self.scrollbar_x.grid(row=1, column=0, sticky="ew")

        # Conecta o Canvas às Scrollbars
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        
        # 5. Bindings para MouseWheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel) # Windows
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)   # Linux Up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)   # Linux Down
        # Shift + Scroll para rolagem horizontal (opcional, mas útil)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

        # 6. O Frame interno que conterá todos os widgets
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Cria a janela dentro do canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Evento para atualizar a região de scroll quando o conteúdo muda
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        # Evento para redimensionar o frame interno (lógica inteligente para horizontal)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_frame_configure(self, event):
        """Atualiza a região de rolagem para englobar todo o conteúdo"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """
        Ajusta a largura do frame interno.
        Se a janela for maior que o conteúdo mínimo, expande o frame para preencher (fica bonito).
        Se a janela for menor, mantém o tamanho mínimo do frame (ativa a barra horizontal).
        """
        min_width = self.scrollable_frame.winfo_reqwidth()
        
        if event.width >= min_width:
            # Janela larga: expande o frame para ocupar a largura total
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        else:
            # Janela estreita: fixa no tamanho mínimo do conteúdo (permite scroll horizontal)
            self.canvas.itemconfig(self.canvas_window, width=min_width)

    def _on_mousewheel(self, event):
        """Trata o scroll vertical do mouse"""
        if self.canvas.winfo_exists():
            # Verifica se há barra de rolagem vertical ativa (scrollregion > height)
            bbox = self.canvas.bbox("all")
            if bbox and bbox[3] > self.canvas.winfo_height():
                if event.num == 5 or event.delta == -120:
                    self.canvas.yview_scroll(1, "units")
                elif event.num == 4 or event.delta == 120:
                    self.canvas.yview_scroll(-1, "units")

    def _on_shift_mousewheel(self, event):
        """Trata o scroll horizontal (Shift + MouseWheel)"""
        if self.canvas.winfo_exists():
            if event.num == 5 or event.delta == -120:
                self.canvas.xview_scroll(1, "units")
            elif event.num == 4 or event.delta == 120:
                self.canvas.xview_scroll(-1, "units")

    def create_layout(self):
        """
        Cria o layout dentro do self.scrollable_frame.
        """
        # Configuração do Grid no Frame Rolável
        self.scrollable_frame.grid_columnconfigure(0, weight=3)
        self.scrollable_frame.grid_columnconfigure(1, weight=7)
        self.scrollable_frame.grid_rowconfigure(0, weight=1)

        # === PAINEL ESQUERDO: CONTROLES ===
        control_panel = ttk.Frame(self.scrollable_frame, padding=10)
        control_panel.grid(row=0, column=0, sticky="nsew")
        
        # Título
        ttk.Label(control_panel, text="Painel de Controle", font=("Helvetica", 16, "bold"), bootstyle="primary").pack(pady=(0, 10))

        # --- 1. SEÇÃO: CREDENCIAIS ---
        lbl_creds = ttk.Labelframe(control_panel, text="🔐 Credenciais de Acesso", padding=10, bootstyle="info")
        lbl_creds.pack(fill=X, pady=5)

        self.add_entry(lbl_creds, "Email TEC:", "tec_user")
        self.add_entry(lbl_creds, "Senha TEC:", "tec_pass", show="*")
        self.add_entry(lbl_creds, "User BackOffice:", "bo_user")
        self.add_entry(lbl_creds, "Senha BackOffice:", "bo_pass", show="*")
        
        # --- 2. SEÇÃO: INTEGRAÇÕES ---
        lbl_integ = ttk.Labelframe(control_panel, text="🔗 Integrações", padding=10, bootstyle="warning")
        lbl_integ.pack(fill=X, pady=5)
        
        ttk.Label(lbl_integ, text="Webhook Google Sheets:", font=("Helvetica", 9, "bold")).pack(anchor="w")
        self.entry_webapp_url = ttk.Entry(lbl_integ)
        self.entry_webapp_url.pack(fill=X, pady=5)
        
        # --- 3. SEÇÃO: CONFIGURAÇÃO DO CADERNO ---
        lbl_config = ttk.Labelframe(control_panel, text="⚙️ Definições do Caderno", padding=10, bootstyle="success")
        lbl_config.pack(fill=X, pady=5)

        ttk.Label(lbl_config, text="URL do Curso (BackOffice):", font=("Helvetica", 9)).pack(anchor="w")
        self.entry_url = ttk.Entry(lbl_config)
        self.entry_url.pack(fill=X, pady=5)

        # --- CAMPO MATÉRIA (MULTISSELEÇÃO) ---
        ttk.Label(lbl_config, text="Matéria(s) (Obrigatório):", font=("Helvetica", 9, "bold"), bootstyle="inverse-success").pack(anchor="w", pady=(5,0))
        
        self.materia_display_var = StringVar()
        # Entry apenas leitura para mostrar o que foi selecionado
        self.entry_materia_display = ttk.Entry(lbl_config, textvariable=self.materia_display_var, state="readonly")
        self.entry_materia_display.pack(fill=X, pady=(0, 2))
        
        # Botão para abrir o seletor
        ttk.Button(lbl_config, text="Selecionar Matérias...", bootstyle="outline-success", command=self.open_materia_multiselect).pack(fill=X, pady=(0, 5))

        # Filtro: Área
        ttk.Label(lbl_config, text="Área / Carreira:", font=("Helvetica", 9)).pack(anchor="w", pady=(5,0))
        self.combo_area = ttk.Combobox(lbl_config, values=LISTA_AREAS_TEC, state="readonly")
        self.combo_area.pack(fill=X, pady=5)

        self.add_entry(lbl_config, "Banca (ex: VUNESP):", "banca")
        self.add_entry(lbl_config, "Ano (ex: 2023, 2024):", "ano")

        # Escolaridade
        ttk.Label(lbl_config, text="Escolaridade:", font=("Helvetica", 9)).pack(anchor="w", pady=(5,0))
        self.frame_escolaridade = ttk.Frame(lbl_config)
        self.frame_escolaridade.pack(fill=X, pady=5)
        self.vars_escolaridade = {
            "Superior": ttk.BooleanVar(value=False),
            "Médio": ttk.BooleanVar(value=False),
            "Fundamental": ttk.BooleanVar(value=False)
        }
        for nivel, var in self.vars_escolaridade.items():
            ttk.Checkbutton(self.frame_escolaridade, text=nivel, variable=var, bootstyle="round-toggle").pack(side=LEFT, padx=5)

        # --- 4. ÁREA DE AÇÃO ---
        frame_actions = ttk.Frame(control_panel, padding=(0, 10))
        frame_actions.pack(fill=X, pady=10)

        self.btn_review = ttk.Button(frame_actions, text="🔍 1. Revisar Matches (IA)", bootstyle="info", command=self.start_review)
        self.btn_review.pack(fill=X, pady=5)

        self.btn_start = ttk.Button(frame_actions, text="▶ 2. INICIAR AUTOMAÇÃO", bootstyle="success", command=self.start_thread)
        self.btn_start.pack(fill=X, pady=5)

        # Botões de Saída
        frame_saida = ttk.Frame(control_panel)
        frame_saida.pack(fill=X, pady=5)
        
        self.btn_report = ttk.Button(frame_saida, text="📄 Abrir Relatório", bootstyle="secondary", state="disabled", command=self.open_report)
        self.btn_report.pack(side=LEFT, fill=X, expand=True, padx=(0, 2))

        self.btn_send_sheet = ttk.Button(frame_saida, text="📤 Enviar p/ Planilha", bootstyle="warning", state="disabled", command=self.send_to_sheet_thread)
        self.btn_send_sheet.pack(side=RIGHT, fill=X, expand=True, padx=(2, 0))

        # === PAINEL DIREITO: LOGS ===
        log_panel = ttk.Frame(self.scrollable_frame, padding=10)
        log_panel.grid(row=0, column=1, sticky="nsew")
        
        # Cabeçalho dos Logs
        header_log = ttk.Frame(log_panel)
        header_log.pack(fill=X, pady=(0, 5))
        
        ttk.Label(header_log, text="Logs do Processo", font=("Helvetica", 12, "bold")).pack(side=LEFT)
        ttk.Button(header_log, text="🗑️ Limpar Logs", bootstyle="outline-secondary", command=self.clear_logs).pack(side=RIGHT)
        
        # Área de texto com scroll próprio
        self.log_area = ScrolledText(log_panel, state="disabled", height=40)
        self.log_area.pack(fill=BOTH, expand=True)

    def open_materia_multiselect(self):
        """
        Abre janela modal para seleção múltipla com filtro e checkbox.
        """
        todas_materias = self.lista_materias
        
        # Janela Popup
        # CORREÇÃO: Passar 'master' como argumento nomeado, não posicional.
        top = ttk.Toplevel(title="Selecionar Matérias", master=self)
        top.geometry("600x600")
        
        # --- CABEÇALHO E FILTRO ---
        header_frame = ttk.Frame(top, padding=10, bootstyle="light")
        header_frame.pack(fill=X)
        
        ttk.Label(header_frame, text="Digite para filtrar:", font=("Arial", 10, "bold")).pack(anchor=W)
        
        search_var = StringVar()
        search_entry = ttk.Entry(header_frame, textvariable=search_var)
        search_entry.pack(fill=X, pady=(5, 0))
        search_entry.focus_set()

        # --- ÁREA DE ROLAGEM (Checkboxes) ---
        list_container = ttk.Frame(top, padding=10)
        list_container.pack(fill=BOTH, expand=True)

        sf = ScrolledFrame(list_container, autohide=True)
        sf.pack(fill=BOTH, expand=True)

        # Variáveis de controle
        check_vars = {}     # { "Nome da Matéria": IntVar }
        check_widgets = []  # Lista de widgets checkbox criados

        # Recupera seleção atual
        current_selection = self.materia_selecionada if isinstance(self.materia_selecionada, list) else []

        def populate_list(filter_text=""):
            # 1. Limpa a visualização anterior
            for widget in check_widgets:
                widget.destroy()
            check_widgets.clear()
            
            filter_text = filter_text.lower()
            
            # 2. Cria os checkboxes filtrados
            for mat in todas_materias:
                if filter_text in mat.lower():
                    if mat not in check_vars:
                        is_selected = 1 if mat in current_selection else 0
                        check_vars[mat] = ttk.IntVar(value=is_selected)
                    
                    chk = ttk.Checkbutton(
                        sf, 
                        text=mat, 
                        variable=check_vars[mat],
                        bootstyle="primary-round-toggle"
                    )
                    chk.pack(anchor=W, pady=2, padx=5)
                    check_widgets.append(chk)

        search_var.trace("w", lambda *args: populate_list(search_var.get()))
        populate_list()

        # --- RODAPÉ ---
        footer_frame = ttk.Frame(top, padding=15, bootstyle="light")
        footer_frame.pack(fill=X, side=BOTTOM)

        def confirm_selection():
            # Coleta tudo que está marcado
            selected_items = [m for m, var in check_vars.items() if var.get() == 1]
            
            self.materia_selecionada = selected_items
            
            # Atualiza visual
            if not selected_items:
                self.materia_display_var.set("")
            else:
                self.materia_display_var.set(", ".join(selected_items))
            
            self.save_settings()
            top.destroy()

        ttk.Button(footer_frame, text="Confirmar Seleção", command=confirm_selection, bootstyle="success", width=20).pack(side=RIGHT)
        ttk.Button(footer_frame, text="Cancelar", command=top.destroy, bootstyle="secondary-outline").pack(side=RIGHT, padx=10)

    def clear_logs(self):
        """Limpa a área de logs"""
        self.log_area.config(state="normal")
        self.log_area.delete("1.0", "end")
        self.log_area.config(state="disabled")

    def start_review(self):
        if not self.entry_url.get().strip():
            Messagebox.show_error("URL Obrigatória", "Erro")
            return
        
        self.save_settings()
        
        # Validação de Matéria (Lista)
        if not self.materia_selecionada:
            Messagebox.show_error("Selecione pelo menos uma matéria.", "Erro")
            return

        config = self._get_config_dict()
        self.btn_review.config(state="disabled")
        
        # Display visual amigável (truncado se for muito longo)
        display_mat = ", ".join(self.materia_selecionada)
        if len(display_mat) > 50: display_mat = display_mat[:47] + "..."
            
        self.log(f"🔍 Revisando para: {display_mat}...")
        
        def review_worker():
            try:
                orc = Orchestrator(config, self.log, headless=False)
                data = orc.fetch_and_preview_matches()
                # Passa a lista completa para o método de abertura de janela
                self.after(0, lambda: self._open_review_window(data, orc.cache_manager, orc.data_loader, self.materia_selecionada))
            except Exception as e:
                self.log(f"Erro na revisão: {e}")
                self.log(traceback.format_exc())
            finally:
                self.after(0, lambda: self.btn_review.config(state="normal"))

        threading.Thread(target=review_worker, daemon=True).start()

    def _open_review_window(self, data, cache_mgr, data_loader, materia_selecionada_list):
        if not data:
            self.log("⚠️ Nenhuma aula encontrada ou cache vazio.")
            return
        
        # Lógica para coletar filtros de TODAS as matérias selecionadas
        filtros_focados = []
        if isinstance(materia_selecionada_list, list):
            for m in materia_selecionada_list:
                filtros_focados.extend(data_loader.assuntos_por_materia.get(m, []))
        else:
            # Fallback string única
            filtros_focados = data_loader.assuntos_por_materia.get(materia_selecionada_list, [])
            
        # Filtros focados + Todos os filtros (fallback)
        todos_filtros = data_loader.lista_completa_fallback + filtros_focados
        
        # Remove duplicatas
        todos_filtros = sorted(list(set(todos_filtros)))
        filtros_focados = sorted(list(set(filtros_focados)))

        def on_save_review(reviewed_data):
            count = 0
            for aula, filtros in reviewed_data.items():
                cache_mgr.set(aula, filtros)
                count += 1
            cache_mgr.save_cache()
            self.log(f"✅ {count} aulas salvas no cache!")
            Messagebox.show_info("Revisão Salva! Clique em 'INICIAR AUTOMAÇÃO' para gerar os cadernos.", "Sucesso")

        ReviewWindow(self, data, todos_filtros, filtros_focados, on_save_review)

    def add_entry(self, parent, label, attr_name, show=None):
        ttk.Label(parent, text=label, font=("Helvetica", 9)).pack(anchor="w")
        entry = ttk.Entry(parent, show=show)
        entry.pack(fill=X, pady=(0, 5))
        setattr(self, f"entry_{attr_name}", entry)

    def log(self, msg):
        self.after(0, lambda: self._log_impl(msg))

    def _log_impl(self, msg):
        self.log_area.config(state="normal")
        self.log_area.insert("end", msg + "\n")
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def save_settings(self):
        settings = self._get_config_dict()
        esc_save = {k: v.get() for k,v in self.vars_escolaridade.items()}
        settings["escolaridade"] = esc_save 
        # Remove campos processados para não duplicar no JSON
        if "escolaridades" in settings: del settings["escolaridades"]
        
        # Salva a lista de matérias
        settings["materia_selecionada"] = self.materia_selecionada
        
        settings["webapp_url"] = self.entry_webapp_url.get()
        settings["area_carreira"] = self.combo_area.get()
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e: self.log(f"Erro config: {e}")

    def load_settings(self):
        if not os.path.exists(CONFIG_FILE): return
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: settings = json.load(f)
            def safe_fill(entry, key):
                if key in settings and settings[key]:
                    entry.delete(0, 'end')
                    entry.insert(0, settings[key])
            safe_fill(self.entry_tec_user, "tec_user")
            safe_fill(self.entry_tec_pass, "tec_pass")
            safe_fill(self.entry_bo_user, "bo_user")
            safe_fill(self.entry_bo_pass, "bo_pass")
            safe_fill(self.entry_webapp_url, "webapp_url")
            
            if "course_url" in settings: safe_fill(self.entry_url, "course_url")
            else: safe_fill(self.entry_url, "url")
            safe_fill(self.entry_banca, "banca")
            safe_fill(self.entry_ano, "ano")
            
            # Carrega Matéria (Lista ou String Legada)
            if "materia_selecionada" in settings:
                val = settings["materia_selecionada"]
                if isinstance(val, list):
                    self.materia_selecionada = val
                    self.materia_display_var.set(", ".join(val))
                else:
                    # Legado (string)
                    self.materia_selecionada = [val] if val else []
                    self.materia_display_var.set(val)
            elif "materia" in settings: # Legado antigo
                val = settings["materia"]
                self.materia_selecionada = [val] if val else []
                self.materia_display_var.set(val)

            if "escolaridade" in settings:
                for key, val in settings["escolaridade"].items():
                    if key in self.vars_escolaridade: self.vars_escolaridade[key].set(val)
            if "area_carreira" in settings and settings["area_carreira"] in LISTA_AREAS_TEC:
                self.combo_area.set(settings["area_carreira"])
                
        except: pass

    def _get_config_dict(self):
        escolaridades_selecionadas = []
        for nivel, var in self.vars_escolaridade.items():
            if var.get():
                if nivel == "Médio": escolaridades_selecionadas.append("Ensino Médio")
                elif nivel == "Fundamental": escolaridades_selecionadas.append("Ensino Fundamental")
                else: escolaridades_selecionadas.append(nivel)
        
        return {
            "tec_user": self.entry_tec_user.get(),
            "tec_pass": self.entry_tec_pass.get(),
            "bo_user": self.entry_bo_user.get(),
            "bo_pass": self.entry_bo_pass.get(),
            "webapp_url": self.entry_webapp_url.get(),
            "course_url": self.entry_url.get(),
            "banca": self.entry_banca.get(),
            "ano": self.entry_ano.get(),
            "escolaridade": ",".join(escolaridades_selecionadas),
            "escolaridades": escolaridades_selecionadas,
            "materia_selecionada": self.materia_selecionada, # Retorna a LISTA
            "area_carreira": self.combo_area.get()
        }

    def start_thread(self):
        if not self.entry_url.get().strip():
            Messagebox.show_error("URL Obrigatória", "Erro")
            return
        self.save_settings()
        if not self.materia_selecionada:
            Messagebox.show_error("Selecione Matéria", "Erro")
            return
        
        config = self._get_config_dict()
        self.btn_start.config(state="disabled")
        self.btn_review.config(state="disabled")
        self.btn_send_sheet.config(state="disabled")
        
        t = threading.Thread(target=self.run_tec_worker, args=(config,))
        t.daemon = True
        t.start()

    def run_tec_worker(self, config):
        try:
            self.log("="*40)
            self.log("🚀 FASE 2: INICIANDO GERAÇÃO NO TEC")
            self.log("="*40)
            
            orc = Orchestrator(config, self.log, headless=False)
            
            result = orc.run_tec_automation()
            if isinstance(result, tuple):
                report_path, final_data = result
            else:
                report_path = result
                final_data = []

            if report_path and os.path.exists(report_path):
                self.last_report_path = report_path
                self.last_results_data = final_data
                
                self.after(0, lambda: self.btn_report.config(state="normal", bootstyle="info"))
                
                if config.get('webapp_url') and final_data:
                    self.after(0, lambda: self.btn_send_sheet.config(state="normal"))
                    
                self.log(f"✅ Processo Finalizado! Relatório: {report_path}")
            else:
                self.log("⏹ Processo finalizado (sem relatório gerado ou erro).")

        except Exception as e:
            self.log(f"❌ ERRO CRÍTICO NA GUI: {e}")
            self.log(traceback.format_exc())
        finally:
            self.after(0, lambda: self.btn_start.config(state="normal"))
            self.after(0, lambda: self.btn_review.config(state="normal"))

    def open_report(self):
        if self.last_report_path: webbrowser.open(self.last_report_path)

    def send_to_sheet_thread(self):
        threading.Thread(target=self._send_to_sheet_logic, daemon=True).start()

    def _send_to_sheet_logic(self):
        url = self.entry_webapp_url.get().strip()
        if not url:
            self.log("⚠️ URL do Webhook não configurada!")
            return

        if not self.last_results_data:
            self.log("⚠️ Nenhum dado de automação disponível para enviar.")
            return

        self.log(f"\n📤 Enviando dados para a Planilha...")
        self.after(0, lambda: self.btn_send_sheet.config(state="disabled"))

        try:
            config = self._get_config_dict()
            assuntos_formatados = []
            
            for i, item in enumerate(self.last_results_data):
                aula_sequencial = f"Aula {i:02d}"
                assuntos_formatados.append({
                    "aula": aula_sequencial,
                    "assunto": item.get('filtros_ia', 'Geral'),
                    "questoes": item.get('num_questoes', 0),
                    "caderno": item.get('url', '')
                })

            # Formata a matéria para envio (se for lista, junta com vírgula)
            nome_disc = config['materia_selecionada']
            if isinstance(nome_disc, list): nome_disc = ", ".join(nome_disc)

            payload = {
                "nomeDisciplina": nome_disc,
                "banca": config['banca'],
                "escolaridade": config['escolaridade'],
                "anos": config['ano'],
                "assuntos": assuntos_formatados
            }

            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get("status") == "success":
                    self.log(f"✅ SUCESSO! Disciplina '{resp_json.get('disciplina')}' criada na planilha.")
                    self.after(0, lambda: Messagebox.show_info(f"Dados enviados com sucesso!\nDisciplina: {resp_json.get('disciplina')}", "Sucesso"))
                else:
                    self.log(f"⚠️ Erro retornado pela planilha: {resp_json.get('message')}")
                    self.after(0, lambda: Messagebox.show_error(f"Erro na Planilha: {resp_json.get('message')}", "Erro Remoto"))
            else:
                self.log(f"❌ Erro HTTP {response.status_code}: {response.text}")
                self.after(0, lambda: Messagebox.show_error(f"Erro HTTP {response.status_code}", "Erro de Conexão"))

        except Exception as e:
            self.log(f"❌ Erro ao enviar para planilha: {e}")
            self.log(traceback.format_exc())
            self.after(0, lambda: Messagebox.show_error(f"Erro ao enviar: {e}", "Erro Local"))
        finally:
            self.after(0, lambda: self.btn_send_sheet.config(state="normal"))

if __name__ == "__main__":
    app = App()
    app.mainloop()