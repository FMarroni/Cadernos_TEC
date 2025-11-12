# Ficheiro: src/gui/main_window.py
# (VERSÃO ATUALIZADA PARA RELATÓRIO HTML)

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import webbrowser # Usado para abrir o link do relatório
import os # Usado para verificar se o relatório existe

from main import run_automation_logic

class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="litera") 
        
        self.title("PROJETO - Automação de Cadernos")
        self.geometry("1200x800")
        
        # NOVO: Variável para guardar o caminho do último relatório
        self.last_report_path = None
        
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=7)
        self.grid_rowconfigure(0, weight=1)

        self.create_control_panel()
        self.create_display_panel()

    def create_control_panel(self):
        control_frame = ttk.Frame(self, padding="15")
        control_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        title_label = ttk.Label(control_frame, text="Configurações", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10, fill='x')
        
        credentials_frame = ttk.Labelframe(control_frame, text="Credenciais de Acesso", padding="15")
        credentials_frame.pack(fill="x", pady=10)
        
        ttk.Label(credentials_frame, text="E-mail Back Office:").pack(fill="x", pady=(5,2))
        self.bo_email_entry = ttk.Entry(credentials_frame)
        self.bo_email_entry.pack(fill="x")
        
        ttk.Label(credentials_frame, text="Senha Back Office:").pack(fill="x", pady=(5,2))
        self.bo_password_entry = ttk.Entry(credentials_frame, show="*")
        self.bo_password_entry.pack(fill="x")
        
        ttk.Label(credentials_frame, text="E-mail TEC:").pack(fill="x", pady=(5,2))
        self.tec_email_entry = ttk.Entry(credentials_frame)
        self.tec_email_entry.pack(fill="x")
        
        ttk.Label(credentials_frame, text="Senha TEC:").pack(fill="x", pady=(5,2))
        self.tec_password_entry = ttk.Entry(credentials_frame, show="*")
        self.tec_password_entry.pack(fill="x")
        
        course_frame = ttk.Labelframe(control_frame, text="Informações do Curso", padding="15")
        course_frame.pack(fill="x", pady=10)
        
        ttk.Label(course_frame, text="Link do Curso no Back Office:").pack(fill="x", pady=(5,2))
        self.course_link_entry = ttk.Entry(course_frame)
        self.course_link_entry.pack(fill="x")

        filters_frame = ttk.Labelframe(control_frame, text="Filtros para Questões", padding="15")
        filters_frame.pack(fill="x", pady=10)
        
        ttk.Label(filters_frame, text="Banca(s) (separado por vírgula):").pack(fill="x", pady=(5,2))
        self.bancas_entry = ttk.Entry(filters_frame)
        self.bancas_entry.pack(fill="x")
        
        ttk.Label(filters_frame, text="Ano(s) (separado por vírgula):").pack(fill="x", pady=(5,2))
        self.anos_entry = ttk.Entry(filters_frame)
        self.anos_entry.pack(fill="x")
        
        ttk.Label(filters_frame, text="Escolaridade:").pack(fill="x", pady=(5,2))
        self.escolaridade_combobox = ttk.Combobox(filters_frame, values=["Superior", "Médio", "Fundamental"])
        self.escolaridade_combobox.pack(fill="x")
        self.escolaridade_combobox.set("Superior")

        self.start_button = ttk.Button(
            control_frame, 
            text="Iniciar Automação", 
            command=self.start_automation_thread,
            bootstyle="primary" 
        )
        self.start_button.pack(pady=20, ipady=10, fill='x')

        # MODIFICADO: Este é o novo botão de relatório
        self.open_report_button = ttk.Button(
            control_frame,
            text="Abrir Último Relatório",
            command=self.open_report, # Aponta para a nova função
            bootstyle="secondary-outline", # Estilo inicial
            state="disabled" # Começa desativado
        )
        self.open_report_button.pack(pady=5, ipady=5, fill='x')

    def create_display_panel(self):
        display_frame = ttk.Frame(self, padding="10")
        display_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        
        display_title = ttk.Label(display_frame, text="Painel de Execução", font=("Helvetica", 16, "bold"))
        display_title.pack(pady=10)
        
        self.log_area = ScrolledText(display_frame, state="disabled", wrap="word", font=("Courier New", 10))
        self.log_area.pack(expand=True, fill="both")
    
    # REMOVIDO: A função open_gdrive_folder foi retirada.

    # NOVO: Função para abrir o relatório HTML
    def open_report(self):
        """Abre o ficheiro de relatório HTML gerado no navegador padrão."""
        if self.last_report_path and os.path.exists(self.last_report_path):
            try:
                # 'file://' é necessário para garantir que o navegador abra o ficheiro local
                url = f"file://{os.path.abspath(self.last_report_path)}"
                webbrowser.open_new_tab(url)
                self.log_message(f"Abrindo relatório em: {url}")
            except Exception as e:
                self.log_message(f"Erro ao tentar abrir o relatório: {e}")
                messagebox.showerror("Erro ao Abrir", f"Não foi possível abrir o relatório:\n{e}")
        else:
            messagebox.showinfo("Nenhum Relatório", "Nenhum relatório foi gerado nesta sessão ou o ficheiro foi movido.")


    def start_automation_thread(self):
        # Prepara os valores brutos dos filtros para o relatório
        report_bancas = self.bancas_entry.get()
        report_anos = self.anos_entry.get()
        report_escolaridade = self.escolaridade_combobox.get()
        
        try:
            # Prepara os filtros processados (listas) para a automação
            filtros_bancas = [b.strip() for b in report_bancas.split(',') if b.strip()]
            filtros_anos = [a.strip() for a in report_anos.split(',') if a.strip() and a.strip().isdigit()]
            filtros_escolaridade = [report_escolaridade]

            # Validação simples para o campo 'anos'
            anos_nao_numericos = [a.strip() for a in report_anos.split(',') if a.strip() and not a.strip().isdigit()]
            if anos_nao_numericos:
                messagebox.showerror("Erro de Validação", f"O campo 'Ano(s)' contém valores não numéricos: {', '.join(anos_nao_numericos)}")
                return

            config = {
                "bo_email": self.bo_email_entry.get(),
                "bo_password": self.bo_password_entry.get(),
                "tec_email": self.tec_email_entry.get(),
                "tec_password": self.tec_password_entry.get(),
                "link_curso": self.course_link_entry.get(),
                
                # Campos brutos para o relatório
                "report_bancas": report_bancas,
                "report_anos": report_anos,
                "report_escolaridade": report_escolaridade,
                
                # Filtros processados (listas) para a automação
                "filtros": {
                    "bancas": filtros_bancas,
                    "anos": filtros_anos,
                    "escolaridades": filtros_escolaridade
                }
            }
            
            if not all([config["bo_email"], config["bo_password"], config["tec_email"], config["tec_password"], config["link_curso"]]):
                messagebox.showerror("Erro de Validação", "Todos os campos de credenciais e link do curso devem ser preenchidos.")
                return
        
        except Exception as e:
            messagebox.showerror("Erro na Preparação", f"Ocorreu um erro ao preparar os dados: {e}")
            return
        
        # Desativa os botões e limpa o estado
        self.start_button.config(state="disabled", text="Executando...")
        self.start_button.configure(bootstyle="success-outline")
        self.open_report_button.config(state="disabled", bootstyle="secondary-outline")
        self.last_report_path = None # Limpa o caminho do relatório anterior

        self.log_area.config(state="normal"); self.log_area.delete(1.0, "end"); self.log_area.config(state="disabled")

        automation_thread = threading.Thread(target=self.run_and_restore_button, args=(config,))
        automation_thread.daemon = True
        automation_thread.start()
        
    def run_and_restore_button(self, config):
        """Executa a automação e reativa os botões no final."""
        
        # NOVO: Captura o caminho do relatório retornado pela lógica
        report_path = None
        
        try:
            # A lógica de automação agora retorna o caminho do relatório
            report_path = run_automation_logic(config, self.log_message)
            
        except Exception as e:
            # Log de segurança para qualquer erro não capturado dentro do thread
            self.log_message(f"ERRO FATAL NO THREAD: {e}")
            
        finally:
            # Restaura o botão de iniciar
            self.start_button.config(state="normal", text="Iniciar Automação")
            self.start_button.configure(bootstyle="primary")
            
            # NOVO: Verifica se o relatório foi criado com sucesso
            if report_path and os.path.exists(report_path):
                self.log_message(f"Relatório gerado com sucesso!")
                self.log_message(f"Caminho: {report_path}")
                self.last_report_path = report_path
                # Ativa o botão de relatório e muda a cor
                self.open_report_button.config(state="normal", bootstyle="success")
            else:
                self.log_message("A automação terminou, mas nenhum relatório foi gerado.")
                # Mantém o botão de relatório desativado
                self.open_report_button.config(state="disabled", bootstyle="secondary-outline")


    def log_message(self, message):
        self.after(0, self._add_log, message)

    def _add_log(self, message):
        self.log_area.config(state="normal")
        self.log_area.insert("end", str(message) + "\n")
        self.log_area.config(state="disabled")
        self.log_area.see("end")