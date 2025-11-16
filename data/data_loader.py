# Ficheiro: data/data_loader.py

import os
import sys  # <-- Importe o 'sys'
import json
import traceback
from typing import List, Dict, Callable

def resource_path(relative_path: str) -> str:
    """
    Retorna o caminho absoluto para o recurso, funcionando para desenvolvimento
    e para o executável do PyInstaller.
    """
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Se _MEIPASS não existir, estamos em modo de desenvolvimento
        # O caminho base é o diretório do script principal que foi executado
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Constrói o caminho para o arquivo JSON usando a função auxiliar
# O caminho relativo deve ser 'data/materias_assuntos_tec.json'
HIERARQUIA_FILE = resource_path("data/materias_assuntos_tec.json")


class DataLoader:
    """
    Responsável por carregar e processar o arquivo JSON
    com a hierarquia de Matérias -> Assuntos.
    """
    
    def __init__(self, log_callback: Callable[..., None]):
        self.log = log_callback
        
        # Atributos que serão preenchidos
        self.materias: List[str] = []
        self.assuntos_por_materia: Dict[str, List[str]] = {}
        self.lista_completa_fallback: List[str] = []

        try:
            self._load_and_process_data()
        except Exception as e:
            self.log(f"❌ Falha crítica ao carregar ou processar o arquivo de dados: {e}")
            self.log(traceback.format_exc())
            raise

    def _load_and_process_data(self):
        """Lê o JSON e preenche os atributos da classe."""
        self.log(f"Carregando arquivo de hierarquia: {HIERARQUIA_FILE}")

        try:
            # A lógica aqui dentro não precisa mudar
            with open(HIERARQUIA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.log(f"❌ ERRO CRÍTICO: Arquivo de dados não encontrado em '{HIERARQUIA_FILE}'")
            self.log(f"  (Verifique se 'materias_assuntos_tec.json' está na pasta 'data' e se a pasta foi incluída no build)")
            raise
        except json.JSONDecodeError:
            self.log(f"❌ ERRO CRÍTICO: O arquivo '{HIERARQUIA_FILE}' não é um JSON válido.")
            raise
        
        # O resto do seu código permanece exatamente o mesmo...
        materias_list = []
        assuntos_dict = {}
        lista_fallback = []

        for materia_data in data:
            nome_materia = materia_data.get('nome')
            if not nome_materia:
                continue
            
            materias_list.append(nome_materia)
            assuntos_dict[nome_materia] = []
            
            for assunto_data in materia_data.get('assuntos', []):
                nome_assunto = assunto_data.get('nome')
                if nome_assunto:
                    assuntos_dict[nome_materia].append(nome_assunto)
                    lista_fallback.append(nome_assunto)
        
        self.log(f"Processadas {len(materias_list)} matérias e {len(lista_fallback)} assuntos no total.")
        
        self.materias = materias_list
        self.assuntos_por_materia = assuntos_dict        
        self.lista_completa_fallback = lista_fallback

