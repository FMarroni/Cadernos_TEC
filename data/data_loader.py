# Ficheiro: data/data_loader.py
# (VERSÃO 5 - CORREÇÃO do AttributeError 'lista_completa_fallback')

import os
import json
import traceback
from typing import List, Dict, Callable

# Esta lógica agora encontra o arquivo JSON ao lado deste script
try:
    # Obtém o caminho absoluto para o diretório onde este script (data_loader.py) está
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # Fallback para o PyInstaller (quando __file__ não está definido)
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

# Constrói o caminho para o arquivo JSON
HIERARQUIA_FILE = os.path.join(_SCRIPT_DIR, "materias_assuntos_tec.json")


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
        self.lista_completa_fallback: List[str] = [] # <-- Será preenchido agora

        try:
            self._load_and_process_data()
        except Exception as e:
            self.log(f"❌ Falha crítica ao carregar ou processar o arquivo de dados: {e}")
            self.log(traceback.format_exc())
            raise # Interrompe a inicialização do Orquestrador

    def _load_and_process_data(self):
        """Lê o JSON e preenche os atributos da classe."""
        self.log(f"Carregando arquivo de hierarquia: {HIERARQUIA_FILE}")

        try:
            with open(HIERARQUIA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.log(f"❌ ERRO CRÍTICO: Arquivo de dados não encontrado em '{HIERARQUIA_FILE}'")
            self.log(f"  (Verifique se 'materias_assuntos_tec.json' está na pasta 'data')")
            raise
        except json.JSONDecodeError:
            self.log(f"❌ ERRO CRÍTICO: O arquivo '{HIERARQUIA_FILE}' não é um JSON válido.")
            raise
        
        # Listas temporárias
        materias_list = []
        assuntos_dict = {}
        lista_fallback = [] # Lista plana com TODOS os assuntos

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
                    lista_fallback.append(nome_assunto) # Adiciona à lista plana
        
        self.log(f"Processadas {len(materias_list)} matérias e {len(lista_fallback)} assuntos no total.")
        
        # Armazena os resultados como atributos da instância
        self.materias = materias_list
        self.assuntos_por_materia = assuntos_dict        
        self.lista_completa_fallback = lista_fallback
        