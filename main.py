# main.py
# Este arquivo agora atua como um "ponto de entrada" (entry point)
# que é chamado pela GUI para iniciar o processo.
# (VERSÃO ATUALIZADA PARA REPORT_GENERATOR HTML)

import traceback
from typing import Dict, Any, Callable
from datetime import datetime

# A ÚNICA importação de lógica que precisamos é o Orquestrador,
# que agora centraliza todo o fluxo de trabalho.
from src.automation.orchestrator import Orchestrator

def run_automation_logic(config: Dict[str, Any], log_callback: Callable[..., None], headless: bool = False) -> str:
    """
    Função principal que INICIA a automação.

    Args:
        config (Dict[str, Any]): Dicionário vindo da GUI com as configurações.
        log_callback (Callable[..., None]): Função da GUI para logar mensagens.
        headless (bool, optional): Define se o navegador roda em modo invisível.
        
    Returns:
        str: O caminho para o arquivo de relatório gerado, ou None.
    """
    log_callback("=" * 80)
    log_callback(" 🚀 INICIANDO AUTOMAÇÃO A PARTIR DA INTERFACE 🚀")
    log_callback("=" * 80)
    
    report_path = None # Inicializa o caminho
    
    try:
        # Pega o sub-dicionário de filtros (que conterá as listas processadas)
        filtros_gui = config.get("filtros", {})

        # MODIFICAÇÃO: O dicionário user_data agora passa
        # tanto os filtros processados (listas) para a automação,
        # quanto os filtros brutos (strings) para o relatório.
        user_data = {
            "bo_user": config.get("bo_email"),
            "bo_pass": config.get("bo_password"),
            "tec_user": config.get("tec_email"),
            "tec_pass": config.get("tec_password"),
            "course_url": config.get("link_curso"),
            
            # --- Para o Orchestrator (_prepare_tec_filters) ---
            # O Orchestrator sabe lidar com listas diretamente
            "banca": filtros_gui.get("bancas", []),
            "ano": filtros_gui.get("anos", []),
            "escolaridade": filtros_gui.get("escolaridades", []),
            
            # --- NOVOS CAMPOS: Para o ReportGenerator (HTML) ---
            # O ReportGenerator espera as strings brutas
            "report_bancas": config.get("report_bancas", ""),
            "report_anos": config.get("report_anos", ""),
            "report_escolaridade": config.get("report_escolaridade", "")
        }

        # Cria a instância do Orquestrador
        orchestrator = Orchestrator(
            user_data=user_data,
            log_callback=log_callback,
            headless=headless
        )
        
        # Captura o caminho do relatório retornado pelo .run()
        report_path = orchestrator.run()
        
        log_callback("Automação concluída pelo Orquestrador.")

    except Exception as e:
        # Pega qualquer erro que possa acontecer *antes* do Orquestrador
        log_callback(f"\n\n❌ ERRO INESPERADO NO 'main.py': {e}")
        log_callback(traceback.format_exc())
        
    # Retorna o caminho do relatório para a GUI
    return report_path

# --------------------------------------------------------------------------
# Bloco de Teste
# --------------------------------------------------------------------------
if __name__ == "__main__":
    
    print("--- EXECUTANDO main.py EM MODO DE TESTE (SEM GUI) ---")
    
    def console_logger(message: str):
        """Um logger simples que imprime mensagens no terminal."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")

    # MODIFICAÇÃO: O mock_config agora reflete a nova estrutura
    # que a GUI irá gerar (separando 'report_...' de 'filtros')
    mock_config_para_teste = {
        "bo_email": "seu_email_bo@dominio.com",
        "bo_password": "sua_senha_bo",
        "tec_email": "seu_email_tec@dominio.com",
        "tec_password": "sua_senha_tec",
        "link_curso": "https://url.do.curso.com/view?id=123456",
        
        # Strings brutas para o relatório
        "report_bancas": "CESPE, FGV", 
        "report_anos": "2024, 2023",
        "report_escolaridade": "Superior",
        
        # Listas processadas para a automação
        "filtros": {
            "bancas": ["CESPE", "FGV"],
            "anos": ["2024", "2023"], # O Orchestrator converte para int
            "escolaridades": ["Superior"]
        }
    }
    
    # Executa a lógica e imprime o resultado
    path_do_relatorio = run_automation_logic(
        config=mock_config_para_teste,
        log_callback=console_logger,
        headless=False  # Queremos ver o navegador durante o teste
    )
    
    if path_do_relatorio:
        print(f"\n--- TESTE CONCLUÍDO ---")
        print(f"Relatório gerado em: {path_do_relatorio}")
    else:
        print(f"\n--- TESTE FALHOU ---")
        print("Nenhum relatório foi gerado.")