# src/gui/main_window.py (VERSÃO FINAL - COM CHECKBOXES DE ESCOLARIDADE)

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter.scrolledtext import ScrolledText
import threading
import os
import sys
import webbrowser

sys.path.append(os.getcwd())
from data.data_loader import DataLoader
from main import run_automation_logic

class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="litera")
        self.title("Automação TEC - IA Inteligente")
        self.geometry("1200x900") # Aumentei um pouco a altura
        self.last_report_path = None
        
        try:
            loader = DataLoader(lambda x: None)
            self.lista_materias = sorted(loader.materias)
        except:
            self.lista_materias = []

        self.create_layout()

    def create_layout(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=7)
        self.grid_rowconfigure(0, weight=1)

        # Painel Esquerdo
        control_panel = ttk.Frame(self, padding=10)
        control_panel.grid(row=0, column=0, sticky="nsew")
        
        ttk.Label(control_panel, text="Configurações", font=("Helvetica", 16, "bold")).pack(pady=10)

        # Credenciais
        self.add_entry(control_panel, "Email TEC:", "tec_user")
        self.add_entry(control_panel, "Senha TEC:", "tec_pass", show="*")
        self.add_entry(control_panel, "User BackOffice:", "bo_user")
        self.add_entry(control_panel, "Senha BackOffice:", "bo_pass", show="*")
        
        # Curso e Matéria
        ttk.Label(control_panel, text="URL do Curso:", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(10,0))
        self.entry_url = ttk.Entry(control_panel)
        self.entry_url.pack(fill="x", pady=5)

        ttk.Label(control_panel, text="Forçar Matéria (Opcional):", font=("Helvetica", 10, "bold"), bootstyle="primary").pack(anchor="w", pady=(10,0))
        self.combo_materia = ttk.Combobox(control_panel, values=["Automático (IA)"] + self.lista_materias, state="readonly")
        self.combo_materia.set("Automático (IA)")
        self.combo_materia.pack(fill="x", pady=5)

        # Filtros de Texto
        self.add_entry(control_panel, "Banca (ex: VUNESP):", "banca")
        self.add_entry(control_panel, "Ano (ex: 2023, 2024):", "ano")

        # --- NOVO: SELEÇÃO MÚLTIPLA DE ESCOLARIDADE ---
        ttk.Label(control_panel, text="Escolaridade:", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(10,0))
        
        self.frame_escolaridade = ttk.Frame(control_panel)
        self.frame_escolaridade.pack(fill="x", pady=5)
        
        # Checkboxes para as opções mais comuns
        self.vars_escolaridade = {
            "Superior": ttk.BooleanVar(value=False),
            "Médio": ttk.BooleanVar(value=False), # Mapeia para 'Ensino Médio' no robô
            "Fundamental": ttk.BooleanVar(value=False)
        }
        
        for nivel, var in self.vars_escolaridade.items():
            cb = ttk.Checkbutton(self.frame_escolaridade, text=nivel, variable=var, bootstyle="round-toggle")
            cb.pack(side="left", padx=5)
        # ----------------------------------------------

        # Botões
        self.btn_start = ttk.Button(control_panel, text="INICIAR AUTOMAÇÃO", bootstyle="success", command=self.start_thread)
        self.btn_start.pack(pady=20, fill="x")

        self.btn_report = ttk.Button(control_panel, text="Abrir Relatório", bootstyle="secondary", state="disabled", command=self.open_report)
        self.btn_report.pack(pady=5, fill="x")

        # Painel Direito
        log_panel = ttk.Frame(self, padding=10)
        log_panel.grid(row=0, column=1, sticky="nsew")
        ttk.Label(log_panel, text="Logs do Processo", font=("Helvetica", 12, "bold")).pack(anchor="w")
        self.log_area = ScrolledText(log_panel, state="disabled", height=40)
        self.log_area.pack(fill="both", expand=True)

    def add_entry(self, parent, label, attr_name, show=None):
        ttk.Label(parent, text=label).pack(anchor="w")
        entry = ttk.Entry(parent, show=show)
        entry.pack(fill="x", pady=(0, 5))
        setattr(self, f"entry_{attr_name}", entry)

    def log(self, msg):
        self.after(0, lambda: self._log_impl(msg))

    def _log_impl(self, msg):
        self.log_area.config(state="normal")
        self.log_area.insert("end", msg + "\n")
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def start_thread(self):
        materia = self.combo_materia.get()
        if materia == "Automático (IA)": materia = None

        # Coleta Escolaridades Selecionadas
        escolaridades_selecionadas = []
        for nivel, var in self.vars_escolaridade.items():
            if var.get():
                # Converte para o texto esperado pelo robô/site
                if nivel == "Médio": escolaridades_selecionadas.append("Ensino Médio")
                elif nivel == "Fundamental": escolaridades_selecionadas.append("Ensino Fundamental")
                else: escolaridades_selecionadas.append(nivel)
        
        # Se nenhuma foi marcada, manda vazio (sem filtro)
        str_escolaridade = ",".join(escolaridades_selecionadas)

        config = {
            "tec_user": self.entry_tec_user.get(),
            "tec_pass": self.entry_tec_pass.get(),
            "bo_user": self.entry_bo_user.get(),
            "bo_pass": self.entry_bo_pass.get(),
            "course_url": self.entry_url.get(),
            "banca": self.entry_banca.get(),
            "ano": self.entry_ano.get(),
            "escolaridade": str_escolaridade, # Passa como string separada por vírgula para o Orchestrator processar
            "materia_selecionada": materia
        }
        
        self.btn_start.config(state="disabled")
        self.btn_report.config(state="disabled", bootstyle="secondary")
        
        t = threading.Thread(target=self.run_logic_wrapper, args=(config,))
        t.daemon = True
        t.start()

    def run_logic_wrapper(self, config):
        try:
            report_path = run_automation_logic(config, self.log)
            if report_path and os.path.exists(report_path):
                self.last_report_path = report_path
                self.after(0, lambda: self.btn_report.config(state="normal", bootstyle="info"))
                self.log(f"✅ Relatório pronto: {report_path}")
        except Exception as e:
            self.log(f"ERRO: {e}")
        finally:
            self.after(0, lambda: self.btn_start.config(state="normal"))

    def open_report(self):
        if self.last_report_path:
            webbrowser.open(self.last_report_path)