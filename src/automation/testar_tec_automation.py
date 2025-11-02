"""
Script de teste para a classe TecAutomationPerfeito
"""

from playwright.sync_api import sync_playwright
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, '/home/ubuntu')

from src.automation.tec_automation import TecAutomationPerfeito

# CONFIGURAÇÕES
TEC_EMAIL = "marroni.felipe@gmail.com"  # Substitua pelo seu email
TEC_PASSWORD = "sua_senha_aqui"  # Substitua pela sua senha

FILTROS_PADRAO = {
    "bancas": ["FGV"],
    "anos": [2024, 2023],
    "escolaridades": ["Médio"]
}

# Lista de aulas para criar cadernos
LISTA_AULAS = [
    {
        "nome_caderno": "Caderno - Aula 02: Classes de palavras, aspectos morfológicos, sintáticos, semânticos e textuais de substantivos, adjetivos, pronomes, artigos, numerais, advérbios e interjeições.",
        "materias": ["Morfologia"]
    },
    {
        "nome_caderno": "Caderno - Aula 03: Classes de palavras, aspectos morfológicos, sintáticos, semânticos e textuais de preposições e conjunções.",
        "materias": ["Morfologia"]
    },
    {
        "nome_caderno": "Caderno - Aula 04: Classes de palavras, aspectos morfológicos, sintáticos, semânticos e textuais de verbos.",
        "materias": ["Morfologia"]
    },
    {
        "nome_caderno": "Caderno - Aula 05: Estrutura e formação de palavras. Formas de abreviação.",
        "materias": ["Morfologia"]
    },
    {
        "nome_caderno": "Caderno - Aula 06: Organização sintática das frases: termos e orações. Ordem direta e inversa.",
        "materias": ["Sintaxe"]
    },
    {
        "nome_caderno": "Caderno - Aula 07: Pontuação e sinais gráficos.",
        "materias": ["Pontuação"]
    },
    {
        "nome_caderno": "Caderno - Aula 08: Concordância verbal e nominal.",
        "materias": ["Concordância"]
    },
    {
        "nome_caderno": "Caderno - Aula 09: Regência verbal e nominal. A crase.",
        "materias": ["Regência"]
    },
    {
        "nome_caderno": "Caderno - Aula 10: Marcas de textualidade: coesão, coerência. Tipologia e estrutura da frase: operações de deslocamento, substituição, modificação e correção. Problemas estruturais das frases.",
        "materias": ["Coerência"]
    },
    {
        "nome_caderno": "Caderno - Aula 11: Semântica: sentido próprio e figurado; antônimos, sinônimos, parônimos e hiperônimos. Polissemia e ambiguidade.",
        "materias": ["Semântica"]
    },
    {
        "nome_caderno": "Caderno - Aula 12: Interpretação e compreensão de texto. Organização estrutural dos textos. intertextualidade. Modos de organização discursiva: descrição, narração, exposição, argumentação e injunção; características específicas de cada modo. Tipos de discurso. Textos literários e não literários. Funções da linguagem. Os modalizadores.",
        "materias": ["Interpretação"]
    },
    {
        "nome_caderno": "Caderno - Aula 13 - Somente em PDF: Tipos textuais, características específicas de cada tipo.",
        "materias": ["Interpretação"]
    },
    {
        "nome_caderno": "Caderno - Aula 14: Norma culta. Registros de linguagem.",
        "materias": ["Linguagem"]
    },
    {
        "nome_caderno": "Caderno - Aula 15 - Somente em PDF: Elementos dos atos de comunicação. Os dicionários: tipos, organização de verbetes. Vocabulário: neologismos, arcaísmos, estrangeirismos, latinismos.",
        "materias": ["Linguagem"]
    },
    {
        "nome_caderno": "Caderno - Aula 16 - Somente em PDF: Aula extra",
        "materias": ["Português"]
    }
]


def main():
    print("="*80)
    print("  🚀 AUTOMAÇÃO TEC CONCURSOS - CRIAÇÃO DE CADERNOS 🚀")
    print("="*80)
    
    with sync_playwright() as p:
        # Iniciar navegador
        print("\nIniciando navegador...")
        browser = p.chromium.launch(
            headless=False,  # Mostrar navegador
            slow_mo=100  # Adicionar delay entre ações para visualização
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        
        try:
            # Criar instância da automação
            tec_robot = TecAutomationPerfeito(
                page=page,
                filtros_padrao=FILTROS_PADRAO
            )
            
            # Fazer login
            print("\n--- FASE 1: LOGIN NO TEC CONCURSOS ---")
            tec_robot.login(TEC_EMAIL, TEC_PASSWORD)
            
            # Criar cadernos
            print("\n--- FASE 2: CRIAÇÃO DE CADERNOS ---")
            resultados = tec_robot.criar_multiplos_cadernos(LISTA_AULAS)
            
            # Gerar tabela Markdown
            print("\n--- FASE 3: GERANDO TABELA MARKDOWN ---")
            
            tabela_md = []
            tabela_md.append("# Cadernos Criados - TEC Concursos\n")
            tabela_md.append("| Nome do Caderno | URL do Caderno | Status |\n")
            tabela_md.append("| :--- | :--- | :---: |\n")
            
            # Adicionar caderno já criado
            tabela_md.append("| Caderno - Aula 01: Ortografia e acentuação gráfica. | https://www.tecconcursos.com.br/questoes/cadernos/79761622 | ✅ |\n")
            
            # Adicionar novos resultados
            for r in resultados:
                status = "✅" if r.get("success") else "❌"
                nome = r.get("nome", "Sem nome")
                url = r.get("url", "Erro")
                tabela_md.append(f"| {nome} | {url} | {status} |\n")
            
            # Salvar tabela
            with open('/home/ubuntu/tabela_cadernos_final.md', 'w', encoding='utf-8') as f:
                f.writelines(tabela_md)
            
            print("\n✅ Tabela Markdown salva em: /home/ubuntu/tabela_cadernos_final.md")
            
            # Exibir tabela
            print("\n" + "="*80)
            print("TABELA MARKDOWN DOS CADERNOS")
            print("="*80)
            print("".join(tabela_md))
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Processo interrompido pelo usuário.")
        except Exception as e:
            print(f"\n\n❌ Erro durante a automação: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\nMantendo navegador aberto por 10 segundos...")
            page.wait_for_timeout(10000)
            browser.close()
            print("Navegador fechado.")


if __name__ == "__main__":
    main()