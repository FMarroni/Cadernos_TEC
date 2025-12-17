# src/gui/main_window.py
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from tkinter.scrolledtext import ScrolledText
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
        self.geometry("1200x980") # Altura ajustada para novo campo
        self.last_report_path = None
        self.last_results_data = None
        
        try:
            self.loader = DataLoader(lambda x: None)
            self.lista_materias = sorted(self.loader.materias)
        except:
            self.loader = None
            self.lista_materias = []

        self.create_layout()
        self.load_settings()

    def create_layout(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=7)
        self.grid_rowconfigure(0, weight=1)

        # Painel Esquerdo
        control_panel = ttk.Frame(self, padding=10)
        control_panel.grid(row=0, column=0, sticky="nsew")
        
        ttk.Label(control_panel, text="Configurações", font=("Helvetica", 16, "bold")).pack(pady=10)

        # Inputs Básicos
        self.add_entry(control_panel, "Email TEC:", "tec_user")
        self.add_entry(control_panel, "Senha TEC:", "tec_pass", show="*")
        self.add_entry(control_panel, "User BackOffice:", "bo_user")
        self.add_entry(control_panel, "Senha BackOffice:", "bo_pass", show="*")
        
        # Webhook
        ttk.Label(control_panel, text="Webhook Google Sheets:", font=("Helvetica", 10, "bold"), bootstyle="warning").pack(anchor="w", pady=(10,0))
        self.entry_webapp_url = ttk.Entry(control_panel)
        self.entry_webapp_url.pack(fill="x", pady=5)
        
        ttk.Label(control_panel, text="URL do Curso:", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(10,0))
        self.entry_url = ttk.Entry(control_panel)
        self.entry_url.pack(fill="x", pady=5)

        ttk.Label(control_panel, text="Matéria (Obrigatório):", font=("Helvetica", 10, "bold"), bootstyle="primary").pack(anchor="w", pady=(10,0))
        self.combo_materia = ttk.Combobox(control_panel, values=self.lista_materias, state="readonly")
        if self.lista_materias: self.combo_materia.current(0) 
        self.combo_materia.pack(fill="x", pady=5)

        # --- NOVO FILTRO: ÁREA (CARREIRA) ---
        ttk.Label(control_panel, text="Área / Carreira:", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(10,0))
        self.combo_area = ttk.Combobox(control_panel, values=LISTA_AREAS_TEC, state="readonly")
        self.combo_area.pack(fill="x", pady=5)
        # ------------------------------------

        self.add_entry(control_panel, "Banca (ex: VUNESP):", "banca")
        self.add_entry(control_panel, "Ano (ex: 2023, 2024):", "ano")

        # Escolaridade
        ttk.Label(control_panel, text="Escolaridade:", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(10,0))
        self.frame_escolaridade = ttk.Frame(control_panel)
        self.frame_escolaridade.pack(fill="x", pady=5)
        self.vars_escolaridade = {
            "Superior": ttk.BooleanVar(value=False),
            "Médio": ttk.BooleanVar(value=False),
            "Fundamental": ttk.BooleanVar(value=False)
        }
        for nivel, var in self.vars_escolaridade.items():
            ttk.Checkbutton(self.frame_escolaridade, text=nivel, variable=var, bootstyle="round-toggle").pack(side="left", padx=5)

        # --- BOTÕES ---
        self.btn_review = ttk.Button(control_panel, text="🔍 Revisar Matches (IA)", bootstyle="info", command=self.start_review)
        self.btn_review.pack(pady=(20, 5), fill="x")

        self.btn_start = ttk.Button(control_panel, text="▶ INICIAR AUTOMAÇÃO", bootstyle="success", command=self.start_thread)
        self.btn_start.pack(pady=5, fill="x")

        # Botões de Saída
        frame_saida = ttk.Frame(control_panel)
        frame_saida.pack(fill="x", pady=5)
        
        self.btn_report = ttk.Button(frame_saida, text="Abrir Relatório", bootstyle="secondary", state="disabled", command=self.open_report)
        self.btn_report.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.btn_send_sheet = ttk.Button(frame_saida, text="Enviar p/ Planilha", bootstyle="warning", state="disabled", command=self.send_to_sheet_thread)
        self.btn_send_sheet.pack(side="right", fill="x", expand=True, padx=(2, 0))

        # Logs
        log_panel = ttk.Frame(self, padding=10)
        log_panel.grid(row=0, column=1, sticky="nsew")
        ttk.Label(log_panel, text="Logs do Processo", font=("Helvetica", 12, "bold")).pack(anchor="w")
        self.log_area = ScrolledText(log_panel, state="disabled", height=40)
        self.log_area.pack(fill="both", expand=True)

    def start_review(self):
        if not self.entry_url.get().strip():
            Messagebox.show_error("URL Obrigatória", "Erro")
            return
        
        self.save_settings()
        materia_selecionada = self.combo_materia.get()
        if not materia_selecionada:
            Messagebox.show_error("Selecione uma matéria.", "Erro")
            return

        config = self._get_config_dict()
        self.btn_review.config(state="disabled")
        self.log(f"🔍 Revisando para a matéria: {materia_selecionada}...")
        
        def review_worker():
            try:
                orc = Orchestrator(config, self.log, headless=False)
                data = orc.fetch_and_preview_matches()
                self.after(0, lambda: self._open_review_window(data, orc.cache_manager, orc.data_loader, materia_selecionada))
            except Exception as e:
                self.log(f"Erro na revisão: {e}")
                self.log(traceback.format_exc())
            finally:
                self.after(0, lambda: self.btn_review.config(state="normal"))

        threading.Thread(target=review_worker, daemon=True).start()

    def _open_review_window(self, data, cache_mgr, data_loader, materia_selecionada):
        if not data:
            self.log("⚠️ Nenhuma aula encontrada ou cache vazio.")
            return
            
        todos_filtros = data_loader.lista_completa_fallback + \
                        [item for sublist in data_loader.assuntos_por_materia.values() for item in sublist]
        
        filtros_materia = data_loader.assuntos_por_materia.get(materia_selecionada, [])

        def on_save_review(reviewed_data):
            count = 0
            for aula, filtros in reviewed_data.items():
                cache_mgr.set(aula, filtros)
                count += 1
            cache_mgr.save_cache()
            self.log(f"✅ {count} aulas salvas no cache!")
            Messagebox.show_info("Revisão Salva! Clique em 'INICIAR AUTOMAÇÃO' para gerar os cadernos.", "Sucesso")

        ReviewWindow(self, data, todos_filtros, filtros_materia, on_save_review)

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

    def save_settings(self):
        settings = self._get_config_dict()
        esc_save = {k: v.get() for k,v in self.vars_escolaridade.items()}
        settings["escolaridade"] = esc_save 
        del settings["materia_selecionada"]
        del settings["escolaridades"] 
        settings["materia"] = self.combo_materia.get()
        settings["webapp_url"] = self.entry_webapp_url.get()
        # Salva a Área
        settings["area_carreira"] = self.combo_area.get()
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
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
            if "materia" in settings and settings["materia"] in self.lista_materias:
                self.combo_materia.set(settings["materia"])
            if "escolaridade" in settings:
                for key, val in settings["escolaridade"].items():
                    if key in self.vars_escolaridade: self.vars_escolaridade[key].set(val)
            # Carrega Área
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
            "materia_selecionada": self.combo_materia.get(),
            "area_carreira": self.combo_area.get() # Inclui a nova configuração
        }

    def start_thread(self):
        if not self.entry_url.get().strip():
            Messagebox.show_error("URL Obrigatória", "Erro")
            return
        self.save_settings()
        if not self.combo_materia.get():
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

            payload = {
                "nomeDisciplina": config['materia_selecionada'],
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