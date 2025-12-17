# src/gui/review_window.py
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from typing import List, Dict, Callable
import traceback

class ReviewWindow(ttk.Toplevel):
    def __init__(self, parent, data: List[Dict], all_filters: List[str], current_materia_filters: List[str], on_save: Callable):
        super().__init__(title="Revisão de Matches - Human in the Loop", master=parent)
        self.geometry("1100x850") # Ligeiramente maior para melhor respiro
        
        self.data = data 
        self.all_filters = sorted(list(set(all_filters))) if all_filters else []
        self.current_materia_filters = sorted(list(set(current_materia_filters))) if current_materia_filters else self.all_filters

        self.on_save_callback = on_save
        self.result_map = {} 

        self.create_ui()
        self.focus_force()

    def create_ui(self):
        # --- 1. HEADER (Visual Melhorado) ---
        # Aumentei o padding e usei inverse-primary para um visual de barra de título sólida
        header = ttk.Frame(self, padding=(20, 15), bootstyle="primary")
        header.pack(fill=X)
        
        title_frame = ttk.Frame(header, bootstyle="primary")
        title_frame.pack(side=LEFT)
        
        ttk.Label(title_frame, text="Revisão de Assuntos", font=("Segoe UI", 16, "bold"), bootstyle="inverse-primary").pack(anchor=W)
        ttk.Label(title_frame, text=f"Total de Aulas: {len(self.data)}", font=("Segoe UI", 10), bootstyle="inverse-primary").pack(anchor=W)

        legend = ttk.Frame(header, bootstyle="primary")
        legend.pack(side=RIGHT, anchor="center")
        
        # Legendas com visual mais limpo
        ttk.Label(legend, text="Legenda:", bootstyle="inverse-primary", font=("Segoe UI", 9, "bold")).pack(side=LEFT, padx=(0, 10))
        self._add_badge(legend, "IA (Alta Confiança)", "success")
        self._add_badge(legend, "IA (Baixa Confiança)", "warning")
        self._add_badge(legend, "Manual / Cache", "info")

        # --- 2. ÁREA DE CONTEÚDO ---
        # Container principal com padding para não colar nas bordas da janela
        container = ttk.Frame(self, padding=20)
        container.pack(fill=BOTH, expand=True)
        
        # Frame com borda sutil para delimitar a área de scroll
        scroll_container = ttk.Labelframe(container, text=" Lista de Aulas ", bootstyle="secondary", padding=2)
        scroll_container.pack(fill=BOTH, expand=True)

        scroll_container.grid_rowconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(0, weight=1)

        self.canvas = ttk.Canvas(scroll_container, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Barras de Rolagem com estilo 'round'
        vsb = ttk.Scrollbar(scroll_container, orient=VERTICAL, command=self.canvas.yview, bootstyle="round")
        vsb.grid(row=0, column=1, sticky="ns", padx=(2,0))
        
        hsb = ttk.Scrollbar(scroll_container, orient=HORIZONTAL, command=self.canvas.xview, bootstyle="round")
        hsb.grid(row=1, column=0, sticky="ew", pady=(2,0))

        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.scroll_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        # Eventos
        self.scroll_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        # Criação das Linhas
        # Adicionei um espaçador inicial
        ttk.Frame(self.scroll_frame, height=10).pack()
        for i, item in enumerate(self.data):
            self._create_row(self.scroll_frame, i, item)
        ttk.Frame(self.scroll_frame, height=10).pack()

        # --- 3. FOOTER ---
        # Separador visual antes do footer
        ttk.Separator(self, orient=HORIZONTAL).pack(fill=X)
        
        footer = ttk.Frame(self, padding=20)
        footer.pack(fill=X)
        
        # Botões maiores e com ícones (simulados via texto ou estilo)
        ttk.Button(footer, text="SALVAR E FECHAR", bootstyle="success", width=20, command=self.save_and_close).pack(side=RIGHT, padx=10)
        ttk.Button(footer, text="Cancelar", bootstyle="danger-outline", width=15, command=self.destroy).pack(side=RIGHT)

    # --- Funções de Controle do Canvas/Scroll (MANTIDAS) ---
    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        min_width = self.scroll_frame.winfo_reqwidth()
        if event.width >= min_width:
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        else:
            self.canvas.itemconfig(self.canvas_window, width=min_width)

    def _on_mousewheel(self, event):
        if self.canvas.winfo_exists():
             if self.canvas.bbox("all")[3] > self.canvas.winfo_height():
                if event.num == 5 or event.delta == -120:
                    self.canvas.yview_scroll(1, "units")
                elif event.num == 4 or event.delta == 120:
                    self.canvas.yview_scroll(-1, "units")

    def _on_shift_mousewheel(self, event):
        if self.canvas.winfo_exists():
            if event.num == 5 or event.delta == -120:
                self.canvas.xview_scroll(1, "units")
            elif event.num == 4 or event.delta == 120:
                self.canvas.xview_scroll(-1, "units")

    # --- Lógica Visual Melhorada ---
    def _add_badge(self, parent, text, style):
        # Badge visualmente mais agradável (pílula)
        frame = ttk.Frame(parent, bootstyle=style, padding=(10, 3)) # Padding cria o formato
        frame.pack(side="left", padx=5)
        ttk.Label(frame, text=text, bootstyle=f"inverse-{style}", font=("Segoe UI", 8, "bold")).pack()

    def _create_row(self, parent, idx, item):
        # Card da linha com borda 'info' para destaque sutil
        row_frame = ttk.Labelframe(
            parent, 
            text=f" Aula: {item['aula']} ", 
            padding=(15, 10), 
            bootstyle="info" 
        )
        row_frame.pack(fill=X, pady=8, padx=10) # Mais espaçamento vertical entre cards
        
        container = ttk.Frame(row_frame)
        container.pack(fill=X)
        
        tags_frame = ttk.Frame(container)
        tags_frame.pack(side="left", fill=X, expand=True)
        
        # Botão de adicionar mais sutil e alinhado
        btn_add = ttk.Button(
            container, 
            text="+ Adicionar Assunto", 
            bootstyle="link", 
            cursor="hand2",
            command=lambda f=tags_frame, a=item['aula']: self.add_filter_dialog(f, a)
        )
        btn_add.pack(side="right", anchor="center")

        self.result_map[item['aula']] = []
        
        # Se não houver matches, mostrar um texto explicativo
        if not item['matches']:
            ttk.Label(tags_frame, text="Nenhum assunto identificado.", bootstyle="secondary", font=("Segoe UI", 9, "italic")).pack(side=LEFT)

        for match in item['matches']:
            self._add_tag_widget(tags_frame, item['aula'], match)

    def _add_tag_widget(self, parent, aula_key, match_data):
        score = match_data.get('score', 0)
        origem = match_data.get('origem', 'IA')
        
        if origem == 'Manual' or origem == 'Cache':
            style = "info"
        elif score >= 0.75: 
            style = "success"
        else:
            style = "warning"
            
        term = match_data['termo']
        
        # Tag estilo "Chip" / "Pill"
        # Usando Frame colorido com padding interno maior
        tag = ttk.Frame(parent, bootstyle=style, padding=(10, 5)) 
        tag.pack(side="left", padx=4, pady=4)
        
        txt = f"{term} ({int(score*100)}%)" if score > 0 else term
        
        # Texto da tag
        ttk.Label(tag, text=txt, bootstyle=f"inverse-{style}", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
        
        # Separador vertical sutil (opcional, aqui feito com padding)
        
        # Botão de fechar (X) com cursor de mão e fonte maior
        btn_del = ttk.Label(tag, text="×", bootstyle=f"inverse-{style}", font=("Arial", 12, "bold"), cursor="hand2")
        btn_del.pack(side="right")
        
        def remove_tag(e):
            tag.destroy()
            self.result_map[aula_key] = [m for m in self.result_map[aula_key] if m['termo'] != term]
            
        btn_del.bind("<Button-1>", remove_tag)
        # Permite clicar no frame inteiro para deletar se quiser (opcional, removi para evitar clicks acidentais)
        
        current_terms = [x['termo'] for x in self.result_map[aula_key]]
        if term not in current_terms:
            self.result_map[aula_key].append(match_data)

    def add_filter_dialog(self, parent_tags, aula_key):
        top = ttk.Toplevel(title="Adicionar Filtro", master=self)
        top.geometry("600x300")
        
        # Centralizar visualmente (simples)
        top.place_window_center() 

        # Container interno com padding
        content = ttk.Frame(top, padding=20)
        content.pack(fill=BOTH, expand=True)
        
        ttk.Label(content, text="Adicionar Assunto Manualmente", font=("Segoe UI", 12, "bold"), bootstyle="primary").pack(pady=(0, 10))
        ttk.Label(content, text=f"Aula: {aula_key[:50]}...", font=("Segoe UI", 9, "italic")).pack(pady=(0, 20))
        
        ttk.Label(content, text="Digite para buscar na lista de matérias:", font=("Segoe UI", 9)).pack(anchor=W, pady=(0,5))
        
        cb = ttk.Combobox(content, values=self.current_materia_filters, height=10, font=("Segoe UI", 10))
        cb.pack(fill=X, pady=(0, 20))
        
        def on_type(event):
            typed = cb.get()
            if typed == '':
                cb['values'] = self.current_materia_filters
            else:
                typed_lower = typed.lower()
                matches = [f for f in self.all_filters if typed_lower in f.lower()][:50]
                cb['values'] = matches

        cb.bind('<KeyRelease>', on_type)

        def confirm():
            val = cb.get()
            if val:
                match_data = {'termo': val, 'score': 1.0, 'origem': 'Manual'}
                self._add_tag_widget(parent_tags, aula_key, match_data)
                top.destroy()
        
        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill=X, pady=10)
        
        ttk.Button(btn_frame, text="Adicionar Filtro", bootstyle="success", width=15, command=confirm).pack(side=RIGHT)
        ttk.Button(btn_frame, text="Cancelar", bootstyle="secondary-outline", command=top.destroy).pack(side=RIGHT, padx=10)
        
        cb.focus_set()

    def save_and_close(self):
        try:
            final_data = {}
            for aula, matches in self.result_map.items():
                final_data[aula] = [m['termo'] for m in matches]
            
            self.destroy()
            self.on_save_callback(final_data)
            
        except Exception as e:
            traceback.print_exc()
            Messagebox.show_error(f"Erro ao salvar revisão: {str(e)}", "Erro Crítico")
            self.destroy()