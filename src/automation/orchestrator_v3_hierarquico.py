# orchestrator.py (VERSÃO 3 - MATCHING HIERÁRQUICO COM ASSUNTOS ESPECÍFICOS)
# ATUALIZADO: Usa matching em 2 níveis - primeiro matéria, depois assuntos específicos

import traceback
from typing import Dict, Any, Callable, List
from playwright.sync_api import Page

from .web_automation import WebAutomation
from .bo_integration import BoAutomation
from .tec_automation import TecAutomationPerfeito
from src.matching import TextMatcher
from src.reporting.report_generator import ReportGenerator

# NOVO: Importa a lista completa de filtros (matérias + assuntos)
try:
    from data.filtros_tec_completo import LISTA_COMPLETA_FILTROS_TEC
    print(f"✅ Lista completa carregada: {len(LISTA_COMPLETA_FILTROS_TEC)} filtros (matérias + assuntos)")
except ImportError:
    print("⚠️ Aviso: Não foi possível importar a lista completa de filtros.")
    print("   Tentando importar apenas matérias...")
    try:
        from data.filtros_tec_materias import LISTA_MATERIAS_TEC as LISTA_COMPLETA_FILTROS_TEC
        print(f"✅ Lista de matérias carregada: {len(LISTA_COMPLETA_FILTROS_TEC)} matérias")
    except ImportError:
        print("❌ ERRO: Nenhuma lista de filtros disponível!")
        LISTA_COMPLETA_FILTROS_TEC = []


