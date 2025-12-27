import sys
import os

# Garante que o diretório raiz do projeto esteja no PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importa a classe principal com o nome original (App)
from src.gui.main_window import App

if __name__ == "__main__":
    # Cria uma instância da nossa classe App
    app = App()
    # Inicia o loop principal da interface, que a mantém rodando e esperando
    # por interações do usuário (cliques, digitação, etc.)
    app.mainloop()