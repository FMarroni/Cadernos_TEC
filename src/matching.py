# src/matching.py (VERSÃO 5.1 - CORREÇÃO DO NameError)
# Esta versão SALVA os embeddings calculados em disco para evitar o recálculo de 15 minutos a cada inicialização.

import torch
import os
import pickle  # Usado para salvar e carregar os embeddings
from sentence_transformers import SentenceTransformer, util
from typing import List, Callable, Dict, Any

# --- Define os caminhos para salvar os embeddings ---
CACHE_DIR = "cache/embeddings"
MATERIAS_EMBEDDINGS_CACHE = os.path.join(CACHE_DIR, "materias_embeddings.pkl")
ASSUNTOS_EMBEDDINGS_CACHE = os.path.join(CACHE_DIR, "assuntos_embeddings.pkl")
FALLBACK_EMBEDDINGS_CACHE = os.path.join(CACHE_DIR, "fallback_embeddings.pkl")

class TextMatcher:
    """
    Usa IA para encontrar as melhores correspondências semânticas.
    Agora inclui cache em disco para os embeddings.
    """
    def __init__(self,
                 log_callback: Callable[..., None],
                 lista_materias: List[str],
                 dict_assuntos_por_materia: Dict[str, List[str]],
                 lista_completa_fallback: List[str],
                 model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        
        self.log = log_callback
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.log(f"Usando dispositivo: {self.device} para IA.")

        self.log(f"Carregando modelo de IA '{model_name}' (isso pode levar um momento)...")
        try:
            self.model = SentenceTransformer(model_name, device=self.device)
            self.log("✅ Modelo de IA carregado com sucesso.")
        except Exception as e:
            self.log(f"❌ ERRO CRÍTICO: Falha ao carregar o modelo de IA '{model_name}'.")
            self.log(f"Detalhes do erro: {e}")
            raise

        # --- LÓGICA DE CACHE DE EMBEDDINGS ---
        
        # 1. Guarda as listas de texto
        self.lista_materias = lista_materias
        self.dict_assuntos_por_materia = dict_assuntos_por_materia
        self.lista_completa_fallback = lista_completa_fallback
        
        # 2. Carrega ou Calcula os embeddings das MATÉRIAS
        self.materias_embeddings = self._load_or_compute_embeddings(
            self.lista_materias,
            MATERIAS_EMBEDDINGS_CACHE,
            "matérias"
        )
        
        # 3. Carrega ou Calcula os embeddings dos ASSUNTOS (Hierárquico)
        self.assuntos_embeddings_por_materia = {}
        assuntos_para_calcular = {}
        try:
            # Tenta carregar o cache principal de assuntos
            assuntos_cache_file = ASSUNTOS_EMBEDDINGS_CACHE
            if os.path.exists(assuntos_cache_file):
                self.log(f"Carregando embeddings de assuntos do cache: {assuntos_cache_file}")
                with open(assuntos_cache_file, 'rb') as f:
                    self.assuntos_embeddings_por_materia = pickle.load(f)
                self.log(f"✅ Embeddings de {len(self.assuntos_embeddings_por_materia)} matérias (com assuntos) carregados.")
            else:
                # Se o cache não existe, marca todos para cálculo
                self.log("Nenhum cache de embeddings de assuntos encontrado. Calculando...")
                assuntos_para_calcular = self.dict_assuntos_por_materia
        
            # Lógica de "preencher" se novas matérias foram adicionadas
            for materia, assuntos in self.dict_assuntos_por_materia.items():
                if materia not in self.assuntos_embeddings_por_materia and assuntos:
                    assuntos_para_calcular[materia] = assuntos

            if assuntos_para_calcular:
                self.log(f"Calculando embeddings para {len(assuntos_para_calcular)} matérias (novas ou sem cache)...")
                # Calcula os embeddings para as matérias que faltam
                for materia, assuntos in assuntos_para_calcular.items():
                    self.log(f"  - Processando {len(assuntos)} assuntos de '{materia}'...")
                    self.assuntos_embeddings_por_materia[materia] = self.model.encode(
                        assuntos, convert_to_tensor=True, show_progress_bar=False
                    )
                # Salva o cache atualizado
                self._save_embeddings(self.assuntos_embeddings_por_materia, ASSUNTOS_EMBEDDINGS_CACHE)

        except Exception as e:
            self.log(f"AVISO: Falha ao carregar/processar cache de assuntos: {e}. Recalculando tudo.")
            # Recalcula tudo se o cache falhar
            self.assuntos_embeddings_por_materia = {}
            for materia, assuntos in self.dict_assuntos_por_materia.items():
                if assuntos: # Só processa se houver assuntos
                    self.assuntos_embeddings_por_materia[materia] = self.model.encode(
                        assuntos, convert_to_tensor=True, show_progress_bar=False
                    )
            self._save_embeddings(self.assuntos_embeddings_por_materia, ASSUNTOS_EMBEDDINGS_CACHE)
            
        # 4. Carrega ou Calcula os embeddings de FALLBACK
        self.fallback_embeddings = self._load_or_compute_embeddings(
            self.lista_completa_fallback,
            FALLBACK_EMBEDDINGS_CACHE,
            "filtros de fallback"
        )
        
        self.log("✅ Todos os embeddings estão prontos.")


    def _load_or_compute_embeddings(self, texts: List[str], cache_path: str, description: str) -> torch.Tensor:
        """
        Função helper: Tenta carregar embeddings do cache. Se não conseguir,
        calcula e salva no cache.
        """
        if not texts:
            self.log(f"Aviso: Nenhuma entrada de texto para embeddings de '{description}'.")
            return torch.tensor([]) # Retorna tensor vazio

        try:
            if os.path.exists(cache_path):
                self.log(f"Carregando embeddings de '{description}' do cache: {cache_path}")
                with open(cache_path, 'rb') as f:
                    embeddings = pickle.load(f)
                self.log(f"✅ Embeddings de '{description}' carregados.")
                return embeddings
        except Exception as e:
            self.log(f"AVISO: Falha ao ler cache '{cache_path}': {e}. Recalculando.")

        # --- Se o cache falhou ou não existe ---
        self.log(f"Calculando embeddings para {len(texts)} {description} (Isso só acontece 1 vez)...")
        
        # Move para CPU antes de salvar, para compatibilidade
        embeddings = self.model.encode(
            texts, 
            convert_to_tensor=True, 
            show_progress_bar=True # Mostra barra de progresso no console
        ).cpu() 
        
        self.log(f"✅ Cálculo de '{description}' concluído.")
        
        # Salva o novo cache
        self._save_embeddings(embeddings, cache_path)
        
        # Retorna o embedding (movido para o dispositivo correto)
        return embeddings.to(self.device)

    def _save_embeddings(self, data: Any, cache_path: str):
        """Salva os dados de embedding em um arquivo pickle."""
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            self.log(f"Salvando embeddings no cache: {cache_path}")
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            self.log("✅ Cache salvo.")
        except Exception as e:
            self.log(f"❌ ERRO CRÍTICO ao salvar cache em '{cache_path}': {e}")


    def _find_best_match(self, query_embedding: torch.Tensor, candidate_embeddings: torch.Tensor, candidates: List[str], threshold: float) -> (str, float):
        """Helper para encontrar o melhor match (1) de um query contra um conjunto."""
        if not candidates or candidate_embeddings.nelement() == 0:
            return None, 0.0
            
        cos_scores = util.cos_sim(query_embedding, candidate_embeddings)[0]
        best_match_idx = torch.argmax(cos_scores)
        best_score = cos_scores[best_match_idx].item()
        
        if best_score >= threshold:
            return candidates[best_match_idx], best_score
        return None, best_score

    def find_best_matches_hierarquico_batch(self, 
                                            query_texts: List[str], 
                                            top_k_assuntos: int = 2,
                                            threshold_materia: float = 0.85,
                                            threshold_assunto: float = 0.80,
                                            threshold_fallback: float = 0.82) -> List[List[str]]:
        """
        Processa uma lista de aulas (batch) usando a lógica hierárquica.
        """
        self.log(f"Iniciando Mapeamento Hierárquico em Lote para {len(query_texts)} aulas...")
        
        # 1. Codifica todas as aulas (queries) de uma vez
        query_embeddings = self.model.encode(
            query_texts, 
            convert_to_tensor=True, 
            show_progress_bar=True,
            device=self.device
        )
        
        lista_de_resultados = []

        # 2. Itera sobre os resultados (em memória, super rápido)
        for i, (query_text, query_emb) in enumerate(zip(query_texts, query_embeddings)):
            self.log(f"\n  Analisando Aula: '{query_text[:60]}...'")
            
            # --- Passo 1: Encontrar a melhor MATÉRIA ---
            best_materia, materia_score = self._find_best_match(
                query_emb, self.materias_embeddings, self.lista_materias, threshold_materia
            )
            
            if not best_materia:
                self.log(f"    Passo 1 (Matéria): Nenhuma matéria principal encontrada (Score < {threshold_materia}).")
                # Pula para o Fallback
                pass
            else:
                self.log(f"    Passo 1 (Matéria): '{best_materia}' (Score: {materia_score:.2f})")
                
                # --- Passo 2: Encontrar os melhores ASSUNTOS dentro da matéria ---
                assuntos_da_materia = self.dict_assuntos_por_materia.get(best_materia, [])
                assuntos_emb_da_materia = self.assuntos_embeddings_por_materia.get(best_materia)

                if assuntos_da_materia and assuntos_emb_da_materia is not None:
                    
                    cos_scores_assuntos = util.cos_sim(query_emb, assuntos_emb_da_materia)[0]
                    top_k_assuntos_idx = torch.topk(cos_scores_assuntos, k=min(top_k_assuntos, len(assuntos_da_materia)))

                    matches_assuntos = []
                    for score, idx in zip(top_k_assuntos_idx.values, top_k_assuntos_idx.indices):
                        score_item = score.item()
                        if score_item >= threshold_assunto:
                            assunto_encontrado = assuntos_da_materia[idx]
                            matches_assuntos.append(assunto_encontrado)
                            self.log(f"    Passo 2 (Assunto): '{assunto_encontrado}' (Score: {score_item:.2f})")
                    
                    if matches_assuntos:
                        lista_de_resultados.append(matches_assuntos)
                        continue # Achou! Próxima aula.

                self.log(f"    Passo 2 (Assunto): Nenhum assunto específico encontrado (Score < {threshold_assunto}).")

            # --- Passo 3: FALLBACK (Se Passo 1 ou 2 falharem) ---
            # Procura na lista completa de 13.496 assuntos
            self.log(f"    Passo 3 (Fallback): Procurando na lista completa...")
            
            cos_scores_fallback = util.cos_sim(query_emb, self.fallback_embeddings)[0]
            top_k_fallback_idx = torch.topk(cos_scores_fallback, k=min(top_k_assuntos, len(self.lista_completa_fallback)))
            
            matches_fallback = []
            for score, idx in zip(top_k_fallback_idx.values, top_k_fallback_idx.indices):
                score_item = score.item()
                if score_item >= threshold_fallback:
                    assunto_encontrado = self.lista_completa_fallback[idx]
                    matches_fallback.append(assunto_encontrado)
                    self.log(f"    Passo 3 (Fallback): '{assunto_encontrado}' (Score: {score_item:.2f})")
            
            if not matches_fallback:
                self.log(f"    Passo 3 (Fallback): Nenhum match encontrado.")

            lista_de_resultados.append(matches_fallback) # Adiciona (mesmo que vazio)

        return lista_de_resultados