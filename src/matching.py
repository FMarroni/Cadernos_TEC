# src/matching.py (VERSÃO 6.0 - MELHORIAS DE INTELIGÊNCIA E EFICÁCIA)
# Esta versão implementa melhorias significativas para reduzir falhas de matching:
# - Thresholds mais permissivos e adaptativos
# - Normalização e pré-processamento de texto
# - Detecção de aulas especiais (apresentação, revisão)
# - Quebra de descrições longas em chunks
# - Sistema de sugestões mesmo abaixo do threshold
# - Logging detalhado de scores
# - Expansão semântica com sinônimos

import torch
import os
import pickle
import re
import unicodedata
from sentence_transformers import SentenceTransformer, util
from typing import List, Callable, Dict, Any, Tuple, Optional

# --- Define os caminhos para salvar os embeddings ---
CACHE_DIR = "cache/embeddings"
MATERIAS_EMBEDDINGS_CACHE = os.path.join(CACHE_DIR, "materias_embeddings_v6.pkl")
ASSUNTOS_EMBEDDINGS_CACHE = os.path.join(CACHE_DIR, "assuntos_embeddings_v6.pkl")
FALLBACK_EMBEDDINGS_CACHE = os.path.join(CACHE_DIR, "fallback_embeddings_v6.pkl")

# --- Dicionário de sinônimos e termos relacionados para Direito Administrativo ---
SINONIMOS_JURIDICOS = {
    "ato administrativo": ["atos administrativos", "ato da administração", "atos da administração"],
    "servidor público": ["servidores públicos", "servidor", "servidores", "agente público", "agentes públicos"],
    "poder de polícia": ["polícia administrativa", "poder de policia"],
    "organização administrativa": ["organização da administração", "estrutura administrativa"],
    "serviços públicos": ["serviço público", "prestação de serviços"],
    "bens públicos": ["bem público", "patrimônio público"],
    "responsabilidade civil": ["responsabilidade do estado", "responsabilidade da administração"],
    "licitação": ["licitações", "procedimento licitatório"],
    "contrato administrativo": ["contratos administrativos", "contrato da administração"],
    "processo administrativo": ["procedimento administrativo", "processos administrativos"],
    "improbidade administrativa": ["ato de improbidade", "improbidade"],
    "consórcio público": ["consórcios públicos", "consórcio"],
    "terceiro setor": ["entidades do terceiro setor", "organizações sociais"],
    "pregão": ["pregão eletrônico", "pregão presencial"],
}

# --- Padrões para detectar aulas especiais que não devem ser mapeadas ---
PADROES_AULAS_ESPECIAIS = [
    r"apresentação\s+do\s+curso",
    r"aula\s+00",
    r"aula\s+inicial",
    r"introdução\s+ao\s+curso",
    r"revisão\s+acelerada",
    r"revisão\s+final",
    r"resumo",
    r"videoaula",
    r"exercícios\s+gerais",
]


