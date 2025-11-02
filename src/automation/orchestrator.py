# orchestrator.py

import traceback
from typing import Dict, Any, Callable, List, Final
from playwright.sync_api import Page  # Importação explícita para type hinting

# Importa as classes dos nossos módulos de automação e IA
from .web_automation import WebAutomation
from .bo_integration import BoAutomation
from .tec_automation import TecAutomationPerfeito
from src.matching import TextMatcher  # matching está um nível acima

# Esta lista alimenta a IA. No futuro, podemos carregá-la de um arquivo.
# Usamos 'Final' para indicar que esta constante não deve ser modificada.
_LISTA_COMPLETA_FILTROS_TEC: Final[List[str]] = [
    "Direito Penal", "Teoria do Crime", "Crimes Contra a Vida",
    "Crimes Contra o Patrimônio", "Crimes Contra a Fé Pública",
    "Crimes Contra a Administração Pública", "Português", "Interpretação de Textos",
    "Ortografia", "Acentuação Gráfica", "Morfologia", "Sintaxe",
    "Concordância Verbal e Nominal", "Regência Verbal e Nominal", "Crase",
    "Pontuação", "Tipologia Textual", "Coesão e Coerência", "Semântica",
    "Contabilidade Geral", "Balanço Patrimonial", "Demonstração de Resultados (DRE)",
]

