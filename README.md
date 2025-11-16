# 🤖 Projeto Cadernos_TEC

Este repositório contém o código-fonte de uma aplicação Python destinada a automatizar a criação e gerenciamento de cadernos de questões na plataforma **TEC Concursos**.

A ferramenta utiliza automação web para interagir com o site, aplicar filtros específicos de matérias e assuntos (definidos em arquivos de dados) e, em seguida, gerar relatórios sobre as operações realizadas.

## 🎯 Funcionalidades Principais

* **Interface Gráfica (GUI):** Possui uma interface gráfica (`run_gui.py` e `src/gui/main_window.py`) para facilitar a interação do usuário.
* **Automação Web:** Utiliza automação (`src/automation/tec_automation.py` e `src/automation/web_automation.py`) para navegar no site do TEC, aplicar filtros e executar ações.
* **Gerenciamento de Filtros:** Carrega e processa dados de matérias e assuntos a partir de arquivos JSON e Python (`data/`) para aplicar filtros de forma automatizada.
* **Geração de Relatórios:** Cria relatórios de status (`src/reporting/report_generator.py`) baseados em um template Word (`templates/template_relatorio.docx`).
* **Orquestração:** Gerencia o fluxo completo da automação através de um orquestrador (`src/automation/orchestrator.py`).
* **Gerenciamento de Cache:** Inclui um gerenciador de cache (`src/cache_manager.py`) para otimizar o desempenho e evitar recarregamentos desnecessários.

## 📂 Estrutura do Repositório

Aqui está uma visão geral da organização dos arquivos e diretórios principais:

```
├── data/                    # Contém dados e scripts para carregar filtros, matérias e assuntos
│   ├── data_loader.py
│   ├── filtros_tec_completo.py
│   ├── materias_assuntos_tec.json
│   └── ...
├── src/                     # Código-fonte principal da aplicação
│   ├── automation/            # Módulos de automação web
│   │   ├── tec_automation.py
│   │   ├── web_automation.py
│   │   ├── orchestrator.py
│   │   └── ...
│   ├── gui/                   # Código da interface gráfica
│   │   └── main_window.py
│   ├── reporting/             # Geração de relatórios
│   │   └── report_generator.py
│   ├── cache_manager.py
│   └── matching.py
├── templates/               # Templates de documentos
│   └── template_relatorio.docx
├── .gitignore               # Arquivos a serem ignorados pelo Git
├── icon.ico                 # Ícone da aplicação
├── main.py                  # Script principal (possível ponto de entrada alternativo)
├── requirements.txt         # Lista de dependências Python
├── run_gui.py               # Ponto de entrada para iniciar a aplicação com GUI
└── teste_rapido_tec.py      # Script para testes rápidos
```

## 🚀 Como Executar o Projeto

Para rodar esta aplicação em sua máquina local, siga os passos abaixo:

1.  **Clone o repositório:**
    ```bash
    git clone [URL-DO-SEU-REPOSITORIO]
    cd Cadernos_TEC
    ```

2.  **Crie e ative um ambiente virtual** (Recomendado):
    ```bash
    # Para Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Para macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    O projeto possui um arquivo `requirements.txt` com todas as bibliotecas necessárias.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Execute a aplicação:**
    Para iniciar a interface gráfica, execute o script `run_gui.py`.
    ```bash
    python run_gui.py
    ```

## 🤝 Contribuição

Contribuições são bem-vindas! Se você encontrar um bug ou tiver sugestões de melhoria, sinta-se à vontade para abrir uma *issue* ou enviar um *pull request*.
````