class Orchestrator:
    def __init__(self, user_data: Dict[str, Any], log_callback: Callable[..., None], headless: bool = False):
        self.user_data = user_data
        self.log = log_callback
        self.headless = headless
        
        self.log("Orquestrador inicializado. Carregando modelo de IA...")
        self.log(f"📊 Base de filtros: {len(LISTA_COMPLETA_FILTROS_TEC)} filtros do TEC Concursos")
        self.log("🎯 Modo: MATCHING HIERÁRQUICO (assuntos específicos)")
        
        try:
            self.text_matcher = TextMatcher(log_callback=self.log)
            self.log("✅ Modelo de IA carregado.")
        except Exception as e:
            self.log(f"❌ Falha crítica ao carregar TextMatcher: {e}")
            raise

    def run(self) -> str:
        """
        Executa o fluxo completo de automação, orquestrando as fases.
        
        Returns:
            str: O caminho para o arquivo de relatório gerado, ou None se falhar.
        """
        self.log("="*50)
        self.log("🚀 INICIANDO FLUXO DE AUTOMAÇÃO 🚀")
        self.log("="*50)
        
        report_path = None

        automacao = WebAutomation(log_callback=self.log, headless=self.headless)
        
        try:
            automacao.start()
            page = automacao.page
            if not page:
                raise ConnectionError("Falha ao inicializar a página do navegador.")
            
            # --- FASE 1: Extração de Dados do Back Office ---
            bo_robot = BoAutomation(page=page, log_callback=self.log)
            lista_aulas_bo = self._run_phase_1_extract_bo_data(bo_robot)
            if not lista_aulas_bo:
                self.log("❌ Nenhuma aula encontrada no Back Office. Encerrando.")
                return None

            # --- FASE 2: Mapeamento Inteligente (IA) ---
            lista_tarefas_tec = self._run_phase_2_match_subjects(lista_aulas_bo)
            if not lista_tarefas_tec:
                self.log("❌ Nenhuma aula pôde ser mapeada. Encerrando.")
                return None

            # --- FASE 3: Criação dos Cadernos no TEC ---
            resultados_criacao = self._run_phase_3_create_tec_notebooks(page, lista_tarefas_tec)

            # --- FASE 4: Geração do Relatório Final ---
            report_path = self._run_phase_4_report_results(resultados_criacao)
            
            self.log("\n✅ PROCESSO CONCLUÍDO! ✅")

        except Exception as e:
            error_details = traceback.format_exc()
            self.log(f"\n❌ ERRO CRÍTICO NO ORQUESTRADOR: {e}")
            self.log(f"Detalhes: {error_details}")
        finally:
            self.log("Finalizando automação. O navegador será fechado em breve.")
            automacao.stop()
            
        return report_path

    def _get_course_id_from_url(self, course_url: str) -> str:
        """Helper para extrair o ID do curso da URL."""
        try:
            if 'id=' not in course_url:
                raise ValueError("URL não contém 'id='.")
            return course_url.split('id=')[-1].strip()
        except Exception as e:
            self.log(f"Erro ao parsear URL do curso ('{course_url}'): {e}")
            raise ValueError("URL do curso parece ser inválida.")

    def _run_phase_1_extract_bo_data(self, bo_robot: BoAutomation) -> List[str]:
        """
        Executa a automação do Back Office (BO) para extrair a lista de aulas.
        """
        self.log("\n--- FASE 1: Extraindo dados do Back Office ---")
        bo_robot.login(self.user_data['bo_user'], self.user_data['bo_pass'])
        
        codigo_curso = self._get_course_id_from_url(self.user_data['course_url'])
        
        lista_de_aulas_bo = bo_robot.get_aulas(codigo_curso)
        self.log(f"Encontradas {len(lista_de_aulas_bo)} aulas no BO.")
        return lista_de_aulas_bo

    def _run_phase_2_match_subjects(self, lista_aulas_bo: List[str]) -> List[Dict[str, Any]]:
        """
        Usa o TextMatcher (IA) para mapear nomes de aulas para filtros do TEC.
        VERSÃO HIERÁRQUICA: Busca assuntos específicos, não apenas matérias gerais.
        """
        self.log("\n--- FASE 2: Mapeamento Hierárquico (Assuntos Específicos) ---")
        self.log(f"Base de dados: {len(LISTA_COMPLETA_FILTROS_TEC)} filtros do TEC Concursos")
        
        lista_tarefas_tec = []
        for nome_aula_bo in lista_aulas_bo:
            self.log(f"  Analisando aula: '{nome_aula_bo[:60]}...'")
            
            # NOVO: Busca com threshold mais baixo para pegar assuntos específicos
            materias_mapeadas = self.text_matcher.find_best_matches(
                query_text=nome_aula_bo,
                candidates=LISTA_COMPLETA_FILTROS_TEC,
                top_k=2,  # Aumentado para pegar mais opções
                threshold=0.80  # Threshold mais baixo para assuntos específicos
            )
            
            if not materias_mapeadas:
                self.log(f"    -> ⚠️ Aviso: Nenhuma correspondência encontrada.")
                tarefa = {"nome_caderno": f"Caderno - {nome_aula_bo}", "materias": [], "mapeado": False}
                lista_tarefas_tec.append(tarefa)
                continue
            
            # NOVO: Filtrar para pegar apenas os mais específicos (não matérias gerais)
            # Prioriza assuntos que não são apenas o nome da matéria
            materias_filtradas = self._filtrar_assuntos_especificos(materias_mapeadas, nome_aula_bo)
            
            if not materias_filtradas:
                self.log(f"    -> ⚠️ Apenas correspondências genéricas encontradas.")
                materias_filtradas = materias_mapeadas[:2]  # Usar as 2 primeiras como fallback
            
            self.log(f"    -> ✅ Mapeada para: {materias_filtradas}")
            tarefa = {"nome_caderno": f"Caderno - {nome_aula_bo}", "materias": materias_filtradas, "mapeado": True}
            lista_tarefas_tec.append(tarefa)
            
        self.log(f"{len(lista_tarefas_tec)} tarefas mapeadas com sucesso.")
        return lista_tarefas_tec

    def _filtrar_assuntos_especificos(self, matches: List[str], nome_aula: str) -> List[str]:
        """
        Filtra os matches para priorizar assuntos específicos ao invés de matérias gerais.
        
        Estratégia:
        1. Remove matérias muito genéricas se houver assuntos mais específicos
        2. Prioriza matches que contêm palavras-chave da aula
        3. Limita a 3 assuntos mais relevantes
        """
        if not matches:
            return []
        
        # Lista de matérias muito genéricas que devemos evitar se houver alternativas
        materias_genericas = {
            'Direito Penal', 'Direito Processual Penal', 'Direito Administrativo',
            'Direito Constitucional', 'Direito Civil', 'Português', 'Matemática',
            'Legislação Penal e Processual Penal Especial'
        }
        
        # Separar matches em genéricos e específicos
        especificos = []
        genericos = []
        
        for match in matches:
            if match in materias_genericas:
                genericos.append(match)
            else:
                especificos.append(match)
        
        # Se temos assuntos específicos, priorizar eles
        if especificos:
            self.log(f"    -> 🎯 Priorizando assuntos específicos: {especificos[:3]}")
            return especificos[:3]  # Limitar a 3 assuntos específicos
        
        # Se só temos genéricos, retornar no máximo 2
        self.log(f"    -> ⚠️ Apenas matérias genéricas disponíveis: {genericos[:2]}")
        return genericos[:2]

    def _prepare_tec_filters(self) -> Dict[str, Any]:
        """
        Helper para processar os filtros de texto da GUI em listas.
        """

        def process_filter_input(data: Any) -> List[str]:
            if isinstance(data, str):
                return [item.strip() for item in data.split(',') if item.strip()]
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
            return []

        def process_anos_input(data: Any) -> List[int]:
            str_list = process_filter_input(data)
            int_list = []
            for item in str_list:
                if item.isdigit():
                    int_list.append(int(item))
            return int_list

        filtros_padrao = {
            "bancas": process_filter_input(self.user_data.get('banca')),
            "anos": process_anos_input(self.user_data.get('ano')),
            "escolaridade": process_filter_input(self.user_data.get('escolaridade'))
        }
        self.log(f"Filtros padrão preparados: {filtros_padrao}")
        return filtros_padrao

    def _run_phase_3_create_tec_notebooks(self, page: Page, lista_tarefas_tec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Executa a automação do TEC Concursos para criar os cadernos de questões.
        """
        self.log("\n--- FASE 3: Criando cadernos no TEC Concursos ---")
        
        filtros_padrao = self._prepare_tec_filters()
        
        tec_robot = TecAutomationPerfeito(page=page, log_callback=self.log, filtros_padrao=filtros_padrao)
        
        if not tec_robot.login(self.user_data['tec_user'], self.user_data['tec_pass']):
             self.log("❌ Falha crítica no login do TEC! Encerrando automação.")
             raise ConnectionError("Falha no login do TEC.")
        
        tarefas_mapeadas = [tarefa for tarefa in lista_tarefas_tec if tarefa.get("mapeado")]
        
        if not tarefas_mapeadas:
            self.log("⚠️ Nenhuma tarefa foi mapeada pela IA. Nenhum caderno será criado.")
            return lista_tarefas_tec
        
        self.log(f"Iniciando criação de {len(tarefas_mapeadas)} cadernos mapeados...")
        
        resultados_criacao = tec_robot.criar_multiplos_cadernos(tarefas_mapeadas)
        
        mapa_resultados = {res.get("nome"): res for res in resultados_criacao}
        
        lista_final_resultados = []
        for tarefa in lista_tarefas_tec:
            if not tarefa.get("mapeado"):
                tarefa["success"] = False
                tarefa["erro"] = "Não mapeado pela IA"
                lista_final_resultados.append(tarefa)
                continue
            
            resultado = mapa_resultados.get(tarefa["nome_caderno"])
            if resultado:
                tarefa.update(resultado)
                lista_final_resultados.append(tarefa)
            else:
                tarefa["success"] = False
                tarefa["erro"] = "Resultado da criação não encontrado"
                lista_final_resultados.append(tarefa)
                
        return lista_final_resultados


    def _run_phase_4_report_results(self, resultados_finais: List[Dict[str, Any]]) -> str:
        """
        Loga um resumo e gera o arquivo de relatório .html.
        
        Returns:
            str: O caminho do arquivo gerado, ou None.
        """
        self.log("\n--- FASE 4: Gerando Relatório Final ---")
        if not resultados_finais:
            self.log("Nenhum resultado para reportar.")
            return None

        sucesso = sum(1 for r in resultados_finais if r.get("success"))
        falha = len(resultados_finais) - sucesso
        self.log(f"Resumo da operação: {sucesso} cadernos criados, {falha} falhas (incluindo não-mapeados).")

        if falha > 0:
            self.log("Detalhe das falhas:")
            for r in resultados_finais:
                if not r.get("success"):
                    self.log(f"  - Caderno: {r.get('nome_caderno', 'Nome não encontrado')}")
                    self.log(f"    Erro: {r.get('erro', 'Erro desconhecido')}")
        
        try:
            dados_relatorio = [
                {
                    "nome": r.get("nome_caderno", "Nome ausente"),
                    "success": r.get("success", False),
                    "url": r.get("url", ""),
                    "erro": r.get("erro", "N/A")
                }
                for r in resultados_finais
            ]

            report_gen = ReportGenerator(log_callback=self.log)
            
            report_path = report_gen.generate_report(
                user_data=self.user_data, 
                resultados=dados_relatorio
            )
            return report_path
            
        except Exception as e:
            self.log(f"❌ Falha inesperada ao tentar instanciar ou gerar o relatório HTML: {e}")
            self.log(traceback.format_exc())
            
        return None
