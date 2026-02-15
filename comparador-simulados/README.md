# Comparador IA de Simulados

**Autor:** Manus AI
**Versão:** 1.0.0

## 1. Visão Geral

O **Comparador IA de Simulados** é uma ferramenta desenvolvida em **Google Apps Script** para automatizar a validação de dados de simulados de concursos públicos entre duas fontes distintas:

- **Fonte A (Base):** Uma planilha Google Sheets (`ID: 1weow7SAt4Z5Gyzry34mrmRp4inqRYpQ5S9kh2L06l90`) contendo os dados estruturados na aba `BaseDados`.
- **Fonte B (Alvo):** Um documento Google Docs (`ID: 1pV1sMYxVv3hvcAzuK4iMKKoRP3PmgZhNEUbfn7hiY3A`) com o planejamento dos simulados em formato de texto semi-estruturado.

O sistema utiliza a **Gemini API** (modelo `gemini-2.5-flash`) para realizar o parsing inteligente do Google Docs, convertendo o texto em dados estruturados (JSON) que podem ser comparados com a base do Google Sheets. O objetivo é identificar discrepâncias, como diferenças no número de questões, professores responsáveis, ou simulados/disciplinas ausentes em uma das fontes.

## 2. Arquitetura e Fluxo de Execução

O script é modular e opera diretamente dentro do ambiente do Google Sheets. O fluxo principal é orquestrado pela função `executarComparacaoCompleta()` e segue as seguintes etapas:

1.  **Extração da Fonte A (Sheets):** A função `extrairDadosSheets()` lê todas as linhas da aba `BaseDados`, normaliza os campos (nomes de simulados, blocos, etc.) e os converte em um array de objetos JSON padronizados.

2.  **Extração da Fonte B (Docs):** A função `extrairDadosDoc()` lê o conteúdo do Google Docs. Primeiramente, um parser local (`extrairLocalFallback`) tenta extrair os dados com base na estrutura de linhas com tabulação. Se o parser local não conseguir extrair disciplinas de um bloco, ele recorre à **Gemini API** (`extrairComGemini`), enviando o bloco de texto do simulado para que a IA o converta em JSON estruturado. Essa abordagem híbrida otimiza a velocidade e reduz os custos de API.

3.  **Comparação:** A função `compararFontes()` recebe os dados das duas fontes. Ela agrupa os registros por simulado e utiliza um algoritmo de **matching fuzzy** (`encontrarMelhorMatch` com coeficiente de Dice) para parear os simulados entre as fontes, mesmo que os nomes não sejam idênticos. Em seguida, compara cada disciplina dentro dos simulados pareados, verificando divergências em número de questões, numeração, professor e bloco.

4.  **Geração de Relatório:** A função `gravarResultados()` cria (ou limpa) uma aba chamada `Comparação` na planilha ativa. Ela gera um resumo estatístico e uma tabela detalhada com todos os resultados, utilizando formatação condicional para destacar visualmente as discrepâncias (vermelho para itens ausentes no Doc, azul para itens ausentes no Sheets, e laranja para dados divergentes).

## 3. Como Utilizar

Para utilizar a ferramenta, siga os passos abaixo:

1.  **Copie o Código:** Copie todo o conteúdo do arquivo `ComparadorSimulados_Completo.gs`.

2.  **Abra o Editor de Script:** Na sua planilha Google Sheets (pode ser a própria Fonte A ou uma nova), vá em `Extensões > Apps Script`.

3.  **Cole o Código:** Apague qualquer código existente no editor e cole o código copiado. Salve o projeto (ícone de disquete).

4.  **Configure a API Key:**
    - Volte para a planilha. Um novo menu chamado **"🔍 Comparador de Simulados"** deverá aparecer (pode levar alguns segundos ou exigir que a página seja recarregada).
    - Clique em `🔍 Comparador de Simulados > ⚙️ Configurar API Key`.
    - No pop-up, insira sua chave de API da Gemini (Google AI Studio).

5.  **Execute a Comparação:**
    - Clique em `🔍 Comparador de Simulados > ▶️ Executar Comparação Completa`.
    - O script solicitará permissões para acessar seus documentos e planilhas e para se conectar a serviços externos (a API). Conceda as permissões necessárias.
    - O processo pode levar alguns minutos, dependendo do tamanho dos documentos e da latência da API. Toasts no canto inferior direito indicarão o progresso.

6.  **Analise os Resultados:** Ao final, uma aba chamada `Comparação` será criada com o relatório detalhado das divergências encontradas.

### Funções do Menu

-   **▶️ Executar Comparação Completa:** Roda todo o processo (extração, comparação e relatório).
-   **1️⃣ Extrair Dados do Sheets (Fonte A):** Executa apenas a extração do Sheets e salva os dados em cache.
-   **2️⃣ Extrair Dados do Doc (Fonte B) via IA:** Executa apenas a extração do Docs e salva os dados em cache.
-   **3️⃣ Comparar Fontes A vs B:** Compara os dados salvos em cache das etapas 1 e 2.
-   **⚙️ Configurar API Key:** Salva sua chave da Gemini API nas propriedades do script.
-   **🗑️ Limpar Resultados:** Apaga a aba `Comparação`.

## 4. Estrutura de Dados Padrão (JSON)

Todos os registros, tanto do Sheets quanto do Docs, são convertidos para o seguinte formato JSON antes da comparação:

```json
{
  "simulado": "Nome Completo do Simulado",
  "bloco": "Nome do Bloco ou Bloco Único",
  "disciplina": "Nome da Matéria",
  "questoes": 10,
  "numeracao": "01 - 10",
  "professor": "Nome do Professor",
  "fonte": "Sheets" // ou "Doc"
}
```

## 5. Desafios Técnicos Resolvidos

-   **Parsing de Texto Não Estruturado:** O uso da Gemini API permite a extração de dados de um formato de texto livre, identificando blocos, disciplinas e seus respectivos atributos com alta precisão.
-   **Normalização de Dados:** Funções de normalização (`normalizarNomeSimulado`, `normalizarDisciplina`, etc.) são cruciais para unificar a nomenclatura entre as duas fontes, permitindo uma comparação eficaz.
-   **Matching Fuzzy de Simulados:** O comparador não depende de nomes de simulados idênticos. O algoritmo de similaridade de string (coeficiente de Dice) consegue parear simulados mesmo com pequenas diferenças nos nomes, aumentando a robustez da ferramenta.
-   **Estrutura de Múltiplos Blocos:** O parser é capaz de identificar linhas que definem blocos (ex: "Conhecimentos Gerais") e aplicar essa informação a todas as disciplinas subsequentes até que um novo bloco seja definido.

## 6. Referências

-   [1] [Google Apps Script](https://developers.google.com/apps-script)
-   [2] [Google AI for Developers (Gemini API)](https://ai.google.dev/)
-   [3] [Fonte de Dados A (Google Sheets)](https://docs.google.com/spreadsheets/d/1weow7SAt4Z5Gyzry34mrmRp4inqRYpQ5S9kh2L06l90/edit)
-   [4] [Fonte de Dados B (Google Docs)](https://docs.google.com/document/d/1pV1sMYxVv3hvcAzuK4iMKKoRP3PmgZhNEUbfn7hiY3A/edit)
