# src/cache_manager.py
import os
import json
from typing import Callable, Dict, Any, List

CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "matches_cache.json")

class CacheManager:
    def __init__(self, log_callback: Callable[..., None]):
        self.log = log_callback
        # Estrutura interna agora terá metadados
        self.cache_structure: Dict[str, Any] = {
            "meta": {"course_id": None},
            "data": {}
        }
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
                    loaded = json.load(f)
                    # Migração simples para estrutura nova se for arquivo antigo
                    if "meta" not in loaded:
                        self.cache_structure["data"] = loaded
                    else:
                        self.cache_structure = loaded
            else:
                self.reset_cache()
        except Exception as e:
            self.log(f"⚠️ Erro ao ler cache: {e}")
            self.reset_cache()

    def reset_cache(self):
        self.cache_structure = {"meta": {"course_id": None}, "data": {}}
        self.has_changed = True

    def get_course_id(self) -> str | None:
        return self.cache_structure["meta"].get("course_id")

    def set_course_id(self, course_id: str):
        if self.get_course_id() != course_id:
            self.cache_structure["meta"]["course_id"] = course_id
            self.has_changed = True

    def get(self, key: str) -> List[str] | None:
        return self.cache_structure["data"].get(key)

    def set(self, key: str, value: List[str]):
        if self.cache_structure["data"].get(key) != value:
            self.cache_structure["data"][key] = value
            self.has_changed = True

    def get_all_tasks_formatted(self) -> List[Dict]:
        """Retorna tarefas formatadas para o Orchestrator (TEC)"""
        tarefas = []
        data = self.cache_structure["data"]
        if not data:
            return []
            
        for aula, filtros in data.items():
            tarefas.append({
                "nome_caderno": f"Caderno - {aula}",
                "materias": filtros,
                "mapeado": bool(filtros)
            })
        return tarefas

    def save_cache(self):
        if not self.has_changed:
            return

        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache_structure, f, indent=4, ensure_ascii=False)
            self.has_changed = False
        except Exception as e:
            self.log(f"❌ Erro ao salvar cache: {e}")