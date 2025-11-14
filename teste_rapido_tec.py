# Ficheiro: teste_rapido_tec.py
#
# Este é um script de "teste rápido" (debug) para focar
# APENAS na automação do TEC Concursos (Fase 3).
#
# Ele ignora a GUI, o BO e a IA, permitindo testar rapidamente
# mudanças no arquivo 'tec_automation.py'.
#
import traceback
from datetime import datetime
from typing import Dict, Any, Callable

# Importa as classes de automação necessárias
from src.automation.web_automation import WebAutomation
from src.automation.tec_automation import TecAutomationPerfeito

def console_logger(message: str):
    """Um logger simples que imprime mensagens no terminal."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")

def run_tec_test():
    """
    Executa um teste focado APENAS no 'tec_automation.py'.
    """
    log = console_logger
    log("="*80)
    log("🚀 INICIANDO TESTE RÁPIDO - FOCO NO TEC AUTOMATION 🚀")
    log("="*80)

    # --- DADOS FALSOS (MOCK) PARA O TESTE ---
    # (Baseado no seu log de erro anterior)
    
    # 1. Filtros Padrão (que viriam da GUI)
    filtros_teste = {
        "bancas": ["VUNESP"],
        "anos": [2024, 2023],
        "escolaridade": ["Médio"]
    }
    
    # 2. Tarefa (que viria da IA)
    #    Usando a "Aula 00" do seu log
    tarefa_teste = {
        "nome_caderno": "TESTE RÁPIDO - Aula 00 (Fé Pública)",
        "materias": [
            'Jurisprudência dos Tribunais Superiores sobre Crimes contra a Fé Pública', 
            'Dos Crimes contra a Fé Pública'
        ]
    }
    # ----------------------------------------

    # Inicia o navegador
    # Usamos headless=False para podermos ver o que o robô está fazendo
    with WebAutomation(log_callback=log, headless=False) as automation:
        try:
            page = automation.page
            
            # 1. Inicializa o robô do TEC
            log("Iniciando robô do TEC...")
            tec_robot = TecAutomationPerfeito(
                page=page, 
                log_callback=log, 
                filtros_padrao=filtros_teste
            )

            # 2. Faz o login manual (ele vai pausar)
            log("O robô irá pausar para login manual no TEC...")
            # As credenciais aqui não importam, pois ele pausa
            if not tec_robot.login("teste@teste.com", "123"):
                log("❌ Login falhou ou foi cancelado.")
                return

            # 3. Executa a função que queremos testar
            log(f"Login concluído. Executando 'create_notebook' para: '{tarefa_teste['nome_caderno']}'")
            resultado = tec_robot.create_notebook(
                nome_caderno=tarefa_teste["nome_caderno"],
                materias=tarefa_teste["materias"]
            )

            # 4. Mostra o resultado
            log("\n" + "-"*80)
            log("✅ TESTE CONCLUÍDO. RESULTADO:")
            log(f"  Sucesso: {resultado.get('success')}")
            log(f"  Nº Questões: {resultado.get('num_questoes')}")
            log(f"  URL: {resultado.get('url')}")
            log(f"  Erro: {resultado.get('erro')}")
            log(f"  Filtros Usados: {resultado.get('filtros_usados')}")
            log("-" * 80)

        except Exception as e:
            log(f"\n❌ ERRO CRÍTICO NO SCRIPT DE TESTE: {e}")
            log(traceback.format_exc())
        finally:
            log("Fechando o navegador em 10 segundos...")
            automation.page.wait_for_timeout(10000) # Pausa para ver o resultado

# --- Ponto de entrada do script ---
if __name__ == "__main__":
    run_tec_test()