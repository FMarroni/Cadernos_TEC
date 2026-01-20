# src/cache_manager.py
import os
import json
from typing import Callable, Dict, Any, List, Optional

CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "matches_cache.json")

class CacheManager:
    def __init__(self, log_callback: Callable[..., None]):
        self.log = log_callback
        self.current_course_id: Optional[str] = None
        
        # Nova estrutura: suporta múltiplos cursos simultaneamente
        # { 
        #   "meta": { "last_accessed_id": "..." },
        #   "courses": { 
        #       "ID_DO_CURSO_1": { ... dados ... },
        #       "ID_DO_CURSO_2": { ... dados ... }
        #   }
        # }
        self.cache_structure: Dict[str, Any] = {
            "meta": {"last_accessed_id": None},
            "courses": {}
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
                    
                    # --- MIGRAÇÃO AUTOMÁTICA (Single Slot -> Multi Slot) ---
                    # Se for o formato antigo (sem a chave 'courses'), migramos
                    if "courses" not in loaded:
                        self.log("🔄 Migrando cache antigo para formato multi-curso...")
                        old_id = loaded.get("meta", {}).get("course_id")
                        old_data = loaded.get("data", {})
                        
                        self.cache_structure["courses"] = {}
                        if old_id and old_data:
                            self.cache_structure["courses"][old_id] = old_data
                            self.cache_structure["meta"]["last_accessed_id"] = old_id
                    else:
                        self.cache_structure = loaded
            else:
                self.reset_all_cache()
        except Exception as e:
            self.log(f"⚠️ Erro ao ler cache: {e}")
            self.reset_all_cache()

    def reset_all_cache(self):
        """Limpa TODOS os cursos (Hard Reset)"""
        self.cache_structure = {
            "meta": {"last_accessed_id": None}, 
            "courses": {}
        }
        self.has_changed = True

    def reset_current_course(self):
        """Limpa apenas os dados do curso atual selecionado"""
        if self.current_course_id and self.current_course_id in self.cache_structure["courses"]:
            del self.cache_structure["courses"][self.current_course_id]
            self.has_changed = True

    # Mantido para compatibilidade, mas agora apenas reseta o curso ATUAL
    def reset_cache(self):
        self.reset_current_course()

    def get_course_id(self) -> str | None:
        """Retorna o ID que está carregado no contexto atual"""
        return self.current_course_id

    def set_course_id(self, course_id: str):
        """Define qual curso estamos manipulando agora, sem apagar os outros"""
        if self.current_course_id != course_id:
            self.current_course_id = course_id
            self.cache_structure["meta"]["last_accessed_id"] = course_id
            
            # Garante que a chave existe no dicionário de cursos
            if course_id not in self.cache_structure["courses"]:
                self.cache_structure["courses"][course_id] = {}
            
            # Não marcamos has_changed aqui para evitar salvar apenas por troca de contexto,
            # salvamos apenas se dados forem gravados.
            # self.has_changed = True 

    def has_data(self) -> bool:
        """Verifica se o curso atual já tem dados salvos"""
        if not self.current_course_id:
            return False
        dados = self.cache_structure["courses"].get(self.current_course_id, {})
        return len(dados) > 0

    def get(self, key: str) -> List[str] | None:
        if not self.current_course_id: return None
        return self.cache_structure["courses"][self.current_course_id].get(key)

    def set(self, key: str, value: List[str]):
        if not self.current_course_id: return
        
        current_data = self.cache_structure["courses"][self.current_course_id]
        if current_data.get(key) != value:
            self.cache_structure["courses"][self.current_course_id][key] = value
            self.has_changed = True

    def get_all_tasks_formatted(self) -> List[Dict]:
        """Retorna tarefas do curso ATUAL"""
        tarefas = []
        if not self.current_course_id: return []

        data = self.cache_structure["courses"].get(self.current_course_id, {})
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