# src/automation/orchestrator.py (VERSÃO 10 - CORREÇÕES DE RELATÓRIO E FILTROS)

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
        self.log("Orquestrador iniciado.")
        
        self.cache_manager = CacheManager(log_callback=self.log)
        self.data_loader = DataLoader(log_callback=self.log)
        
        self.text_matcher = TextMatcher(
            log_callback=self.log,
            lista_materias=self.data_loader.materias,
            dict_assuntos_por_materia=self.data_loader.assuntos_por_materia,
            lista_completa_fallback=self.data_loader.lista_completa_fallback
        )

    def run(self) -> str:
        automation = WebAutomation(log_callback=self.log, headless=self.headless)
        try:
            automation.start()
            page = automation.page
            
            # FASE 1: Backoffice
            bo = BoAutomation(page, self.log)
            bo.login(self.user_data['bo_user'], self.user_data['bo_pass'])
            
            try:
                curso_id = self.user_data['course_url'].split('id=')[-1].strip()
            except:
                self.log("❌ URL inválida.")
                return None

            aulas_bo = bo.get_aulas(curso_id)
            
            # FASE 2: IA
            tarefas = self._match_aulas_inteligente(aulas_bo)
            
            # FASE 3: TEC
            # Prepara filtros (AGORA PASSANDO ESCOLARIDADES CORRETAMENTE)
            filtros_tec = self._prepare_filters()
            tec = TecAutomationPerfeito(page, self.log, filtros_tec)
            
            if tec.login(self.user_data['tec_user'], self.user_data['tec_pass']):
                resultados = tec.criar_multiplos_cadernos([t for t in tarefas if t['mapeado']])
                
                # Mescla resultados
                final_res = []
                mapa_res = {r['nome_caderno']: r for r in resultados}
                
                for t in tarefas:
                    if t['mapeado'] and t['nome_caderno'] in mapa_res:
                        t.update(mapa_res[t['nome_caderno']])
                    else:
                        if not t.get('success'):
                            t.update({"success": False, "erro": "Não mapeado/Falha", "num_questoes": 0})
                    
                    # --- CORREÇÃO CRÍTICA: Formata a lista de filtros para String ---
                    # Isso garante que apareça na tabela do relatório HTML
                    if 'materias' in t and isinstance(t['materias'], list):
                        t['filtros_ia'] = ", ".join(t['materias'])
                    else:
                        t['filtros_ia'] = "N/A"
                    # ---------------------------------------------------------------
                    
                    final_res.append(t)

                # FASE 4: Relatório
                gen = ReportGenerator(self.log)
                return gen.generate_report(self.user_data, final_res)

        except Exception as e:
            self.log(f"❌ Erro no fluxo: {e}")
            self.log(traceback.format_exc())
        finally:
            automation.stop()
        return None

    def _match_aulas_inteligente(self, aulas_bo):
        materia_alvo = self.user_data.get("materia_selecionada")
        tarefas = []
        def limpar(nome): return re.sub(r'(?i)aula\s+\d+\s*[:.-]\s*', '', nome).strip()
        aulas_limpas = [limpar(a) for a in aulas_bo]

        if materia_alvo:
            self.log(f"🔒 MODO FILTRADO: '{materia_alvo}'")
            matches = self.text_matcher.find_best_matches_filtered_batch(
                query_texts=aulas_limpas, target_materia=materia_alvo, threshold_assunto=0.60
            )
        else:
            self.log("🤖 MODO AUTOMÁTICO")
            matches = self.text_matcher.find_best_matches_hierarquico_batch(
                query_texts=aulas_limpas, threshold_materia=0.60, threshold_assunto=0.65, threshold_fallback=0.65
            )

        for aula_orig, match_list in zip(aulas_bo, matches):
            tarefas.append({
                "nome_caderno": f"Caderno - {aula_orig}",
                "materias": match_list,
                "mapeado": bool(match_list)
            })
        return tarefas

    def _prepare_filters(self):
        def to_list(s): return [x.strip() for x in s.split(',')] if s else []
        def to_int_list(s): return [int(x) for x in to_list(s) if x.isdigit()]
        
        return {
            "bancas": to_list(self.user_data.get('banca', '')),
            "anos": to_int_list(self.user_data.get('ano', '')),
            # Aqui mudamos a chave para 'escolaridades' (plural) para o robô entender
            "escolaridades": to_list(self.user_data.get('escolaridade', '')) 
        }