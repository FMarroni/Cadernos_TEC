import torch
import os
import pickle
import re
import unicodedata
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Any, Union

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
        
        try:
            self.model = SentenceTransformer(model_name, device=self.device)
        except Exception as e:
            self.log(f"❌ Erro ao carregar IA: {e}")
            raise

        self.lista_materias = lista_materias
        self.lista_materias_normalizadas = [self._normalizar_texto(m) for m in lista_materias]
        self.dict_assuntos_por_materia = dict_assuntos_por_materia
        self.dict_assuntos_normalizados = {m: [self._normalizar_texto(a) for a in l] for m, l in dict_assuntos_por_materia.items()}
        self.lista_completa_fallback = lista_completa_fallback
        self.lista_fallback_normalizada = [self._normalizar_texto(f) for f in lista_completa_fallback]

        self.materias_embeddings = self._load_or_compute_embeddings(self.lista_materias_normalizadas, MATERIAS_EMBEDDINGS_CACHE, "matérias")
        self.assuntos_embeddings_por_materia = {}
        self._carregar_cache_assuntos()
        self.fallback_embeddings = self._load_or_compute_embeddings(self.lista_fallback_normalizada, FALLBACK_EMBEDDINGS_CACHE, "fallback")

    def find_best_matches_filtered_batch(self, query_texts: List[str], target_materia: Union[str, List[str]], top_k_assuntos: int = 3, threshold_assunto: float = 0.60) -> List[List[Dict[str, Any]]]:
        """
        Retorna lista de listas contendo dicts: {'termo': str, 'score': float, 'origem': str}
        Suporta String única ou Lista de Strings para target_materia.
        Concatena embeddings de múltiplas matérias para busca unificada.
        """
        
        # 1. Normalização: Garante que target_materia seja sempre uma lista
        materias_alvo = []
        if isinstance(target_materia, list):
            materias_alvo = target_materia
        elif target_materia:
            materias_alvo = [target_materia]

        # 2. Coleta de dados (Tensores e Textos) das matérias solicitadas
        tensors_to_cat = []
        texts_to_cat = []

        for materia in materias_alvo:
            # Verifica se a matéria existe nos dicionários carregados
            if materia in self.dict_assuntos_por_materia and materia in self.assuntos_embeddings_por_materia:
                emb = self.assuntos_embeddings_por_materia[materia]
                txt = self.dict_assuntos_por_materia[materia]
                
                # Verifica integridade (se tem embedding e texto)
                if emb is not None and len(txt) > 0:
                    tensors_to_cat.append(emb)
                    texts_to_cat.extend(txt)
        
        # 3. Fallback se nenhuma matéria válida for encontrada
        if not tensors_to_cat:
            # Se a lista estiver vazia ou as matérias não existirem, tenta o hierárquico
            return self.find_best_matches_hierarquico_batch(query_texts)

        # 4. Concatenação dos Embeddings
        try:
            # Junta todos os tensores das matérias selecionadas em um único tensor grande
            assuntos_emb = torch.cat(tensors_to_cat, dim=0)
            assuntos_txt = texts_to_cat
        except Exception as e:
            self.log(f"❌ Erro ao concatenar embeddings para multiseleção: {e}")
            return [[] for _ in query_texts]

        # 5. Processamento das Queries
        lista_resultados = []
        
        for query in query_texts:
            if self._e_aula_especial(query):
                lista_resultados.append([])
                continue

            query_norm = self._normalizar_texto(query)
            chunks = self._quebrar_texto_longo(query_norm)
            matches_aula = [] # Lista de dicts

            for chunk in chunks:
                query_emb = self.model.encode(chunk, convert_to_tensor=True, device=self.device)
                
                # Compara contra o tensor unificado de todas as matérias selecionadas
                cos_scores = util.cos_sim(query_emb, assuntos_emb)[0]
                
                # Pega os Top K globais
                top_indices = torch.topk(cos_scores, k=min(top_k_assuntos, len(assuntos_txt)))
                
                for score, idx in zip(top_indices.values, top_indices.indices):
                    sc = score.item()
                    if sc >= threshold_assunto:
                        matches_aula.append({
                            "termo": assuntos_txt[idx.item()],
                            "score": sc,
                            "origem": "Filtro IA (Multi)"
                        })

            # Remove duplicatas mantendo a maior nota
            matches_aula = self._deduplicar_matches(matches_aula)
            lista_resultados.append(matches_aula)
            
        return lista_resultados

    def find_best_matches_hierarquico_batch(self, query_texts: List[str], top_k_assuntos: int = 3, threshold_materia: float = 0.55, threshold_assunto: float = 0.60, threshold_fallback: float = 0.60) -> List[List[Dict[str, Any]]]:
        lista_resultados = []
        
        for query in query_texts:
            if self._e_aula_especial(query):
                lista_resultados.append([])
                continue
                
            query_norm = self._normalizar_texto(query)
            matches_aula = []
            
            # 1. Tenta achar a matéria principal
            q_emb = self.model.encode(query_norm, convert_to_tensor=True, device=self.device)
            cos_mat = util.cos_sim(q_emb, self.materias_embeddings)[0]
            best_mat_idx = torch.argmax(cos_mat).item()
            best_mat_score = cos_mat[best_mat_idx].item()
            
            found_in_materia = False
            if best_mat_score >= threshold_materia:
                materia_nome = self.lista_materias[best_mat_idx]
                ass_emb = self.assuntos_embeddings_por_materia.get(materia_nome)
                ass_txt = self.dict_assuntos_por_materia.get(materia_nome, [])
                
                if ass_emb is not None:
                    cos_ass = util.cos_sim(q_emb, ass_emb)[0]
                    top_vals, top_idxs = torch.topk(cos_ass, k=min(top_k_assuntos, len(ass_txt)))
                    for s, i in zip(top_vals, top_idxs):
                        sc = s.item()
                        if sc >= threshold_assunto:
                            matches_aula.append({
                                "termo": ass_txt[i.item()],
                                "score": sc,
                                "origem": "Hierárquico"
                            })
                            found_in_materia = True
            
            # 2. Se não achou na matéria, tenta no geral (fallback)
            if not found_in_materia:
                cos_fall = util.cos_sim(q_emb, self.fallback_embeddings)[0]
                top_vals, top_idxs = torch.topk(cos_fall, k=min(top_k_assuntos, len(self.lista_completa_fallback)))
                for s, i in zip(top_vals, top_idxs):
                    sc = s.item()
                    if sc >= threshold_fallback:
                        matches_aula.append({
                            "termo": self.lista_completa_fallback[i.item()],
                            "score": sc,
                            "origem": "Fallback"
                        })
                        
            lista_resultados.append(self._deduplicar_matches(matches_aula))
            
        return lista_resultados

    def _deduplicar_matches(self, matches: List[Dict]) -> List[Dict]:
        """Remove duplicatas de termos mantendo o de maior score."""
        seen = {}
        for m in matches:
            t = m['termo']
            if t not in seen or m['score'] > seen[t]['score']:
                seen[t] = m
        return list(seen.values())

    # Utils
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