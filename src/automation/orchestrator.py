# Ficheiro: src/automation/orchestrator.py
# (VERSÃO 7 - Passando dados completos para o relatório)

import traceback
from typing import Dict, Any, Callable, List
from playwright.sync_api import Page

from data.data_loader import DataLoader
from src.cache_manager import CacheManager
from .web_automation import WebAutomation
from .bo_integration import BoAutomation
from .tec_automation import TecAutomationPerfeito
from src.matching import TextMatcher
from src.reporting.report_generator import ReportGenerator

class Orchestrator:
    def __init__(self, user_data: Dict[str, Any], log_callback: Callable[..., None], headless: bool = False):
        self.user_data = user_data
        self.log = log_callback
        self.headless = headless
        
        self.log("Orquestrador inicializado.")
        
        # Carrega o cache de resultados (Aula -> Filtros)
        self.log("Carregando cache de matches da IA...")
        self.cache_manager = CacheManager(log_callback=self.log)
        
        try:
            # Carrega a estrutura de dados (Matérias -> Assuntos)
            self.log("Carregando estrutura de dados hierárquica...")
            self.data_loader = DataLoader(log_callback=self.log)
            self.log("✅ Estrutura de dados hierárquica carregada e processada.")

            # Inicializa a IA com os dados carregados
            self.log("Pré-calculando embeddings da IA...")
            self.text_matcher = TextMatcher(
                log_callback=self.log,
                # Passa os dados do DataLoader para o TextMatcher
                lista_materias=self.data_loader.materias,
                dict_assuntos_por_materia=self.data_loader.assuntos_por_materia,
                lista_completa_fallback=self.data_loader.lista_completa_fallback,
                model_name='paraphrase-multilingual-MiniLM-L12-v2'
            )
            self.log("✅ Modelo de IA e dados carregados com sucesso.")
            
        except Exception as e:
            self.log(f"❌ Falha crítica ao carregar TextMatcher ou DataLoader: {e}")
            self.log(traceback.format_exc())
            raise

    def run(self) -> str:
        """
        Executa o fluxo completo de automação, orquestrando as fases.
        """
        self.log("="*50)
        self.log("🚀 INICIANDO FLUXO DE AUTOMAÇÃO 🚀")
        self.log("="*50)
        
        report_path = None
        automation = WebAutomation(log_callback=self.log, headless=self.headless)
        
        try:
            automation.start()
            page = automation.page
            if not page:
                raise ConnectionError("Falha ao inicializar a página do navegador.")
            
            # --- FASE 1: Extração de Dados do Back Office ---
            bo_robot = BoAutomation(page=page, log_callback=self.log)
            lista_aulas_bo = self._run_phase_1_extract_bo_data(bo_robot)
            if not lista_aulas_bo:
                self.log("❌ Nenhuma aula encontrada no Back Office. Encerrando.")
                return None

            # --- FASE 2: Mapeamento Inteligente (IA) ---
            lista_tarefas_tec = self._run_phase_2_match_subjects_optimized(lista_aulas_bo)
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
            automation.stop()
            
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

    def _run_phase_2_match_subjects_optimized(self, lista_aulas_bo: List[str]) -> List[Dict[str, Any]]:
        """
        Usa o TextMatcher (IA) e o Cache para mapear nomes de aulas.
        """
        self.log("\n--- FASE 2: Mapeamento Hierárquico Otimizado (IA) ---")
        
        lista_tarefas_tec = []
        aulas_para_processar_ia = []
        mapa_aulas_para_processar = {}

        # 1. Verificar o cache
        for i, nome_aula_bo in enumerate(lista_aulas_bo):
            cache_result = self.cache_manager.get(nome_aula_bo)
            if cache_result is not None:
                self.log(f"  [Cache HIT] Aula: '{nome_aula_bo[:60]}...' -> {cache_result}")
                tarefa = {"nome_caderno": f"Caderno - {nome_aula_bo}", "materias": cache_result, "mapeado": bool(cache_result)}
                lista_tarefas_tec.append(tarefa)
            else:
                self.log(f"  [Cache MISS] Aula: '{nome_aula_bo[:60]}...'")
                aulas_para_processar_ia.append(nome_aula_bo)
                mapa_aulas_para_processar[nome_aula_bo] = i # Guardar índice
                # Adiciona um placeholder
                lista_tarefas_tec.append(None) 

        # 2. Processar o que faltou em lote
        if aulas_para_processar_ia:
            self.log(f"Enviando {len(aulas_para_processar_ia)} aulas para processamento em lote pela IA...")
            
            # Chama a IA (TextMatcher)
            resultados_ia_batch = self.text_matcher.find_best_matches_hierarquico_batch(
                query_texts=aulas_para_processar_ia,
                top_k_assuntos=2,
                threshold_materia=0.75,
                threshold_assunto=0.80,
                threshold_fallback=0.82
            )
            
            # 3. Atualizar o cache e a lista de tarefas
            for nome_aula, materias_mapeadas in zip(aulas_para_processar_ia, resultados_ia_batch):
                self.cache_manager.set(nome_aula, materias_mapeadas)
                
                tarefa = {"nome_caderno": f"Caderno - {nome_aula}", "materias": materias_mapeadas, "mapeado": bool(materias_mapeadas)}
                
                # Re-coloca na lista na ordem correta
                indice_original = mapa_aulas_para_processar[nome_aula]
                lista_tarefas_tec[indice_original] = tarefa
        
        # Salva o cache no disco (se houver mudanças)
        self.cache_manager.save_cache()
        
        self.log(f"{len(lista_tarefas_tec)} tarefas mapeadas com sucesso (total).")
        return lista_tarefas_tec


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
            return lista_tarefas_tec # Retorna a lista original (com "mapeado: False")
        
        self.log(f"Iniciando criação de {len(tarefas_mapeadas)} cadernos mapeados...")
        
        # Esta função agora retorna os resultados completos (com contagem, erros, etc.)
        resultados_criacao = tec_robot.criar_multiplos_cadernos(tarefas_mapeadas)
        
        # Mapeia os resultados pelo nome para fácil acesso
        mapa_resultados = {res.get("nome"): res for res in resultados_criacao}
        
        # Junta os resultados da criação com as tarefas que não foram mapeadas
        lista_final_resultados = []
        for tarefa in lista_tarefas_tec:
            if not tarefa.get("mapeado"):
                # Adiciona dados para o relatório (Req 1, 2, 3)
                tarefa["success"] = False
                tarefa["erro"] = "Não mapeado pela IA (Ex: Raio-X)"
                tarefa["num_questoes"] = 0
                tarefa["filtros_usados"] = []
                lista_final_resultados.append(tarefa)
                continue
            
            # Pega o resultado correspondente da criação do robô
            resultado = mapa_resultados.get(tarefa["nome_caderno"])
            if resultado:
                # O 'resultado' já tem tudo: success, url, erro, num_questoes, filtros_usados
                # Apenas atualizamos a 'tarefa' original com esses dados
                tarefa.update(resultado)
                lista_final_resultados.append(tarefa)
            else:
                # Fallback de segurança (não deve acontecer)
                tarefa["success"] = False
                tarefa["erro"] = "Resultado da criação não encontrado (Erro interno)"
                tarefa["num_questoes"] = 0
                tarefa["filtros_usados"] = tarefa.get("materias", [])
                lista_final_resultados.append(tarefa)
                
        return lista_final_resultados


    def _run_phase_4_report_results(self, resultados_finais: List[Dict[str, Any]]) -> str:
        """
        Loga um resumo e gera o arquivo de relatório .html.
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
                    self.log(f"    Erro: {r.get('erro', 'Erro desconhecido')}") # Agora mostra o erro limpo
        
        try:
            # --- PREPARA OS DADOS PARA O NOVO RELATÓRIO (REQ 1, 2, 3) ---
            dados_relatorio = []
            for r in resultados_finais:
                # Pega os filtros que a IA mapeou (ou que o robô tentou usar)
                filtros_ia = r.get("filtros_usados", r.get("materias", []))
                
                dados_relatorio.append({
                    "nome": r.get("nome_caderno", "Nome ausente"),
                    "success": r.get("success", False),
                    "url": r.get("url", ""),
                    "erro": r.get("erro", "N/A"), # Erro limpo
                    "num_questoes": r.get("num_questoes", 0), # Contagem de questões
                    "filtros_ia": ", ".join(filtros_ia) or "N/A" # Filtros da IA
                })
            # --- FIM DA PREPARAÇÃO ---

            report_gen = ReportGenerator(log_callback=self.log)
            
            report_path = report_gen.generate_report(
                user_data=self.user_data, 
                resultados=dados_relatorio # Passa os dados formatados
            )
            return report_path
            
        except Exception as e:
            self.log(f"❌ Falha inesperada ao tentar instanciar ou gerar o relatório HTML: {e}")
            self.log(traceback.format_exc())
            
        return None