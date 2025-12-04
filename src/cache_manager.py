# Ficheiro: src/cache_manager.py
import os
import json
import traceback
from typing import Callable, Dict, Any, List

CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "matches_cache.json")

class CacheManager:
    """
    Gerencia o cache de resultados de match (Aula -> Filtros).
    """
    
    def __init__(self, log_callback: Callable[..., None]):
        self.log = log_callback
        self.cache_data: Dict[str, List[str]] = {}
        self.has_changed: bool = False

        try:
            if not os.path.exists(CACHE_DIR):
                os.makedirs(CACHE_DIR)
        except Exception as e:
            self.log(f"⚠️ Aviso: Não foi possível criar diretório cache: {e}")
            
        self._load_cache()

    def _load_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
            else:
                self.cache_data = {}
        except Exception as e:
            self.log(f"⚠️ Erro ao ler cache: {e}")
            self.cache_data = {}

    def get(self, key: str) -> List[str] | None:
        return self.cache_data.get(key)

    def set(self, key: str, value: List[str]):
        if self.cache_data.get(key) != value:
            self.cache_data[key] = value
            self.has_changed = True

    # --- NOVO MÉTODO PARA O FLUXO OTIMIZADO ---
    def get_all_tasks_formatted(self) -> List[Dict]:
        """
        Retorna todo o cache formatado como lista de tarefas para o Orquestrador.
        Isso permite pular a etapa do Backoffice.
        """
        tarefas = []
        if not self.cache_data:
            return []
            
        for aula, filtros in self.cache_data.items():
            tarefas.append({
                "nome_caderno": f"Caderno - {aula}",
                "materias": filtros,
                "mapeado": bool(filtros)
            })
        return tarefas

    def clear_cache(self):
        """Limpa o cache atual (útil ao iniciar nova revisão)"""
        self.cache_data = {}
        self.has_changed = True
        self.save_cache()

    def save_cache(self):
        if not self.has_changed:
            return

        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=4, ensure_ascii=False)
            self.has_changed = False
        except Exception as e:
            self.log(f"❌ Erro ao salvar cache: {e}")