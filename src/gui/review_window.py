# src/gui/review_window.py
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame
from ttkbootstrap.dialogs import Messagebox  # Adicionado para erros
from typing import List, Dict, Callable
import traceback

class ReviewWindow(ttk.Toplevel):
    def __init__(self, parent, data: List[Dict], all_filters: List[str], current_materia_filters: List[str], on_save: Callable):
        super().__init__(title="Revisão de Matches - Human in the Loop", master=parent)
        self.geometry("1000x800")
        
        self.data = data 
        self.all_filters = sorted(list(set(all_filters))) if all_filters else []
        self.current_materia_filters = sorted(list(set(current_materia_filters))) if current_materia_filters else self.all_filters

        self.on_save_callback = on_save
        self.result_map = {} 

        self.create_ui()

    def create_ui(self):
        header = ttk.Frame(self, padding=10, bootstyle="primary")
        header.pack(fill="x")
        ttk.Label(header, text="Revisão de Assuntos", font=("Helvetica", 14, "bold"), bootstyle="inverse-primary").pack(side="left")
        
        legend = ttk.Frame(header, bootstyle="primary")
        legend.pack(side="right")
        self._add_badge(legend, "IA (Alta)", "success")
        self._add_badge(legend, "IA (Baixa)", "warning")
        self._add_badge(legend, "Manual", "info")

        self.scroll = ScrolledFrame(self, autohide=True)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        for i, item in enumerate(self.data):
            self._create_row(self.scroll, i, item)

        footer = ttk.Frame(self, padding=10)
        footer.pack(fill="x")
        
        # Botão SALVAR agora chama o método corrigido
        ttk.Button(footer, text="SALVAR E FECHAR", bootstyle="success", command=self.save_and_close).pack(side="right", padx=10)
        ttk.Button(footer, text="Cancelar", bootstyle="danger-outline", command=self.destroy).pack(side="right")

    def _add_badge(self, parent, text, style):
        ttk.Label(parent, text=text, bootstyle=f"inverse-{style}", padding=5).pack(side="left", padx=5)

    def _create_row(self, parent, idx, item):
        row_frame = ttk.Labelframe(parent, text=f"Aula: {item['aula']}", padding=10, bootstyle="default")
        row_frame.pack(fill="x", pady=5, padx=5)
        
        container = ttk.Frame(row_frame)
        container.pack(fill="x")
        
        tags_frame = ttk.Frame(container)
        tags_frame.pack(side="left", fill="x", expand=True)
        
        btn_add = ttk.Button(container, text="+", bootstyle="secondary-outline", width=3, 
                           command=lambda f=tags_frame, a=item['aula']: self.add_filter_dialog(f, a))
        btn_add.pack(side="right", anchor="n")

        self.result_map[item['aula']] = []
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
        
        tag = ttk.Frame(parent, bootstyle=style, padding=2)
        tag.pack(side="left", padx=2, pady=2)
        
        txt = f"{term} ({int(score*100)}%)" if score > 0 else term
        ttk.Label(tag, text=txt, bootstyle=f"inverse-{style}").pack(side="left", padx=2)
        
        btn_del = ttk.Label(tag, text="✕", bootstyle=f"inverse-{style}", cursor="hand2")
        btn_del.pack(side="right", padx=2)
        
        def remove_tag(e):
            tag.destroy()
            self.result_map[aula_key] = [m for m in self.result_map[aula_key] if m['termo'] != term]
            
        btn_del.bind("<Button-1>", remove_tag)
        
        current_terms = [x['termo'] for x in self.result_map[aula_key]]
        if term not in current_terms:
            self.result_map[aula_key].append(match_data)

    def add_filter_dialog(self, parent_tags, aula_key):
        top = ttk.Toplevel(title="Adicionar Filtro", master=self)
        top.geometry("600x250")
        
        ttk.Label(top, text=f"Adicionar assunto em: {aula_key[:40]}...", font=("Helvetica", 10, "bold")).pack(pady=10)
        ttk.Label(top, text="Digite para filtrar:", font=("Helvetica", 9)).pack(pady=(0,5))
        
        cb = ttk.Combobox(top, values=self.current_materia_filters, height=10)
        cb.pack(fill="x", padx=20, pady=5)
        
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
        
        ttk.Button(top, text="Adicionar", bootstyle="success", command=confirm).pack(pady=10)
        cb.focus_set()

    def save_and_close(self):
        """
        Salva os dados e fecha a janela.
        Ordem invertida: Fecha -> Callback para evitar sobreposição de popups.
        """
        try:
            final_data = {}
            for aula, matches in self.result_map.items():
                final_data[aula] = [m['termo'] for m in matches]
            
            # 1. Fechamos a janela PRIMEIRO. 
            # Isso garante que o Messagebox da tela principal apareça livremente.
            self.destroy()
            
            # 2. Executamos o callback de salvamento
            self.on_save_callback(final_data)
            
        except Exception as e:
            # Se der erro, mostramos um alerta
            traceback.print_exc()
            Messagebox.show_error(f"Erro ao salvar revisão: {str(e)}", "Erro Crítico")
            self.destroy() # Fecha para não travar o fluxo