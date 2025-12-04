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

    def fetch_and_preview_matches(self) -> List[Dict]:
        """
        Modo de revisão: 
        1. Busca aulas no BO.
        2. Roda IA.
        3. FUNDE com o Cache (Memória) para respeitar correções anteriores.
        """
        # --- ALTERAÇÃO: NÃO LIMPAMOS MAIS O CACHE AQUI ---
        # self.cache_manager.clear_cache() <--- Removido para manter a memória
        
        automation = WebAutomation(log_callback=self.log, headless=self.headless)
        try:
            automation.start()
            bo = BoAutomation(automation.page, self.log)
            bo.login(self.user_data['bo_user'], self.user_data['bo_pass'])
            
            try:
                curso_id = self.user_data['course_url'].split('id=')[-1].strip()
            except:
                self.log("❌ URL inválida.")
                return []
                
            aulas_bo = bo.get_aulas(curso_id)
            
        except Exception as e:
            self.log(f"Erro ao buscar aulas: {e}")
            return []
        finally:
            automation.stop()

        self.log("🧠 IA processando aulas...")
        # A IA roda para todas as aulas (caso haja alguma nova)
        tarefas_detalhadas = self._match_aulas_inteligente(aulas_bo, return_details=True)
        
        dados_para_review = []
        
        # --- LÓGICA DE FUSÃO (Memória vs IA) ---
        for tarefa in tarefas_detalhadas:
            aula_nome = tarefa['aula_original']
            
            # Pergunta para a memória: "Já corrigimos essa aula antes?"
            memoria = self.cache_manager.get(aula_nome)
            
            matches_finais = []
            if memoria is not None:
                # Se tem memória, usa ela e marca como CACHE (Azul)
                self.log(f"💾 Recuperando memória para: {aula_nome[:30]}...")
                for filtro in memoria:
                    matches_finais.append({
                        'termo': filtro,
                        'score': 1.0,
                        'origem': 'Cache' # Isso fará aparecer em AZUL na tela
                    })
            else:
                # Se não tem memória, usa a sugestão da IA
                matches_finais = tarefa['matches_detalhados']

            dados_para_review.append({
                'aula': aula_nome,
                'matches': matches_finais
            })
            
        return dados_para_review

    def run(self) -> str:
        """Modo Execução: Verifica cache para pular BO"""
        automation = WebAutomation(log_callback=self.log, headless=self.headless)
        try:
            automation.start()
            page = automation.page
            
            tarefas = []
            
            # 1. Verifica Cache (Pulo do Gato)
            tarefas_em_cache = self.cache_manager.get_all_tasks_formatted()
            
            if tarefas_em_cache and len(tarefas_em_cache) > 0:
                self.log("⚡ MODO TURBO: Usando dados da memória (Cache).")
                self.log("⏩ Pulando Backoffice e IA...")
                tarefas = tarefas_em_cache
            else:
                self.log("ℹ️ Cache vazio. Executando fluxo completo.")
                
                # Fluxo Normal (BO + IA) - Só roda se nunca tiver revisado
                bo = BoAutomation(page, self.log)
                bo.login(self.user_data['bo_user'], self.user_data['bo_pass'])
                try:
                    curso_id = self.user_data['course_url'].split('id=')[-1].strip()
                except: return None
                aulas_bo = bo.get_aulas(curso_id)
                
                ia_matches = self._match_aulas_inteligente(aulas_bo, return_details=True)
                for item in ia_matches:
                    filters = [m['termo'] for m in item['matches_detalhados']]
                    tarefas.append({
                        "nome_caderno": f"Caderno - {item['aula_original']}",
                        "materias": filters,
                        "mapeado": bool(filters)
                    })

            # 2. Site TEC (Sempre roda)
            if not tarefas:
                self.log("❌ Nenhuma tarefa válida.")
                return None

            filtros_tec = self._prepare_filters()
            tec = TecAutomationPerfeito(page, self.log, filtros_tec)
            
            if tec.login(self.user_data['tec_user'], self.user_data['tec_pass']):
                resultados = tec.criar_multiplos_cadernos([t for t in tarefas if t['mapeado']])
                
                final_res = []
                mapa_res = {r['nome_caderno']: r for r in resultados}
                
                for t in tarefas:
                    if t['mapeado'] and t['nome_caderno'] in mapa_res:
                        t.update(mapa_res[t['nome_caderno']])
                    else:
                        if not t.get('success'):
                            t.update({"success": False, "erro": "Não mapeado/Falha", "num_questoes": 0})
                    
                    if 'materias' in t and isinstance(t['materias'], list):
                        t['filtros_ia'] = ", ".join(t['materias'])
                    else:
                        t['filtros_ia'] = "N/A"
                    final_res.append(t)

                gen = ReportGenerator(self.log)
                return gen.generate_report(self.user_data, final_res)

        except Exception as e:
            self.log(f"❌ Erro: {e}")
            self.log(traceback.format_exc())
        finally:
            automation.stop()
        return None

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
        return {
            "bancas": to_list(self.user_data.get('banca', '')),
            "anos": to_int_list(self.user_data.get('ano', '')),
            "escolaridades": to_list(self.user_data.get('escolaridade', '')) 
        }