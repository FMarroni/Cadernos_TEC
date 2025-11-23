# Ficheiro: verificacao_qualidade_ia.py
# (VERSÃO SEM PANDAS - Roda em qualquer ambiente Python)
#
# Script de AUDITORIA DE QUALIDADE.
# Objetivo: Comparar semanticamente o título da aula vs. o assunto encontrado
# para garantir que não estamos gerando "falsos positivos" ao baixar os thresholds.
#

import sys
import os
import re

# Adiciona o diretório atual ao path
sys.path.append(os.getcwd())

from src.matching import TextMatcher
from data.data_loader import DataLoader

def limpar_nome(nome):
    """A mesma limpeza usada no Orchestrator V8"""
    return re.sub(r'(?i)aula\s+\d+\s*[:.-]\s*', '', nome).strip()

def run_quality_audit():
    print("="*80)
    print("🧐 AUDITORIA DE QUALIDADE SEMÂNTICA DA IA")
    print("="*80)

    # 1. Carregar Dados
    print("Carregando estrutura de dados...")
    # Silencia o loader para não poluir o log
    loader = DataLoader(lambda x: None)
    
    # 2. Inicializar IA
    print("Inicializando IA...")
    matcher = TextMatcher(
        log_callback=lambda x: None, # Silencia logs técnicos
        lista_materias=loader.materias,
        dict_assuntos_por_materia=loader.assuntos_por_materia,
        lista_completa_fallback=loader.lista_completa_fallback
    )

    # 3. Casos Reais (Problemáticos e Normais) para Auditoria
    casos_reais = [
        # --- Caso 1: Introdução (Era falha) ---
        "Aula 01: Estado, Governo e Administração Pública. Direito Administrativo: fontes, objeto, conceito.",
        
        # --- Caso 2: Controle (Era falha) ---
        "Aula 17: Controle da Administração Pública.",
        
        # --- Caso 3: Atos (Era falha) ---
        "Aula 04: Ato administrativo: espécies e invalidação; cassação, revogação, anulação e convalidação.",
        
        # --- Caso 4: Pregão (Era falha crítica) ---
        "Aula 09: Pregão: Lei nº 10.520/02, Decreto Federal nº 5.450/05.",
        
        # --- Caso 5: Licitações (Teste de robustez) ---
        "Aula 11: Licitações à luz da lei 14.133/2021 - parte I; conceito, natureza jurídica.",
        
        # --- Caso 6: Terceiro Setor (Termo curto) ---
        "Aula 07: Entidades do Terceiro Setor.",
        
        # --- Caso 7: Improbidade (Lei específica) ---
        "Aula 18: Improbidade administrativa; Lei nº 8.429, de 1992."
    ]

    print(f"\nAnalisando {len(casos_reais)} casos com Thresholds Ajustados (0.60 / 0.65 / 0.65)...")
    print("-" * 130)

    # Prepara input limpo
    inputs_limpos = [limpar_nome(c) for c in casos_reais]

    # Roda a IA
    resultados = matcher.find_best_matches_hierarquico_batch(
        query_texts=inputs_limpos,
        top_k_assuntos=1,        # Queremos ver O MELHOR match
        threshold_materia=0.60,
        threshold_assunto=0.65,
        threshold_fallback=0.65  # O novo threshold crítico
    )

    # 4. Exibir Relatório de Qualidade (Formatação manual sem Pandas)
    # Header
    print(f"{'AULA ORIGINAL (LIMPA)':<55} | {'ASSUNTO ENCONTRADO NO TEC':<55} | {'VEREDITO'}")
    print("-" * 130)

    for original, limpo, match_list in zip(casos_reais, inputs_limpos, resultados):
        match_texto = match_list[0] if match_list else "❌ NÃO MAPEADO"
        
        # Truncar para caber na tabela
        titulo_aula = (limpo[:52] + '...') if len(limpo) > 52 else limpo
        assunto_tec = (match_texto[:52] + '...') if len(match_texto) > 52 else match_texto
        
        # Análise visual simples (se contém palavras chave)
        palavras_chave = set(limpo.lower().split())
        palavras_match = set(match_texto.lower().split()) if match_list else set()
        intersecao = palavras_chave.intersection(palavras_match)
        
        # Veredito automático simples
        if not match_list:
            veredito = "🔴 FALHA"
        elif len(intersecao) >= 2 or match_texto.lower() in limpo.lower() or limpo.lower() in match_texto.lower():
            veredito = "🟢 ALTA PRECISÃO"
        else:
            veredito = "🟡 REVISAR"

        print(f"{titulo_aula:<55} | {assunto_tec:<55} | {veredito}")

    print("-" * 130)
    print("\nLEGENDA:")
    print("🟢 ALTA PRECISÃO: O assunto encontrado compartilha várias palavras-chave com a aula.")
    print("🟡 REVISAR: O match aconteceu, mas verifique se o contexto é o mesmo (pode ser um termo relacionado).")
    print("🔴 FALHA: Nenhum assunto atingiu o score mínimo (0.65).")

if __name__ == "__main__":
    run_quality_audit()