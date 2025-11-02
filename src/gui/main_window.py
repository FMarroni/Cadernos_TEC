# Importa a biblioteca ttkbootstrap como ttk. É aqui que a mágica começa!
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import threading

# A nossa lógica de automação continua sendo importada da mesma forma
from main import run_automation_logic

# A classe agora herda de ttk.Window, uma janela já estilizada
class App(ttk.Window):
    def __init__(self):
        # 'themename' define o estilo visual. 'litera' é um tema clean e moderno.
        super().__init__(themename="litera") 
        
        # --- Configurações da Janela Principal ---
        self.title("PROJETO - Automação de Cadernos")
        self.geometry("1200x800")
        
        # --- Layout Principal (idêntico ao anterior) ---
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=7)
        self.grid_rowconfigure(0, weight=1)

        # --- Criação dos Painéis ---
        self.create_control_panel()
        self.create_display_panel()

    def create_control_panel(self):
        # Usamos ttk.Frame que agora respeita o tema 'litera'
        control_frame = ttk.Frame(self, padding="15")
        control_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        title_label = ttk.Label(control_frame, text="Configurações", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10, fill='x')
        
        # Usamos ttk.LabelFrame, que também é estilizado
        credentials_frame = ttk.LabelFrame(control_frame, text="Credenciais de Acesso", padding="15")
        credentials_frame.pack(fill="x", pady=10)
        
        # Todos os widgets (Label, Entry) usarão o novo tema automaticamente
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
        
        course_frame = ttk.LabelFrame(control_frame, text="Informações do Curso", padding="15")
        course_frame.pack(fill="x", pady=10)
        
        ttk.Label(course_frame, text="Link do Curso no Back Office:").pack(fill="x", pady=(5,2))
        self.course_link_entry = ttk.Entry(course_frame)
        self.course_link_entry.pack(fill="x")

        filters_frame = ttk.LabelFrame(control_frame, text="Filtros para Questões", padding="15")
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

        # ATUALIZAÇÃO DO BOTÃO:
        # 'bootstyle="primary"' deixa o botão com a cor de destaque do tema (geralmente azul).
        self.start_button = ttk.Button(
            control_frame, 
            text="Iniciar Automação", 
            command=self.start_automation_thread,
            bootstyle="primary" 
        )
        self.start_button.pack(pady=20, ipady=10, fill='x')

    def create_display_panel(self):
        display_frame = ttk.Frame(self, padding="10")
        display_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        
        display_title = ttk.Label(display_frame, text="Painel de Execução", font=("Helvetica", 16, "bold"))
        display_title.pack(pady=10)
        
        self.log_area = ScrolledText(display_frame, state="disabled", wrap="word", font=("Courier New", 10))
        self.log_area.pack(expand=True, fill="both")
    
    # O restante do código (lógica do botão e de logs) permanece o mesmo
    def start_automation_thread(self):
        try:
            config = {
                "bo_email": self.bo_email_entry.get(),
                "bo_password": self.bo_password_entry.get(),
                "tec_email": self.tec_email_entry.get(),
                "tec_password": self.tec_password_entry.get(),
                "link_curso": self.course_link_entry.get(),
                "filtros": {
                    "bancas": [b.strip() for b in self.bancas_entry.get().split(',') if b.strip()],
                    "anos": [int(a.strip()) for a in self.anos_entry.get().split(',') if a.strip()],
                    "escolaridades": [self.escolaridade_combobox.get()]
                }
            }
            if not all([config["bo_email"], config["bo_password"], config["tec_email"], config["tec_password"], config["link_curso"]]):
                messagebox.showerror("Erro de Validação", "Todos os campos de credenciais e link do curso devem ser preenchidos.")
                return
        except ValueError:
            messagebox.showerror("Erro de Validação", "O campo 'Ano(s)' deve conter apenas números separados por vírgula.")
            return
        
        # 'bootstyle="success-outline"' muda o estilo do botão durante a execução
        self.start_button.config(state="disabled", text="Executando...")
        self.start_button.configure(bootstyle="success-outline")

        self.log_area.config(state="normal"); self.log_area.delete(1.0, "end"); self.log_area.config(state="disabled")

        automation_thread = threading.Thread(target=self.run_and_restore_button, args=(config,))
        automation_thread.daemon = True # Permite que a janela feche mesmo se a automação estiver rodando
        automation_thread.start()
        
    def run_and_restore_button(self, config):
        """Executa a automação e reativa o botão no final, mesmo se der erro."""
        try:
            run_automation_logic(config, self.log_message)
        finally:
            self.start_button.config(state="normal", text="Iniciar Automação")
            self.start_button.configure(bootstyle="primary")

    def log_message(self, message):
        self.after(0, self._add_log, message)

    def _add_log(self, message):
        self.log_area.config(state="normal")
        self.log_area.insert("end", str(message) + "\n")
        self.log_area.config(state="disabled")
        self.log_area.see("end")