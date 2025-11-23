# main.py (VERSÃO ORIGINAL RESTAURADA)

import sys
import os
from typing import Dict, Any, Callable

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.automation.orchestrator import Orchestrator

def run_automation_logic(config: Dict[str, Any], log_callback: Callable[..., None], headless: bool = False) -> str:
    """
    Função chamada pela GUI original (ttkbootstrap).
    """
    log_callback("=" * 50)
    log_callback("🚀 INICIANDO ORQUESTRADOR (MODO ORIGINAL)")
    log_callback("=" * 50)
    
    try:
        # Instancia o Orchestrator passando a config (que agora tem 'materia_selecionada')
        orchestrator = Orchestrator(
            user_data=config, 
            log_callback=log_callback,
            headless=headless
        )
        
        return orchestrator.run()
            
    except Exception as e:
        log_callback(f"❌ Erro fatal no main.py: {e}")
        return None

if __name__ == "__main__":
    print("Execute 'python run_gui.py' para abrir o programa.")