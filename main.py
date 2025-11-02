# main.py
# Este arquivo agora atua como um "ponto de entrada" (entry point)
# que é chamado pela GUI para iniciar o processo.

import traceback
from typing import Dict, Any, Callable
from datetime import datetime

# A ÚNICA importação de lógica que precisamos é o Orquestrador,
# que agora centraliza todo o fluxo de trabalho.
from src.automation.orchestrator import Orchestrator

def run_automation_logic(config: Dict[str, Any], log_callback: Callable[..., None], headless: bool = False):
    """
    Função principal que INICIA a automação.

    Esta função não contém mais a lógica duplicada; ela apenas
    prepara os dados e delega a execução para a classe Orchestrator.

    Args:
        config (Dict[str, Any]): Dicionário vindo da GUI com as configurações.
        log_callback (Callable[..., None]): Função da GUI para logar mensagens.
        headless (bool, optional): Define se o navegador roda em modo invisível.
    """
    log_callback("=" * 80)
    log_callback(" 🚀 INICIANDO AUTOMAÇÃO A PARTIR DA INTERFACE 🚀")
    log_callback("=" * 80)
    
    try:
        # 1. "Traduz" o dicionário 'config' da GUI para o formato
        # 'user_data' que o Orquestrador espera.
        
        # Pega o sub-dicionário de filtros, ou um dict vazio se não existir
        filtros_gui = config.get("filtros", {})

        user_data = {
            "bo_user": config.get("bo_email"),
            "bo_pass": config.get("bo_password"),
            "tec_user": config.get("tec_email"),
            "tec_pass": config.get("tec_password"),
            "course_url": config.get("link_curso"),
            
            # O Orquestrador espera strings separadas por vírgula
            "banca": filtros_gui.get("bancas", ""),
            "ano": filtros_gui.get("anos", ""),
            "escolaridade": filtros_gui.get("escolaridades", "")
        }

        # 2. Cria a instância do Orquestrador
        # Toda a lógica complexa está encapsulada aqui.
        orchestrator = Orchestrator(
            user_data=user_data,
            log_callback=log_callback,
            headless=headless
        )
        
        # 3. Executa o fluxo completo
        # O Orquestrador cuidará de logar as Fases 1, 2, 3 e 4.
        orchestrator.run()
        
        log_callback("Automação concluída pelo Orquestrador.")

    except Exception as e:
        # Pega qualquer erro que possa acontecer *antes* do Orquestrador
        # ser chamado (ex: erro na preparação dos dados).
        log_callback(f"\n\n❌ ERRO INESPERADO NO 'main.py': {e}")
        log_callback(traceback.format_exc())

# --------------------------------------------------------------------------
# Bloco de Teste
# --------------------------------------------------------------------------
if __name__ == "__main__":
    """
    Este bloco SÓ é executado quando você roda o arquivo 
    diretamente no terminal (ex: `python main.py`).
    
    Isso é uma prática profissional para permitir testar a lógica
    principal (run_automation_logic) sem precisar da GUI.
    """
    
    print("--- EXECUTANDO main.py EM MODO DE TESTE (SEM GUI) ---")
    
    # 1. Define um "log_callback" falso que apenas imprime no console
    def console_logger(message: str):
        """Um logger simples que imprime mensagens no terminal."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")

    # 2. Define um dicionário de configuração 'mock' (falso)
    # !!! SUBSTITUA PELOS SEUS DADOS REAIS PARA TESTAR !!!
    mock_config_para_teste = {
        "bo_email": "seu_email_bo@dominio.com",
        "bo_password": "sua_senha_bo",
        "tec_email": "seu_email_tec@dominio.com",
        "tec_password": "sua_senha_tec",
        "link_curso": "https://url.do.curso.com/view?id=123456", # URL de exemplo
        "filtros": {
            "bancas": "CESPE, FGV", # Strings separadas por vírgula
            "anos": "2024, 2023",
            "escolaridades": "Superior"
        }
    }
    
    # 3. Executa a lógica principal com os dados de teste
    run_automation_logic(
        config=mock_config_para_teste,
        log_callback=console_logger,
        headless=False  # Queremos ver o navegador durante o teste
    )
