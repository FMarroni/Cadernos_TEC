# src/matching.py (VERSÃO 8.0 - ORIGINAL TURBINADO)
# Mantém a estrutura original mas adiciona os métodos de filtro por matéria.

import torch
import os
import pickle
import re
import unicodedata
from sentence_transformers import SentenceTransformer, util
from typing import List, Callable, Dict, Any, Tuple, Optional, Set

CACHE_DIR = "cache/embeddings"
MATERIAS_EMBEDDINGS_CACHE = os.path.join(CACHE_DIR, "materias_embeddings_v6.pkl")
ASSUNTOS_EMBEDDINGS_CACHE = os.path.join(CACHE_DIR, "assuntos_embeddings_v6.pkl")
FALLBACK_EMBEDDINGS_CACHE = os.path.join(CACHE_DIR, "fallback_embeddings_v6.pkl")

PADROES_AULAS_ESPECIAIS = [
    r"apresentação\s+do\s+curso", r"aula\s+00", r"aula\s+inicial",
    r"introdução\s+ao\s+curso", r"revisão\s+acelerada", r"revisão\s+final",
    r"resumo", r"videoaula", r"exercícios\s+gerais",
]

class TextMatcher:
    def __init__(self, log_callback, lista_materias, dict_assuntos_por_materia, lista_completa_fallback, model_name='BAAI/bge-m3'):
        self.log = log_callback
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.log(f"Usando dispositivo: {self.device} para IA.")

        try:
            self.model = SentenceTransformer(model_name, device=self.device)
        except Exception as e:
            self.log(f"❌ Erro ao carregar IA: {e}")
            raise

        # Inicialização de dados (igual ao original)
        self.lista_materias = lista_materias
        self.lista_materias_normalizadas = [self._normalizar_texto(m) for m in lista_materias]
        self.dict_assuntos_por_materia = dict_assuntos_por_materia
        self.dict_assuntos_normalizados = {m: [self._normalizar_texto(a) for a in l] for m, l in dict_assuntos_por_materia.items()}
        self.lista_completa_fallback = lista_completa_fallback
        self.lista_fallback_normalizada = [self._normalizar_texto(f) for f in lista_completa_fallback]

        # Embeddings
        self.materias_embeddings = self._load_or_compute_embeddings(self.lista_materias_normalizadas, MATERIAS_EMBEDDINGS_CACHE, "matérias")
        self.assuntos_embeddings_por_materia = {}
        self._carregar_cache_assuntos()
        self.fallback_embeddings = self._load_or_compute_embeddings(self.lista_fallback_normalizada, FALLBACK_EMBEDDINGS_CACHE, "fallback")

    # --- NOVO MÉTODO: Busca Filtrada (O que você pediu) ---
    def find_best_matches_filtered_batch(self, query_texts: List[str], target_materia: str, top_k_assuntos: int = 3, threshold_assunto: float = 0.60) -> List[List[str]]:
        """Busca assuntos APENAS dentro da matéria selecionada pelo usuário."""
        self.log(f"🎯 Mapeamento FOCADO na matéria: '{target_materia}'")
        
        # Valida se a matéria existe no banco
        if target_materia not in self.dict_assuntos_por_materia:
            self.log(f"⚠️ Matéria '{target_materia}' não encontrada no banco de dados (JSON). Usando busca padrão.")
            return self.find_best_matches_hierarquico_batch(query_texts) # Fallback para o método normal

        assuntos_emb = self.assuntos_embeddings_por_materia.get(target_materia)
        assuntos_txt = self.dict_assuntos_por_materia.get(target_materia, [])
        
        lista_resultados = []
        
        for query in query_texts:
            if self._e_aula_especial(query):
                lista_resultados.append([])
                continue

            query_norm = self._normalizar_texto(query)
            chunks = self._quebrar_texto_longo(query_norm)
            matches_aula = []

            for chunk in chunks:
                query_emb = self.model.encode(chunk, convert_to_tensor=True, device=self.device)
                
                # Busca direta nos embeddings daquela matéria
                cos_scores = util.cos_sim(query_emb, assuntos_emb)[0]
                top_indices = torch.topk(cos_scores, k=min(top_k_assuntos, len(assuntos_txt)))
                
                for score, idx in zip(top_indices.values, top_indices.indices):
                    if score.item() >= threshold_assunto:
                        matches_aula.append(assuntos_txt[idx.item()])

            # Deduplica
            lista_resultados.append(list(dict.fromkeys(matches_aula)))
            
        return lista_resultados

    # --- Método Original (Mantido para compatibilidade e modo automático) ---
    def find_best_matches_hierarquico_batch(self, query_texts: List[str], top_k_assuntos: int = 3, threshold_materia: float = 0.55, threshold_assunto: float = 0.60, threshold_fallback: float = 0.60) -> List[List[str]]:
        self.log("🤖 Mapeamento AUTOMÁTICO (Hierárquico)")
        lista_resultados = []
        
        for query in query_texts:
            if self._e_aula_especial(query):
                lista_resultados.append([])
                continue
                
            query_norm = self._normalizar_texto(query)
            matches_aula = []
            
            # 1. Tenta achar a matéria
            q_emb = self.model.encode(query_norm, convert_to_tensor=True, device=self.device)
            cos_mat = util.cos_sim(q_emb, self.materias_embeddings)[0]
            best_mat_idx = torch.argmax(cos_mat).item()
            best_mat_score = cos_mat[best_mat_idx].item()
            
            if best_mat_score >= threshold_materia:
                materia_nome = self.lista_materias[best_mat_idx]
                # 2. Busca assuntos na matéria
                ass_emb = self.assuntos_embeddings_por_materia.get(materia_nome)
                ass_txt = self.dict_assuntos_por_materia.get(materia_nome, [])
                if ass_emb is not None:
                    cos_ass = util.cos_sim(q_emb, ass_emb)[0]
                    top_vals, top_idxs = torch.topk(cos_ass, k=min(top_k_assuntos, len(ass_txt)))
                    for s, i in zip(top_vals, top_idxs):
                        if s.item() >= threshold_assunto:
                            matches_aula.append(ass_txt[i.item()])
            
            # 3. Fallback Global
            if not matches_aula:
                cos_fall = util.cos_sim(q_emb, self.fallback_embeddings)[0]
                top_vals, top_idxs = torch.topk(cos_fall, k=min(top_k_assuntos, len(self.lista_completa_fallback)))
                for s, i in zip(top_vals, top_idxs):
                    if s.item() >= threshold_fallback:
                        matches_aula.append(self.lista_completa_fallback[i.item()])
                        
            lista_resultados.append(list(dict.fromkeys(matches_aula)))
            
        return lista_resultados

    # Utils (Simplificados para economizar espaço, mas funcionais)
    def _normalizar_texto(self, t): return unicodedata.normalize('NFD', t).encode('ascii', 'ignore').decode('utf-8').lower() if t else ""
    def _e_aula_especial(self, t): return any(re.search(p, self._normalizar_texto(t), re.IGNORECASE) for p in PADROES_AULAS_ESPECIAIS)
    def _quebrar_texto_longo(self, t, m=50): w=t.split(); return [' '.join(w[i:i+m]) for i in range(0, len(w), m-m//4)] if len(w)>m else [t]
    
    def _load_or_compute_embeddings(self, texts, path, desc):
        if os.path.exists(path):
            with open(path, 'rb') as f: return pickle.load(f)
        self.log(f"Calculando embeddings para {desc}...")
        emb = self.model.encode(texts, convert_to_tensor=True, show_progress_bar=True).cpu()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f: pickle.dump(emb, f)
        return emb.to(self.device)

    def _carregar_cache_assuntos(self):
        if os.path.exists(ASSUNTOS_EMBEDDINGS_CACHE):
            with open(ASSUNTOS_EMBEDDINGS_CACHE, 'rb') as f: self.assuntos_embeddings_por_materia = pickle.load(f)
        else:
            for m, a in self.dict_assuntos_normalizados.items():
                if a: self.assuntos_embeddings_por_materia[m] = self.model.encode(a, convert_to_tensor=True, show_progress_bar=False)
            with open(ASSUNTOS_EMBEDDINGS_CACHE, 'wb') as f: pickle.dump(self.assuntos_embeddings_por_materia, f)