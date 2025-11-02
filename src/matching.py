# src/matching.py (VERSÃO COM SENTENCE TRANSFORMERS E LOGGING)

from sentence_transformers import SentenceTransformer, util
import torch
from typing import List, Callable

class TextMatcher:
    """
    Usa IA para encontrar as melhores correspondências semânticas entre
    o título de uma aula e uma lista de filtros disponíveis.
    Reporta o progresso via log_callback.
    """
    def __init__(self, log_callback: Callable[..., None], model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        """
        Inicializa o matcher e carrega o modelo de IA.
        
        Args:
            log_callback (Callable): Função da GUI para enviar mensagens de log.
            model_name (str): Nome do modelo do SentenceTransformer.
        """
        self.log = log_callback
        self.log(f"Carregando modelo de IA '{model_name}'. Isso pode levar um momento...")
        
        try:
            self.model = SentenceTransformer(model_name)
            self.log("✅ Modelo de IA carregado com sucesso.")
        except Exception as e:
            self.log(f"❌ ERRO CRÍTICO: Falha ao carregar o modelo de IA '{model_name}'.")
            self.log(f"Detalhes do erro: {e}")
            self.log("Verifique sua conexão com a internet ou o nome do modelo.")
            # Re-lança a exceção para parar a execução no Orquestrador
            raise

    def find_best_matches(self, query_text: str, candidates: List[str], top_k: int = 2, threshold: float = 0.5) -> List[str]:
        """
        Encontra as melhores correspondências para um texto dentro de uma lista de candidatos.

        Args:
            query_text (str): O título da aula a ser analisado.
            candidates (list): A lista completa de filtros do TEC.
            top_k (int): O número máximo de correspondências a retornar.
            threshold (float): A pontuação mínima de similaridade (de 0 a 1).

        Returns:
            list: Uma lista com os melhores filtros correspondentes.
        """
        if not candidates:
            return []

        try:
            # Converte os textos em vetores matemáticos (embeddings)
            query_embedding = self.model.encode(query_text, convert_to_tensor=True)
            candidate_embeddings = self.model.encode(candidates, convert_to_tensor=True)

            # Calcula a similaridade de cosseno
            cosine_scores = util.cos_sim(query_embedding, candidate_embeddings)

            # Encontra os 'top_k' melhores resultados
            top_results = torch.topk(cosine_scores, k=min(top_k, len(candidates)), dim=-1)

            matches = []
            for score, idx in zip(top_results[0][0], top_results[1][0]):
                if score >= threshold:
                    filtro = candidates[idx]
                    matches.append(filtro)
                    self.log(f"    → {filtro} (Score: {score:.2f})")
            
            if not matches:
                self.log(f"    ⚠️ Aviso: Nenhum filtro com similaridade > {threshold} encontrado para '{query_text}'.")
                # Fallback simples: busca por palavra-chave
                query_lower = query_text.lower()
                for candidate in candidates:
                    if candidate.lower() in query_lower:
                        matches.append(candidate)
                        self.log(f"    → (Fallback encontrou): {candidate}")
                        if len(matches) >= top_k:
                            break
            
            return matches
            
        except Exception as e:
            self.log(f"❌ Erro durante o matching de IA para '{query_text}': {e}")
            return []