class Orchestrator:
    """
    Coordena todo o fluxo de trabalho da automação, conectando a GUI
    com os módulos de automação e IA.
    """
    def __init__(self, user_data: Dict[str, Any], log_callback: Callable[..., None], headless: bool = False):
        """
        Inicializa o orquestrador.

        Args:
            user_data (Dict[str, Any]): Dicionário com os dados do usuário vindos da GUI.
            log_callback (Callable): Função da GUI para enviar mensagens de log.
            headless (bool): Define se o navegador será executado em modo invisível.
        """
        self.user_data = user_data
        self.log = log_callback
        self.headless = headless
        
        self.log("Orquestrador inicializado. Carregando modelo de IA...")
        
        # REFACTOR: Injeta o log_callback no TextMatcher
        try:
            self.text_matcher = TextMatcher(log_callback=self.log)
            self.log("✅ Modelo de IA carregado.")
        except Exception as e:
            self.log(f"❌ Falha crítica ao carregar TextMatcher: {e}")
            # Re-lança a exceção para que o 'run_automation_logic' possa pegá-la
            raise

    def run(self):
        """
        Executa o fluxo completo de automação, orquestrando as fases.
        Este é o método principal que coordena o fluxo de trabalho.
        """
        self.log("="*50)
        self.log("🚀 INICIANDO FLUXO DE AUTOMAÇÃO 🚀")
        self.log("="*50)

        # REFACTOR: Injeta o log_callback no WebAutomation
        automacao = WebAutomation(log_callback=self.log, headless=self.headless)
        
        try:
            automacao.start()
            # Se 'start' falhar (lançar exceção), o 'finally' cuidará de 'automacao.stop()'
            
            page = automacao.page
            if not page:
                # Verificação caso automacao.start() falhe silenciosamente (embora não devesse)
                raise ConnectionError("Falha ao inicializar a página do navegador.")
            
            # --- FASE 1: Extração de Dados do Back Office ---
            # REFACTOR: Injeta o log_callback no BoAutomation
            bo_robot = BoAutomation(page=page, log_callback=self.log)
            lista_aulas_bo = self._run_phase_1_extract_bo_data(bo_robot)
            if not lista_aulas_bo:
                self.log("❌ Nenhuma aula encontrada no Back Office. Encerrando.")
                return

            # --- FASE 2: Mapeamento Inteligente (IA) ---
            lista_tarefas_tec = self._run_phase_2_match_subjects(lista_aulas_bo)
            if not lista_tarefas_tec:
                self.log("❌ Nenhuma aula pôde ser mapeada. Encerrando.")
                return

            # --- FASE 3: Criação dos Cadernos no TEC ---
            resultados = self._run_phase_3_create_tec_notebooks(page, lista_tarefas_tec)

            # --- FASE 4: Resultado Final ---
            self._run_phase_4_report_results(resultados)
            self.log("\n✅ PROCESSO CONCLUÍDO! ✅")

        except Exception as e:
            error_details = traceback.format_exc()
            self.log(f"\n❌ ERRO CRÍTICO NO ORQUESTRADOR: {e}")
            self.log(f"Detalhes: {error_details}")
        finally:
            self.log("Finalizando automação. O navegador será fechado em breve.")
            automacao.stop()

    def _get_course_id_from_url(self, course_url: str) -> str:
        """Helper para extrair o ID do curso da URL."""
        try:
            # Garante que 'id=' está presente antes de tentar dividir
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
        """
        self.log("\n--- FASE 2: Mapeando aulas para filtros usando IA ---")
        lista_tarefas_tec = []
        for nome_aula_bo in lista_aulas_bo:
            self.log(f"  Analisando aula: '{nome_aula_bo[:50]}...'")
            # Encontra os 2 melhores "matches" para o nome da aula na lista de filtros
            materias_mapeadas = self.text_matcher.find_best_matches(
                query_text=nome_aula_bo,
                candidates=_LISTA_COMPLETA_FILTROS_TEC,
                top_k=2
            )
            
            if not materias_mapeadas:
                self.log(f"    -> ⚠️ Aviso: Nenhuma correspondência forte encontrada.")
                continue
            
            self.log(f"    -> Mapeada para: {materias_mapeadas}")
            tarefa = {"nome_caderno": f"Caderno - {nome_aula_bo}", "materias": materias_mapeadas}
            lista_tarefas_tec.append(tarefa)
            
        self.log(f"{len(lista_tarefas_tec)} tarefas mapeadas com sucesso.")
        return lista_tarefas_tec

    def _prepare_tec_filters(self) -> Dict[str, Any]:
        """
        Helper para processar os filtros de texto da GUI em listas.
        """

        def process_filter_input(data: Any) -> List[str]:
            """Processa entrada que pode ser string ou lista."""
            if isinstance(data, str):
                # Se for string, split por vírgula
                return [item.strip() for item in data.split(',') if item.strip()]
            if isinstance(data, list):
                # Se já for lista, apenas garanta que são strings
                return [str(item).strip() for item in data if str(item).strip()]
            return []  # Retorna lista vazia se for None ou outro tipo

        def process_anos_input(data: Any) -> List[int]:
            """Processa entrada de anos (string ou lista) para lista de ints."""
            str_list = process_filter_input(data)
            int_list = []
            for item in str_list:
                if item.isdigit():
                    int_list.append(int(item))
            return int_list

        # Processa os campos da GUI (separados por vírgula) em listas limpas
        filtros_padrao = {
            "bancas": process_filter_input(self.user_data.get('banca')),
            "anos": process_anos_input(self.user_data.get('ano')),
            "escolaridades": process_filter_input(self.user_data.get('escolaridade'))
        }
        self.log(f"Filtros padrão preparados: {filtros_padrao}")
        return filtros_padrao

    def _run_phase_3_create_tec_notebooks(self, page: Page, lista_tarefas_tec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Executa a automação do TEC Concursos para criar os cadernos de questões.
        """
        self.log("\n--- FASE 3: Criando cadernos no TEC Concursos ---")
        
        filtros_padrao = self._prepare_tec_filters()
        
        # REFACTOR: Injeta o log_callback no TecAutomationPerfeito
        tec_robot = TecAutomationPerfeito(page=page, log_callback=self.log, filtros_padrao=filtros_padrao)
        
        if not tec_robot.login(self.user_data['tec_user'], self.user_data['tec_pass']):
             self.log("❌ Falha crítica no login do TEC! Encerrando automação.")
             # Lança um erro para ser pego pelo 'try' principal e parar a execução
             raise ConnectionError("Falha no login do TEC.")
        
        resultados = tec_robot.criar_multiplos_cadernos(lista_tarefas_tec)
        return resultados

    def _run_phase_4_report_results(self, resultados: List[Dict[str, Any]]):
        """
        Loga um resumo final da operação.
        (Futuramente, pode gerar um arquivo de relatório)
        """
        self.log("\n--- FASE 4: Processo Finalizado ---")
        if not resultados:
            self.log("Nenhum resultado para reportar.")
            return

        sucesso = sum(1 for r in resultados if r.get("success"))
        falha = len(resultados) - sucesso
        self.log(f"Resumo: {sucesso} cadernos criados com sucesso, {falha} falhas.")

        # Log detalhado das falhas (se houver)
        if falha > 0:
            self.log("Detalhe das falhas:")
            for r in resultados:
                if not r.get("success"):
                    self.log(f"  - Caderno: {r.get('nome')}")
                    self.log(f"    Erro: {r.get('erro')}")

