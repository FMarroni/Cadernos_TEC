# Ficheiro: teste_rapido_ia.py
#
# Script de teste focado APENAS na Fase 2 (IA e Matching).
# Objetivo: Validar se a limpeza de texto e os novos thresholds
# resolvem as falhas de mapeamento.
#

import sys
import os
import re

# Adiciona o diretório atual ao path para importar os módulos corretamente
sys.path.append(os.getcwd())

from src.matching import TextMatcher
from data.data_loader import DataLoader

def console_log(msg):
    print(f"[TESTE IA] {msg}")

def limpar_nome_aula(nome):
    """A mesma lógica de limpeza que implementamos no Orchestrator"""
    # Remove "Aula 00:", "Aula 10 :", "Aula 01 - " etc.
    return re.sub(r'(?i)aula\s+\d+\s*[:.-]\s*', '', nome).strip()

def run_ai_test():
    console_log("="*60)
    console_log("🚀 INICIANDO TESTE RÁPIDO DE IA (MATCHING) 🚀")
    console_log("="*60)

    # 1. Carregar Dados (Matérias e Assuntos)
    console_log("Carregando base de dados (JSON)...")
    try:
        data_loader = DataLoader(log_callback=console_log)
    except Exception as e:
        console_log(f"❌ Erro ao carregar DataLoader: {e}")
        return

    # 2. Inicializar a IA
    console_log("\nInicializando Modelo de IA (TextMatcher)...")
    matcher = TextMatcher(
        log_callback=console_log,
        lista_materias=data_loader.materias,
        dict_assuntos_por_materia=data_loader.assuntos_por_materia,
        lista_completa_fallback=data_loader.lista_completa_fallback
    )

    # 3. Definir os Casos de Teste (As aulas que falharam no seu log)
    casos_de_teste = [
        # Caso 1: Falhou com 0.792 (agora deve passar com threshold 0.70)
        "Aula 01: Estado, Governo e Administração Pública. Direito Administrativo: fontes, objeto, conceito.",
        
        # Caso 2: Falhou antes
        "Aula 17: Controle da Administração Pública.",
        
        # Caso 3: Aula complexa
        "Aula 04: Ato administrativo: espécies e invalidação; cassação, revogação, anulação e convalidação.",
        
        # Caso 4: Ruído excessivo
        "Aula 09: Pregão: Lei nº 10.520/02, Decreto Federal nº 5.450/05."
    ]

    console_log(f"\nProcessando {len(casos_de_teste)} casos de teste críticos...")

    # 4. Aplicar a Limpeza (Simulando o Orchestrator corrigido)
    aulas_limpas = [limpar_nome_aula(aula) for aula in casos_de_teste]
    
    # Mostra a limpeza no log para conferência
    console_log("-" * 50)
    for original, limpa in zip(casos_de_teste, aulas_limpas):
        console_log(f"📝 Original: '{original[:40]}...' -> Limpo: '{limpa[:40]}...'")
    console_log("-" * 50)

    # 5. Executar o Matching com os NOVOS THRESHOLDS
    # Thresholds sugeridos: Materia=0.60, Assunto=0.65, Fallback=0.70
    resultados = matcher.find_best_matches_hierarquico_batch(
        query_texts=aulas_limpas,
        top_k_assuntos=3,
        threshold_materia=0.60,   # Mais permissivo
        threshold_assunto=0.65,   # Mais permissivo
        threshold_fallback=0.70   # O "Pulo do Gato" para salvar o que não tem matéria explícita
    )

    # 6. Exibir Resultados Finais
    console_log("\n" + "="*60)
    console_log("📊 RESULTADO DO TESTE:")
    console_log("="*60)

    for i, (aula_original, resultado) in enumerate(zip(casos_de_teste, resultados)):
        status = "✅ SUCESSO" if resultado else "❌ FALHA"
        print(f"\nAula {i+1}: {aula_original}")
        print(f"Status: {status}")
        if resultado:
            print(f"   Mapeado para: {resultado}")
        else:
            print("   Motivo: Nenhum assunto atingiu os thresholds (0.60 / 0.65 / 0.70)")

if __name__ == "__main__":
    run_ai_test()