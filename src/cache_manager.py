# Ficheiro: src/cache_manager.py
# (VERSÃO 3 - Adicionadas as funções get, set, e save_cache)

import os
import json
import traceback
from typing import Callable, Dict, Any, List

CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "matches_cache.json")

class CacheManager:
    """
    Gerencia o cache de resultados de match (Aula -> Filtros) 
    em um arquivo JSON.
    """
    
    def __init__(self, log_callback: Callable[..., None]):
        """
        Inicializa o gerenciador e carrega o cache existente.
        """
        self.log = log_callback
        self.cache_data: Dict[str, List[str]] = {}
        self.has_changed: bool = False # Flag para saber se precisa salvar

        # Garante que o diretório de cache exista
        try:
            if not os.path.exists(CACHE_DIR):
                os.makedirs(CACHE_DIR)
                self.log(f"Diretório de cache criado em: {CACHE_DIR}")
        except Exception as e:
            self.log(f"⚠️ Aviso: Não foi possível criar o diretório de cache: {e}")
            
        self._load_cache()

    def _load_cache(self):
        """Carrega o arquivo de cache JSON para a memória."""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
                self.log(f"✅ Cache carregado. {len(self.cache_data)} aulas em memória.")
            else:
                self.log("Nenhum arquivo de cache encontrado. Um novo será criado.")
        except json.JSONDecodeError:
            self.log(f"⚠️ Aviso: Arquivo de cache '{CACHE_FILE}' corrompido. Ignorando cache.")
            self.cache_data = {}
        except Exception as e:
            self.log(f"⚠️ Aviso: Não foi possível ler o arquivo de cache: {e}")
            self.cache_data = {}

    # --- FUNÇÃO QUE FALTAVA (GET) ---
    def get(self, key: str) -> List[str] | None:
        """
        Busca um resultado de match no cache.
        Retorna a lista de filtros ou None se não encontrado.
        """
        return self.cache_data.get(key)

    # --- FUNÇÃO QUE FALTAVA (SET) ---
    def set(self, key: str, value: List[str]):
        """
        Adiciona ou atualiza um resultado no cache em memória.
        """
        # Só atualiza se o valor for diferente
        if self.cache_data.get(key) != value:
            self.cache_data[key] = value
            self.has_changed = True
            self.log(f"  [Cache SET] Novo resultado para '{key[:60]}...' foi salvo na memória.")

    # --- FUNÇÃO QUE FALTAVA (SAVE) ---
    def save_cache(self):
        """
        Salva o cache (se houver mudanças) no arquivo JSON.
        """
        if not self.has_changed:
            self.log("Cache sem alterações, não é preciso salvar.")
            return

        self.log(f"Salvando {len(self.cache_data)} itens no cache em {CACHE_FILE}...")
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=4, ensure_ascii=False)
            self.log("✅ Cache salvo no disco.")
            self.has_changed = False # Reseta a flag
        except Exception as e:
            self.log(f"❌ ERRO CRÍTICO ao salvar cache: {e}")
            self.log(traceback.format_exc())