# src/automation/orchestrator.py
import traceback
import re
from typing import Dict, Any, Callable, List
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
        
        self.cache_manager = CacheManager(log_callback=self.log)
        self.data_loader = DataLoader(log_callback=self.log)
        
        self.text_matcher = TextMatcher(
            log_callback=self.log,
            lista_materias=self.data_loader.materias,
            dict_assuntos_por_materia=self.data_loader.assuntos_por_materia,
            lista_completa_fallback=self.data_loader.lista_completa_fallback
        )

    def _extract_course_id(self, url: str) -> str:
        try:
            return url.split('id=')[-1].strip()
        except:
            return "unknown"

    def fetch_and_preview_matches(self) -> List[Dict]:
        """
        BOTÃO 1: Lógica de Preparação (BackOffice + IA + Cache)
        """
        current_url = self.user_data.get('course_url', '')
        current_id = self._extract_course_id(current_url)
        cached_id = self.cache_manager.get_course_id()

        dados_para_review = []
        
        # 1. VERIFICAÇÃO DE MEMÓRIA (Pulo do Gato para evitar Login BO)
        if current_id and current_id == cached_id:
            self.log(f"🧠 Curso ID {current_id} reconhecido na memória.")
            self.log("⏩ Pulando acesso ao BackOffice e usando dados salvos.")
            
            # Reconstrói a estrutura para a ReviewWindow baseada apenas no Cache
            data_map = self.cache_manager.cache_structure["data"]
            if data_map:
                for aula, filtros in data_map.items():
                    matches_formatados = [{'termo': f, 'score': 1.0, 'origem': 'Memória'} for f in filtros]
                    dados_para_review.append({
                        'aula': aula,
                        'matches': matches_formatados
                    })
                return dados_para_review
            else:
                self.log("⚠️ Memória vazia, iniciando busca no BO...")

        # 2. SE NÃO TIVER MEMÓRIA, ACESSA O BO
        self.log(f"🔄 Novo curso detectado (ID: {current_id}). Iniciando acesso ao BO...")
        
        # Limpa cache antigo pois mudou o curso
        self.cache_manager.reset_cache()
        self.cache_manager.set_course_id(current_id)

        automation = WebAutomation(log_callback=self.log, headless=self.headless)
        try:
            automation.start()
            bo = BoAutomation(automation.page, self.log)
            bo.login(self.user_data['bo_user'], self.user_data['bo_pass'])
            
            aulas_bo = bo.get_aulas(current_id)
            if not aulas_bo:
                self.log("❌ Nenhuma aula encontrada no BO.")
                return []
            
        except Exception as e:
            self.log(f"Erro ao buscar aulas: {e}")
            return []
        finally:
            automation.stop()

        # 3. RODA A IA
        self.log("🤖 Processando aulas com IA...")
        tarefas_detalhadas = self._match_aulas_inteligente(aulas_bo, return_details=True)
        
        for tarefa in tarefas_detalhadas:
            dados_para_review.append({
                'aula': tarefa['aula_original'],
                'matches': tarefa['matches_detalhados']
            })
            
        return dados_para_review

    def run_tec_automation(self):
        """
        BOTÃO 2: Apenas execução no TEC (Baseado no Cache/Revisão)
        Retorna uma tupla: (caminho_relatorio, lista_dados_finais)
        """
        self.log("🚀 Iniciando fase de automação no TEC Concursos...")
        
        # 1. Carrega tarefas da memória
        tarefas = self.cache_manager.get_all_tasks_formatted()
        
        if not tarefas:
            self.log("❌ Nenhuma tarefa encontrada na memória.")
            self.log("⚠️ Por favor, execute 'Revisar Matches' primeiro e Salve a revisão.")
            return None, []

        self.log(f"📂 {len(tarefas)} cadernos prontos para criação.")

        automation = WebAutomation(log_callback=self.log, headless=self.headless)
        try:
            automation.start()
            page = automation.page
            
            # 2. Login e Criação no TEC
            filtros_tec = self._prepare_filters()
            tec = TecAutomationPerfeito(page, self.log, filtros_tec)
            
            if tec.login(self.user_data['tec_user'], self.user_data['tec_pass']):
                # Filtra apenas o que tem mapeamento
                cadernos_validos = [t for t in tarefas if t['mapeado']]
                
                if not cadernos_validos:
                    self.log("⚠️ Nenhuma aula possui matérias vinculadas. Nada a criar.")
                    return None, []

                resultados = tec.criar_multiplos_cadernos(cadernos_validos)
                
                # Consolidação para Relatório
                final_res = []
                mapa_res = {r['nome_caderno']: r for r in resultados}
                
                for t in tarefas:
                    if t['mapeado'] and t['nome_caderno'] in mapa_res:
                        t.update(mapa_res[t['nome_caderno']])
                    else:
                        if not t.get('success'):
                            t.update({"success": False, "erro": "Não mapeado/Ignorado", "num_questoes": 0})
                    
                    if 'materias' in t and isinstance(t['materias'], list):
                        t['filtros_ia'] = ", ".join(t['materias'])
                    else:
                        t['filtros_ia'] = "N/A"
                    final_res.append(t)

                gen = ReportGenerator(self.log)
                report_path = gen.generate_report(self.user_data, final_res)
                
                return report_path, final_res
            else:
                self.log("❌ Falha no login do TEC.")

        except Exception as e:
            self.log(f"❌ Erro fatal na automação TEC: {e}")
            self.log(traceback.format_exc())
        finally:
            automation.stop()
        return None, []

    def _match_aulas_inteligente(self, aulas_bo, return_details=False):
        materia_alvo = self.user_data.get("materia_selecionada")
        def limpar(nome): return re.sub(r'(?i)aula\s+\d+\s*[:.-]\s*', '', nome).strip()
        aulas_limpas = [limpar(a) for a in aulas_bo]

        if materia_alvo:
            matches = self.text_matcher.find_best_matches_filtered_batch(
                query_texts=aulas_limpas, target_materia=materia_alvo
            )
        else:
            matches = self.text_matcher.find_best_matches_hierarquico_batch(
                query_texts=aulas_limpas
            )

        if return_details:
            results = []
            for aula, match_list in zip(aulas_bo, matches):
                results.append({"aula_original": aula, "matches_detalhados": match_list})
            return results
        return matches

    def _prepare_filters(self):
        def to_list(s): return [x.strip() for x in s.split(',')] if s else []
        def to_int_list(s): return [int(x) for x in to_list(s) if x.isdigit()]
        
        # --- Lógica para Áreas (Sem limpeza regex) ---
        area_selecionada = self.user_data.get('area_carreira', '')
        areas_lista = []
        if area_selecionada:
            areas_lista.append(area_selecionada) # Usa texto original

        return {
            "bancas": to_list(self.user_data.get('banca', '')),
            "anos": to_int_list(self.user_data.get('ano', '')),
            "escolaridades": to_list(self.user_data.get('escolaridade', '')),
            "areas": areas_lista
        }