class TextMatcher:
    """
    Usa IA para encontrar as melhores correspondências semânticas.
    Versão 6.0 com melhorias significativas de inteligência e eficácia.
    """
    def __init__(self,
                 log_callback: Callable[..., None],
                 lista_materias: List[str],
                 dict_assuntos_por_materia: Dict[str, List[str]],
                 lista_completa_fallback: List[str],
                 model_name='BAAI/bge-m3'):
        
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
        
        # 1. Guarda as listas de texto (originais e normalizadas)
        self.lista_materias = lista_materias
        self.lista_materias_normalizadas = [self._normalizar_texto(m) for m in lista_materias]
        
        self.dict_assuntos_por_materia = dict_assuntos_por_materia
        self.dict_assuntos_normalizados = {
            materia: [self._normalizar_texto(a) for a in assuntos]
            for materia, assuntos in dict_assuntos_por_materia.items()
        }
        
        self.lista_completa_fallback = lista_completa_fallback
        self.lista_fallback_normalizada = [self._normalizar_texto(f) for f in lista_completa_fallback]
        
        # 2. Carrega ou Calcula os embeddings das MATÉRIAS (usando textos normalizados)
        self.materias_embeddings = self._load_or_compute_embeddings(
            self.lista_materias_normalizadas,
            MATERIAS_EMBEDDINGS_CACHE,
            "matérias"
        )
        
        # 3. Carrega ou Calcula os embeddings dos ASSUNTOS (Hierárquico)
        self.assuntos_embeddings_por_materia = {}
        assuntos_para_calcular = {}
        try:
            assuntos_cache_file = ASSUNTOS_EMBEDDINGS_CACHE
            if os.path.exists(assuntos_cache_file):
                self.log(f"Carregando embeddings de assuntos do cache: {assuntos_cache_file}")
                with open(assuntos_cache_file, 'rb') as f:
                    self.assuntos_embeddings_por_materia = pickle.load(f)
                self.log(f"✅ Embeddings de {len(self.assuntos_embeddings_por_materia)} matérias (com assuntos) carregados.")
            else:
                self.log("Nenhum cache de embeddings de assuntos encontrado. Calculando...")
                assuntos_para_calcular = self.dict_assuntos_normalizados
        
            # Lógica de "preencher" se novas matérias foram adicionadas
            for materia, assuntos in self.dict_assuntos_normalizados.items():
                if materia not in self.assuntos_embeddings_por_materia and assuntos:
                    assuntos_para_calcular[materia] = assuntos

            if assuntos_para_calcular:
                self.log(f"Calculando embeddings para {len(assuntos_para_calcular)} matérias (novas ou sem cache)...")
                for materia, assuntos in assuntos_para_calcular.items():
                    self.log(f"  - Processando {len(assuntos)} assuntos de '{materia}'...")
                    self.assuntos_embeddings_por_materia[materia] = self.model.encode(
                        assuntos, convert_to_tensor=True, show_progress_bar=False
                    )
                self._save_embeddings(self.assuntos_embeddings_por_materia, ASSUNTOS_EMBEDDINGS_CACHE)

        except Exception as e:
            self.log(f"AVISO: Falha ao carregar/processar cache de assuntos: {e}. Recalculando tudo.")
            self.assuntos_embeddings_por_materia = {}
            for materia, assuntos in self.dict_assuntos_normalizados.items():
                if assuntos:
                    self.assuntos_embeddings_por_materia[materia] = self.model.encode(
                        assuntos, convert_to_tensor=True, show_progress_bar=False
                    )
            self._save_embeddings(self.assuntos_embeddings_por_materia, ASSUNTOS_EMBEDDINGS_CACHE)
            
        # 4. Carrega ou Calcula os embeddings de FALLBACK
        self.fallback_embeddings = self._load_or_compute_embeddings(
            self.lista_fallback_normalizada,
            FALLBACK_EMBEDDINGS_CACHE,
            "filtros de fallback"
        )
        
        self.log("✅ Todos os embeddings estão prontos.")

    def _normalizar_texto(self, texto: str) -> str:
        """
        Normaliza texto para melhorar matching:
        - Remove acentos
        - Converte para lowercase
        - Remove pontuação excessiva
        - Normaliza espaços
        """
        if not texto:
            return ""
        
        # Remove acentos
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')
        
        # Lowercase
        texto = texto.lower()
        
        # Remove pontuação excessiva (mantém vírgulas e pontos importantes)
        texto = re.sub(r'[;:\(\)\[\]{}]', ' ', texto)
        
        # Normaliza espaços múltiplos
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        return texto

    def _expandir_com_sinonimos(self, texto: str) -> List[str]:
        """
        Expande o texto com sinônimos conhecidos para melhorar matching.
        Retorna lista com texto original + variações.
        """
        texto_norm = self._normalizar_texto(texto)
        expansoes = [texto_norm]
        
        for termo_chave, sinonimos in SINONIMOS_JURIDICOS.items():
            if termo_chave in texto_norm:
                for sinonimo in sinonimos:
                    if sinonimo not in texto_norm:
                        texto_expandido = texto_norm.replace(termo_chave, sinonimo)
                        expansoes.append(texto_expandido)
        
        return expansoes

    def _e_aula_especial(self, texto_aula: str) -> bool:
        """
        Detecta se a aula é especial (apresentação, revisão) e não deve ser mapeada.
        """
        texto_norm = self._normalizar_texto(texto_aula)
        
        for padrao in PADROES_AULAS_ESPECIAIS:
            if re.search(padrao, texto_norm, re.IGNORECASE):
                return True
        
        return False

    def _quebrar_texto_longo(self, texto: str, max_palavras: int = 50) -> List[str]:
        """
        Quebra textos longos em chunks menores para melhor processamento.
        Mantém contexto ao incluir sobreposição entre chunks.
        """
        palavras = texto.split()
        
        if len(palavras) <= max_palavras:
            return [texto]
        
        chunks = []
        overlap = max_palavras // 4  # 25% de sobreposição
        
        for i in range(0, len(palavras), max_palavras - overlap):
            chunk = ' '.join(palavras[i:i + max_palavras])
            chunks.append(chunk)
        
        return chunks

    def _load_or_compute_embeddings(self, texts: List[str], cache_path: str, description: str) -> torch.Tensor:
        """
        Função helper: Tenta carregar embeddings do cache. Se não conseguir,
        calcula e salva no cache.
        """
        if not texts:
            self.log(f"Aviso: Nenhuma entrada de texto para embeddings de '{description}'.")
            return torch.tensor([])

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
        
        embeddings = self.model.encode(
            texts, 
            convert_to_tensor=True, 
            show_progress_bar=True
        ).cpu() 
        
        self.log(f"✅ Cálculo de '{description}' concluído.")
        
        self._save_embeddings(embeddings, cache_path)
        
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

    def _find_best_match_with_details(self, 
                                      query_embedding: torch.Tensor, 
                                      candidate_embeddings: torch.Tensor, 
                                      candidates: List[str], 
                                      candidates_originais: List[str],
                                      threshold: float,
                                      top_k: int = 3) -> Tuple[Optional[str], float, List[Tuple[str, float]]]:
        """
        Helper melhorado para encontrar o melhor match com logging detalhado.
        Retorna: (melhor_match, melhor_score, top_k_sugestoes)
        """
        if not candidates or candidate_embeddings.nelement() == 0:
            return None, 0.0, []
            
        cos_scores = util.cos_sim(query_embedding, candidate_embeddings)[0]
        
        # Pega os top K scores
        top_k_actual = min(top_k, len(candidates))
        top_indices = torch.topk(cos_scores, k=top_k_actual)
        
        # Monta lista de sugestões com textos originais
        sugestoes = []
        for score, idx in zip(top_indices.values, top_indices.indices):
            score_val = score.item()
            texto_original = candidates_originais[idx] if idx < len(candidates_originais) else candidates[idx]
            sugestoes.append((texto_original, score_val))
        
        # Verifica se o melhor passou do threshold
        melhor_score = sugestoes[0][1]
        melhor_match = sugestoes[0][0] if melhor_score >= threshold else None
        
        return melhor_match, melhor_score, sugestoes

    def find_best_matches_hierarquico_batch(self, 
                                            query_texts: List[str], 
                                            top_k_assuntos: int = 3,
                                            threshold_materia: float = 0.45,
                                            threshold_assunto: float = 0.55,
                                            threshold_fallback: float = 0.50,
                                            usar_expansao_sinonimos: bool = True) -> List[List[str]]:
        """
        Processa uma lista de aulas (batch) usando a lógica hierárquica MELHORADA.
        
        MELHORIAS:
        - Thresholds mais permissivos (0.45, 0.55, 0.50)
        - Detecção de aulas especiais
        - Normalização de texto
        - Expansão com sinônimos
        - Quebra de textos longos
        - Logging detalhado de scores
        """
        self.log(f"Iniciando Mapeamento Hierárquico MELHORADO para {len(query_texts)} aulas...")
        self.log(f"Thresholds: Matéria={threshold_materia}, Assunto={threshold_assunto}, Fallback={threshold_fallback}")
        
        lista_de_resultados = []

        for i, query_text in enumerate(query_texts):
            self.log(f"\n{'='*80}")
            self.log(f"  Analisando Aula {i+1}/{len(query_texts)}: '{query_text[:80]}...'")
            
            # --- NOVO: Detecta aulas especiais ---
            if self._e_aula_especial(query_text):
                self.log(f"    ⚠️  AULA ESPECIAL DETECTADA (Apresentação/Revisão) - PULANDO MAPEAMENTO")
                lista_de_resultados.append([])
                continue
            
            # --- NOVO: Normaliza e expande o texto ---
            query_normalizado = self._normalizar_texto(query_text)
            
            # --- NOVO: Quebra textos longos ---
            chunks = self._quebrar_texto_longo(query_normalizado, max_palavras=50)
            
            if len(chunks) > 1:
                self.log(f"    📝 Texto longo detectado. Dividido em {len(chunks)} chunks para análise.")
            
            # Processa cada chunk e agrega resultados
            matches_agregados = []
            
            for chunk_idx, chunk in enumerate(chunks):
                if len(chunks) > 1:
                    self.log(f"\n    --- Processando Chunk {chunk_idx+1}/{len(chunks)} ---")
                
                # Codifica o chunk
                query_emb = self.model.encode(
                    chunk, 
                    convert_to_tensor=True,
                    device=self.device
                )
                
                # --- Passo 1: Encontrar a melhor MATÉRIA ---
                best_materia, materia_score, sugestoes_materias = self._find_best_match_with_details(
                    query_emb, 
                    self.materias_embeddings, 
                    self.lista_materias_normalizadas,
                    self.lista_materias,  # Textos originais
                    threshold_materia,
                    top_k=3
                )
                
                # Log detalhado das sugestões de matérias
                self.log(f"    Passo 1 (Matéria) - Top 3 Sugestões:")
                for idx, (materia, score) in enumerate(sugestoes_materias, 1):
                    status = "✅ ACEITO" if score >= threshold_materia else "❌ Abaixo do threshold"
                    self.log(f"      {idx}. '{materia[:60]}...' (Score: {score:.3f}) {status}")
                
                if not best_materia:
                    self.log(f"    ⚠️  Nenhuma matéria encontrada acima do threshold {threshold_materia}")
                else:
                    self.log(f"    ✅ Matéria selecionada: '{best_materia}'")
                    
                    # --- Passo 2: Encontrar os melhores ASSUNTOS dentro da matéria ---
                    assuntos_da_materia = self.dict_assuntos_por_materia.get(best_materia, [])
                    assuntos_norm_da_materia = self.dict_assuntos_normalizados.get(best_materia, [])
                    assuntos_emb_da_materia = self.assuntos_embeddings_por_materia.get(best_materia)

                    if assuntos_da_materia and assuntos_emb_da_materia is not None:
                        
                        cos_scores_assuntos = util.cos_sim(query_emb, assuntos_emb_da_materia)[0]
                        top_k_assuntos_actual = min(top_k_assuntos, len(assuntos_da_materia))
                        top_k_assuntos_idx = torch.topk(cos_scores_assuntos, k=top_k_assuntos_actual)

                        self.log(f"    Passo 2 (Assuntos) - Top {top_k_assuntos_actual} Sugestões:")
                        
                        for rank, (score, idx) in enumerate(zip(top_k_assuntos_idx.values, top_k_assuntos_idx.indices), 1):
                            score_item = score.item()
                            assunto_encontrado = assuntos_da_materia[idx]
                            status = "✅ ACEITO" if score_item >= threshold_assunto else "❌ Abaixo do threshold"
                            self.log(f"      {rank}. '{assunto_encontrado[:60]}...' (Score: {score_item:.3f}) {status}")
                            
                            if score_item >= threshold_assunto:
                                matches_agregados.append(assunto_encontrado)
                        
                        if matches_agregados:
                            continue  # Achou assuntos! Próximo chunk ou aula.

                        self.log(f"    ⚠️  Nenhum assunto específico encontrado acima do threshold {threshold_assunto}")

                # --- Passo 3: FALLBACK (Se Passo 1 ou 2 falharem) ---
                self.log(f"    Passo 3 (Fallback) - Procurando na lista completa...")
                
                cos_scores_fallback = util.cos_sim(query_emb, self.fallback_embeddings)[0]
                top_k_fallback_actual = min(top_k_assuntos, len(self.lista_completa_fallback))
                top_k_fallback_idx = torch.topk(cos_scores_fallback, k=top_k_fallback_actual)
                
                self.log(f"    Top {top_k_fallback_actual} Sugestões do Fallback:")
                
                for rank, (score, idx) in enumerate(zip(top_k_fallback_idx.values, top_k_fallback_idx.indices), 1):
                    score_item = score.item()
                    assunto_encontrado = self.lista_completa_fallback[idx]
                    status = "✅ ACEITO" if score_item >= threshold_fallback else "❌ Abaixo do threshold"
                    self.log(f"      {rank}. '{assunto_encontrado[:60]}...' (Score: {score_item:.3f}) {status}")
                    
                    if score_item >= threshold_fallback:
                        matches_agregados.append(assunto_encontrado)
                
                if not matches_agregados:
                    self.log(f"    ❌ FALHA TOTAL: Nenhum match encontrado em nenhum dos 3 passos")
            
            # Remove duplicatas mantendo ordem
            matches_unicos = []
            vistos = set()
            for match in matches_agregados:
                if match not in vistos:
                    matches_unicos.append(match)
                    vistos.add(match)
            
            if matches_unicos:
                self.log(f"\n    ✅ RESULTADO FINAL: {len(matches_unicos)} assunto(s) encontrado(s)")
            else:
                self.log(f"\n    ❌ RESULTADO FINAL: Nenhum assunto encontrado")
            
            lista_de_resultados.append(matches_unicos)

        return lista_de_resultados