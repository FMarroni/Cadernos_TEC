/**
 * ============================================================
 * COMPARADOR IA DE SIMULADOS
 * ============================================================
 * Compara dados de simulados entre Google Sheets (Fonte A)
 * e Google Docs (Fonte B) usando Gemini API para parsing.
 * 
 * Autor: Manus AI
 * Versão: 1.0.0
 * ============================================================
 */

// ==================== CONFIGURAÇÕES ====================

const CONFIG = {
  // IDs dos documentos (ALTERAR conforme necessário)
  SHEETS_ID: '1weow7SAt4Z5Gyzry34mrmRp4inqRYpQ5S9kh2L06l90',
  DOC_ID: '1pV1sMYxVv3hvcAzuK4iMKKoRP3PmgZhNEUbfn7hiY3A',
  
  // Nome da aba com dados base no Sheets
  ABA_BASEDADOS: 'BaseDados',
  
  // Nome da aba de resultados (será criada automaticamente)
  ABA_RESULTADOS: 'Comparação',
  ABA_LOG: 'Log IA',
  
  // Colunas da BaseDados (índice 0-based)
  COL: {
    SIMULADO: 0,    // A - Nome do simulado
    CONCURSO: 1,    // B - Concurso
    CARGO: 2,       // C - Cargo
    BLOCO: 3,       // D - Bloco
    DISCIPLINA: 4,  // E - Disciplina
    DISC_PADRAO: 5, // F - Disciplina Padrão
    TOPICO: 6,      // G - Tópico
    QUESTOES: 7,    // H - Número de questões
    PESO: 8,        // I - Peso
    NUMERACAO: 9,   // J - Numeração do Simulado
    PROFESSOR: 10   // K - Responsável
  },
  
  // Gemini API
  GEMINI_MODEL: 'gemini-2.5-flash-preview-05-20',
  GEMINI_TEMPERATURE: 0.1,
  GEMINI_MAX_TOKENS: 65536,
  
  // Limites
  MAX_DOC_CHARS_PER_REQUEST: 30000,
  BATCH_DELAY_MS: 2000
};

// ==================== MENU ====================

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('🔍 Comparador de Simulados')
    .addItem('▶️ Executar Comparação Completa', 'executarComparacaoCompleta')
    .addSeparator()
    .addItem('1️⃣ Extrair Dados do Sheets (Fonte A)', 'executarExtracaoSheets')
    .addItem('2️⃣ Extrair Dados do Doc (Fonte B) via IA', 'executarExtracaoDoc')
    .addItem('3️⃣ Comparar Fontes A vs B', 'executarComparacao')
    .addSeparator()
    .addItem('⚙️ Configurar API Key', 'configurarApiKey')
    .addItem('🗑️ Limpar Resultados', 'limparResultados')
    .addToUi();
}

function configurarApiKey() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.prompt(
    'Configurar Gemini API Key',
    'Cole sua API Key do Google AI Studio (Gemini):',
    ui.ButtonSet.OK_CANCEL
  );
  
  if (result.getSelectedButton() === ui.Button.OK) {
    const key = result.getResponseText().trim();
    if (key) {
      PropertiesService.getScriptProperties().setProperty('GEMINI_API_KEY', key);
      ui.alert('✅ API Key salva com sucesso!');
    } else {
      ui.alert('❌ API Key não pode ser vazia.');
    }
  }
}

function getApiKey() {
  const key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!key) {
    throw new Error('API Key do Gemini não configurada. Use o menu: Comparador > Configurar API Key');
  }
  return key;
}
/**
 * ============================================================
 * EXTRATOR SHEETS (FONTE A)
 * ============================================================
 * Lê a aba BaseDados e converte cada linha para o formato
 * JSON padronizado.
 * ============================================================
 */

/**
 * Extrai todos os registros da aba BaseDados e retorna
 * como array de objetos padronizados.
 * @returns {Object[]} Array de registros padronizados
 */
function extrairDadosSheets() {
  const ss = SpreadsheetApp.openById(CONFIG.SHEETS_ID);
  const ws = ss.getSheetByName(CONFIG.ABA_BASEDADOS);
  
  if (!ws) {
    throw new Error(`Aba "${CONFIG.ABA_BASEDADOS}" não encontrada na planilha.`);
  }
  
  const dados = ws.getDataRange().getValues();
  const registros = [];
  
  // Pular cabeçalho (linha 0)
  for (let i = 1; i < dados.length; i++) {
    const row = dados[i];
    const simulado = String(row[CONFIG.COL.SIMULADO] || '').trim();
    
    // Ignorar linhas vazias
    if (!simulado) continue;
    
    const registro = {
      simulado: normalizarNomeSimulado(simulado),
      bloco: normalizarBloco(String(row[CONFIG.COL.BLOCO] || '').trim()),
      disciplina: normalizarDisciplina(String(row[CONFIG.COL.DISCIPLINA] || '').trim()),
      disciplina_padrao: String(row[CONFIG.COL.DISC_PADRAO] || '').trim(),
      questoes: parseFloat(row[CONFIG.COL.QUESTOES]) || 0,
      numeracao: normalizarNumeracao(String(row[CONFIG.COL.NUMERACAO] || '').trim()),
      professor: normalizarProfessor(String(row[CONFIG.COL.PROFESSOR] || '').trim()),
      fonte: 'Sheets'
    };
    
    registros.push(registro);
  }
  
  Logger.log(`[Extrator Sheets] ${registros.length} registros extraídos de ${contarSimuladosUnicos(registros)} simulados.`);
  return registros;
}

/**
 * Conta simulados únicos em um array de registros.
 */
function contarSimuladosUnicos(registros) {
  const unicos = new Set(registros.map(r => r.simulado));
  return unicos.size;
}

/**
 * Executa a extração do Sheets e exibe resultado.
 */
function executarExtracaoSheets() {
  const ui = SpreadsheetApp.getUi();
  try {
    const registros = extrairDadosSheets();
    const nSimulados = contarSimuladosUnicos(registros);
    
    // Salvar no cache para uso posterior
    CacheService.getScriptCache().put('dados_sheets', JSON.stringify(registros), 3600);
    
    ui.alert(
      '✅ Extração Sheets Concluída',
      `Registros extraídos: ${registros.length}\nSimulados únicos: ${nSimulados}`,
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert('❌ Erro na Extração', e.message, ui.ButtonSet.OK);
    Logger.log(`[ERRO Extrator Sheets] ${e.message}\n${e.stack}`);
  }
}
/**
 * ============================================================
 * FUNÇÕES DE NORMALIZAÇÃO
 * ============================================================
 * Unificam nomes de simulados, disciplinas, blocos e
 * professores entre as duas fontes para permitir comparação.
 * ============================================================
 */

/**
 * Normaliza o nome do simulado para comparação.
 * Remove espaços extras, padroniza hifens e caracteres especiais.
 */
function normalizarNomeSimulado(nome) {
  if (!nome) return '';
  
  let n = nome
    // Normalizar espaços
    .replace(/\s+/g, ' ')
    .trim()
    // Padronizar travessões e hifens
    .replace(/\s*[–—]\s*/g, ' - ')
    // Remover espaços antes de vírgulas
    .replace(/\s*,\s*/g, ', ')
    // Padronizar "Pós-edital" / "Pós-Edital" / "Pós edital"
    .replace(/p[oó]s[\s-]*edital/gi, 'Pós-Edital')
    // Padronizar "Pré-edital" / "Pré-Edital" / "Pré edital"
    .replace(/pr[eé][\s-]*edital/gi, 'Pré-Edital')
    // Padronizar "BANCA:" / "Banca:"
    .replace(/banca\s*:\s*/gi, 'Banca: ')
    // Padronizar "CEBRASPE" / "Cebraspe"
    .replace(/cebraspe/gi, 'Cebraspe')
    // Padronizar "FADESP" / "Fadesp"
    .replace(/fadesp/gi, 'Fadesp')
    // Padronizar "IDECAN" / "Idecan"
    .replace(/idecan/gi, 'IDECAN')
    // Padronizar "Petrobrás" / "Petrobras"
    .replace(/petrobr[aá]s/gi, 'Petrobras')
    // Padronizar "ALMS" / "AL MS"
    .replace(/\bAL\s*MS\b/gi, 'ALMS')
    // Padronizar "SEFAZ" 
    .replace(/\bSEFAZ\b/gi, 'SEFAZ')
    // Remover espaços duplos finais
    .replace(/\s+/g, ' ')
    .trim();
  
  return n;
}

/**
 * Gera uma chave simplificada do simulado para matching fuzzy.
 * Remove pontuação, números ordinais, e normaliza fortemente.
 */
function gerarChaveSimulado(nome) {
  if (!nome) return '';
  
  let chave = normalizarNomeSimulado(nome)
    .toLowerCase()
    // Remover acentos
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    // Remover pontuação
    .replace(/[^\w\s]/g, ' ')
    // Remover "simulado especial", "simulado final"
    .replace(/\bsimulado\s+(especial|final)\b/g, '')
    // Remover números ordinais no início (1º, 2°, 10º, etc.)
    .replace(/\b\d+[ºo°]\b/g, '')
    // Remover "banca" e nome da banca
    .replace(/\bbanca\s*\w+/g, '')
    // Remover datas (dd/mm)
    .replace(/\b\d{1,2}\s*\/\s*\d{1,2}\b/g, '')
    // Remover "pos edital", "pre edital"
    .replace(/\b(pos|pre)\s*edital\b/g, '')
    // Remover "cargo:"
    .replace(/\bcargo\s*/g, '')
    // Normalizar espaços
    .replace(/\s+/g, ' ')
    .trim();
  
  return chave;
}

/**
 * Normaliza o nome do bloco.
 */
function normalizarBloco(bloco) {
  if (!bloco) return 'Bloco Único';
  
  let b = bloco
    .replace(/\s+/g, ' ')
    .trim();
  
  // Mapear blocos numéricos
  if (/^[123]\.?0?$/.test(b)) {
    const num = parseInt(b);
    const romanos = { 1: 'I', 2: 'II', 3: 'III' };
    return `Bloco ${romanos[num] || num}`;
  }
  
  // Padronizar "BLOCO I" -> "Bloco I"
  b = b.replace(/^BLOCO\s+/i, 'Bloco ');
  
  // Padronizar variações de "Conhecimentos"
  b = b.replace(/^conhecimentos\s+/i, 'Conhecimentos ');
  
  // Capitalizar primeira letra
  if (b.length > 0) {
    b = b.charAt(0).toUpperCase() + b.slice(1);
  }
  
  return b;
}

/**
 * Normaliza o nome da disciplina.
 * Remove (*), espaços extras, e padroniza nomes comuns.
 */
function normalizarDisciplina(disciplina) {
  if (!disciplina) return '';
  
  let d = disciplina
    // Remover (*) e variações
    .replace(/\s*\(\*\)\s*/g, '')
    .replace(/\s*\*\s*$/g, '')
    // Normalizar espaços
    .replace(/\s+/g, ' ')
    .trim();
  
  return d;
}

/**
 * Gera chave normalizada da disciplina para comparação.
 */
function gerarChaveDisciplina(disciplina) {
  if (!disciplina) return '';
  
  let chave = normalizarDisciplina(disciplina)
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    // Remover "noções de", "noções básicas de"
    .replace(/\bnocoes\s+(basicas\s+)?de\s+/g, '')
    // Padronizar abreviações comuns
    .replace(/\blg?\.\s*portuguesa\b/g, 'lingua portuguesa')
    .replace(/\bportugues\b/g, 'lingua portuguesa')
    .replace(/\brac\.\s*logico\b/g, 'raciocinio logico')
    .replace(/\binformatica\b/g, 'informatica')
    .replace(/\bdir\.\s*/g, 'direito ')
    // Remover pontuação
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  
  return chave;
}

/**
 * Normaliza a numeração do simulado.
 * Padroniza "01 - 10", "1 – 10", "1-10" para "1 - 10".
 */
function normalizarNumeracao(numeracao) {
  if (!numeracao) return '';
  
  let n = numeracao
    .replace(/\s*[–—-]\s*/g, ' - ')
    .replace(/\s+/g, ' ')
    .trim();
  
  // Remover zeros à esquerda: "01 - 10" -> "1 - 10"
  n = n.replace(/\b0+(\d)/g, '$1');
  
  return n;
}

/**
 * Normaliza o nome do professor.
 */
function normalizarProfessor(professor) {
  if (!professor) return '';
  
  return professor
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Calcula a similaridade entre duas strings (Dice coefficient).
 * Retorna valor entre 0 e 1.
 */
function calcularSimilaridade(str1, str2) {
  if (!str1 || !str2) return 0;
  if (str1 === str2) return 1;
  
  const s1 = str1.toLowerCase();
  const s2 = str2.toLowerCase();
  
  if (s1 === s2) return 1;
  
  // Bigrams
  const bigrams1 = new Set();
  const bigrams2 = new Set();
  
  for (let i = 0; i < s1.length - 1; i++) {
    bigrams1.add(s1.substring(i, i + 2));
  }
  for (let i = 0; i < s2.length - 1; i++) {
    bigrams2.add(s2.substring(i, i + 2));
  }
  
  let intersecao = 0;
  for (const bg of bigrams1) {
    if (bigrams2.has(bg)) intersecao++;
  }
  
  return (2 * intersecao) / (bigrams1.size + bigrams2.size);
}
/**
 * ============================================================
 * EXTRATOR DOC COM IA (FONTE B)
 * ============================================================
 * Lê o Google Docs, segmenta por simulado, e usa Gemini API
 * para extrair dados estruturados de cada bloco de texto.
 * 
 * FORMATO DO DOC (texto exportado):
 * - Cada campo da tabela está em uma LINHA SEPARADA com \t
 * - Padrão: \tDisciplina, \tQuestões, \tNumeração, \tProfessor
 * - Blocos são linhas com tab contendo padrões como 
 *   "Bloco Único - X Questões - Peso Y"
 * ============================================================
 */

/**
 * Extrai o conteúdo completo do Google Docs como texto.
 * @returns {string} Texto completo do documento
 */
function obterConteudoDoc() {
  const doc = DocumentApp.openById(CONFIG.DOC_ID);
  const body = doc.getBody();
  const texto = body.getText();
  
  Logger.log(`[Extrator Doc] Documento carregado: ${texto.length} caracteres.`);
  return texto;
}

/**
 * Segmenta o texto do documento em blocos por simulado.
 * @param {string} textoCompleto - Texto do documento
 * @returns {Object[]} Array de {titulo, linhas[]}
 */
function segmentarSimulados(textoCompleto) {
  const linhas = textoCompleto.split('\n');
  const simulados = [];
  let blocoAtual = null;
  
  const regexTitulo = /^(\d+[ºo°]\s+)?Simulado\s+(Especial|Final)\s+/i;
  const regexMarketing = /^\t?Marketing,/i;
  const regexJornalismo = /^\t?Jornalismo,/i;
  
  for (let i = 0; i < linhas.length; i++) {
    const linhaTrimmed = linhas[i].trim();
    
    if (regexTitulo.test(linhaTrimmed)) {
      if (blocoAtual) {
        simulados.push(blocoAtual);
      }
      
      let titulo = linhaTrimmed;
      // Verificar continuação do título na próxima linha
      if (i + 1 < linhas.length) {
        const prox = linhas[i + 1].trim();
        if (prox && !prox.startsWith('P.S') && !prox.startsWith('Disciplina')
            && !regexTitulo.test(prox) && !regexMarketing.test(prox)
            && !linhas[i + 1].startsWith('\t') && prox.length < 100) {
          if (/^(Pública|Gestão|Público)/.test(prox)) {
            titulo += ' ' + prox;
            i++;
          }
        }
      }
      
      blocoAtual = { titulo: titulo, linhas: [] };
    } else if (blocoAtual) {
      if (regexMarketing.test(linhas[i]) || regexJornalismo.test(linhas[i])) {
        simulados.push(blocoAtual);
        blocoAtual = null;
      } else {
        blocoAtual.linhas.push(linhas[i]);
      }
    }
  }
  
  if (blocoAtual) {
    simulados.push(blocoAtual);
  }
  
  Logger.log(`[Extrator Doc] ${simulados.length} simulados segmentados.`);
  return simulados;
}

/**
 * Chama a Gemini API para extrair dados estruturados de um bloco de simulado.
 * @param {string} textoSimulado - Texto do bloco do simulado
 * @returns {Object} Dados extraídos {simulado, registros[]}
 */
function extrairComGemini(textoSimulado) {
  const apiKey = getApiKey();
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${CONFIG.GEMINI_MODEL}:generateContent?key=${apiKey}`;
  
  const prompt = `Você é um extrator de dados preciso. Analise o texto abaixo que descreve um simulado de concurso público e extraia TODOS os registros de disciplinas em formato JSON.

FORMATO DO TEXTO:
- O título do simulado é a primeira linha.
- Linhas com \\t no início são dados da tabela.
- Cada disciplina tem 4 linhas consecutivas com \\t: nome da disciplina, número de questões, numeração, professor.
- Linhas de BLOCO são linhas com \\t que contêm padrões como "Bloco Único - X Questões", "Conhecimentos Gerais - X Questões", "BLOCO I", "Discursiva - X Questões". Essas NÃO são disciplinas.
- Ignore linhas de cabeçalho (Disciplina, Número de questões, Numeração do Simulado, Responsável).
- Ignore linhas de P.S, Marketing, URLs e metadados.

REGRAS:
1. O bloco se aplica a todas as disciplinas abaixo dele até outro bloco ser definido.
2. Se não houver bloco explícito, use "Bloco Único".
3. Remova (*) ou * do final dos nomes de disciplinas.
4. Mantenha os nomes dos professores exatamente como aparecem.
5. A numeração deve ser no formato "X - Y" (ex: "1 - 10").
6. Questões deve ser um número inteiro.

TEXTO:
---
${textoSimulado}
---

Retorne APENAS um JSON válido (sem markdown):
{
  "simulado": "Nome Completo do Simulado",
  "registros": [
    {
      "bloco": "Nome do Bloco",
      "disciplina": "Nome da Disciplina",
      "questoes": 10,
      "numeracao": "1 - 10",
      "professor": "Nome do Professor"
    }
  ]
}`;

  const payload = {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: {
      temperature: CONFIG.GEMINI_TEMPERATURE,
      maxOutputTokens: CONFIG.GEMINI_MAX_TOKENS,
      responseMimeType: "application/json"
    }
  };
  
  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(url, options);
  const statusCode = response.getResponseCode();
  
  if (statusCode !== 200) {
    const erro = response.getContentText();
    Logger.log(`[Gemini API] Erro ${statusCode}: ${erro.substring(0, 300)}`);
    throw new Error(`Gemini API retornou status ${statusCode}`);
  }
  
  const resultado = JSON.parse(response.getContentText());
  let textoResposta = '';
  
  try {
    textoResposta = resultado.candidates[0].content.parts[0].text;
  } catch (e) {
    throw new Error('Resposta da Gemini API em formato inesperado.');
  }
  
  // Parsear JSON
  textoResposta = textoResposta.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim();
  return JSON.parse(textoResposta);
}

/**
 * Extrai disciplinas usando parsing local (fallback sem IA).
 * Cada campo está em uma linha separada com \t.
 * @param {Object} bloco - {titulo, linhas[]}
 * @returns {Object} {simulado, registros[]}
 */
function extrairLocalFallback(bloco) {
  const registros = [];
  let blocoAtual = 'Bloco Único';
  
  const regexBloco = /^\t?(Bloco\s+\w+|Conhecimentos\s+\w+|BLOCO\s+[IVX\d]+|Discursiva)\s*[-–]?\s*/i;
  const regexCabecalho = /^\t?(Disciplina|Número de questões|Numeração do Simulado|Responsável)$/i;
  
  // Coletar linhas com tab que não são cabeçalho
  const linhasTab = [];
  for (const linha of bloco.linhas) {
    if (linha.startsWith('\t')) {
      const conteudo = linha.replace(/^\t+/, '').trim();
      if (!regexCabecalho.test(linha) && conteudo) {
        linhasTab.push(conteudo);
      }
    }
  }
  
  let i = 0;
  while (i < linhasTab.length) {
    const conteudo = linhasTab[i];
    
    // Verificar se é linha de bloco
    if (regexBloco.test('\t' + conteudo)) {
      const m = conteudo.match(/^([\w\s\u00C0-\u024F]+?)(?:\s*[-–]\s*\d+)/i);
      if (m) {
        blocoAtual = m[1].trim();
      } else {
        const m2 = conteudo.match(/^(BLOCO\s+[IVX\d]+)/i);
        if (m2) {
          blocoAtual = m2[1].trim();
        } else if (/^discursiva/i.test(conteudo)) {
          blocoAtual = 'Discursiva';
        } else {
          blocoAtual = conteudo.split(/[-–]/)[0].trim();
        }
      }
      i++;
      continue;
    }
    
    // Tentar ler grupo de 4: disciplina, questoes, numeracao, professor
    if (i + 3 < linhasTab.length) {
      const disc = conteudo;
      const questoesStr = linhasTab[i + 1];
      const numeracaoStr = linhasTab[i + 2];
      const professorStr = linhasTab[i + 3];
      
      const mNum = questoesStr.match(/^(\d+)\s*$/);
      if (mNum && !regexBloco.test('\t' + disc)) {
        const mNumeracao = numeracaoStr.match(/^(\d+\s*[-–]\s*\d+|\d+)\s*$/);
        if (mNumeracao && !/^\d+$/.test(professorStr) && !regexBloco.test('\t' + professorStr)) {
          registros.push({
            bloco: normalizarBloco(blocoAtual),
            disciplina: normalizarDisciplina(disc),
            questoes: parseInt(mNum[1]),
            numeracao: normalizarNumeracao(numeracaoStr),
            professor: professorStr.trim()
          });
          i += 4;
          continue;
        }
      }
    }
    
    i++;
  }
  
  return { simulado: bloco.titulo, registros: registros };
}

/**
 * Processa todos os simulados do Doc.
 * Usa Gemini API como método principal, fallback local se falhar.
 * @returns {Object[]} Array de registros padronizados
 */
function extrairDadosDoc() {
  const textoCompleto = obterConteudoDoc();
  const blocos = segmentarSimulados(textoCompleto);
  const todosRegistros = [];
  const erros = [];
  let usouIA = 0;
  let usouLocal = 0;
  
  Logger.log(`[Extrator Doc] Processando ${blocos.length} simulados...`);
  
  for (let i = 0; i < blocos.length; i++) {
    const bloco = blocos[i];
    const tituloLog = bloco.titulo.substring(0, 70);
    Logger.log(`[Extrator Doc] ${i + 1}/${blocos.length}: ${tituloLog}...`);
    
    let dados = null;
    
    // Tentar parsing local primeiro (mais rápido e sem custo de API)
    const dadosLocal = extrairLocalFallback(bloco);
    
    if (dadosLocal.registros.length > 0) {
      dados = dadosLocal;
      usouLocal++;
      Logger.log(`  -> LOCAL: ${dados.registros.length} disciplinas.`);
    } else {
      // Fallback para Gemini API
      try {
        const textoBloco = bloco.titulo + '\n' + bloco.linhas.join('\n');
        dados = extrairComGemini(textoBloco);
        usouIA++;
        Logger.log(`  -> IA: ${dados.registros ? dados.registros.length : 0} disciplinas.`);
      } catch (e) {
        erros.push({ simulado: bloco.titulo, erro: e.message });
        Logger.log(`  -> ERRO IA: ${e.message}`);
      }
      
      // Delay entre requisições de API
      if (i < blocos.length - 1) {
        Utilities.sleep(CONFIG.BATCH_DELAY_MS);
      }
    }
    
    if (dados && dados.registros && Array.isArray(dados.registros)) {
      for (const reg of dados.registros) {
        todosRegistros.push({
          simulado: normalizarNomeSimulado(dados.simulado || bloco.titulo),
          bloco: normalizarBloco(reg.bloco || 'Bloco Único'),
          disciplina: normalizarDisciplina(reg.disciplina || ''),
          disciplina_padrao: '',
          questoes: parseInt(reg.questoes) || 0,
          numeracao: normalizarNumeracao(String(reg.numeracao || '')),
          professor: normalizarProfessor(reg.professor || ''),
          fonte: 'Doc'
        });
      }
    }
  }
  
  Logger.log(`[Extrator Doc] Concluído: ${todosRegistros.length} registros. Local: ${usouLocal}, IA: ${usouIA}, Erros: ${erros.length}`);
  
  if (erros.length > 0) {
    salvarLogErros(erros);
  }
  
  return todosRegistros;
}

/**
 * Salva erros de extração na aba de Log.
 */
function salvarLogErros(erros) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let wsLog = ss.getSheetByName(CONFIG.ABA_LOG);
  
  if (!wsLog) {
    wsLog = ss.insertSheet(CONFIG.ABA_LOG);
  }
  
  wsLog.clear();
  wsLog.appendRow(['Timestamp', 'Simulado', 'Erro']);
  
  const agora = new Date().toISOString();
  for (const erro of erros) {
    wsLog.appendRow([agora, erro.simulado, erro.erro]);
  }
}

/**
 * Executa a extração do Doc e exibe resultado.
 */
function executarExtracaoDoc() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const registros = extrairDadosDoc();
    const nSimulados = contarSimuladosUnicos(registros);
    
    // Salvar no cache
    const cache = CacheService.getScriptCache();
    const jsonStr = JSON.stringify(registros);
    if (jsonStr.length > 90000) {
      const chunkSize = 90000;
      const numChunks = Math.ceil(jsonStr.length / chunkSize);
      cache.put('dados_doc_chunks', String(numChunks), 3600);
      for (let c = 0; c < numChunks; c++) {
        cache.put(`dados_doc_${c}`, jsonStr.substring(c * chunkSize, (c + 1) * chunkSize), 3600);
      }
    } else {
      cache.put('dados_doc_chunks', '0', 3600);
      cache.put('dados_doc', jsonStr, 3600);
    }
    
    ui.alert(
      '✅ Extração Doc Concluída',
      `Registros extraídos: ${registros.length}\nSimulados únicos: ${nSimulados}`,
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert('❌ Erro na Extração', e.message, ui.ButtonSet.OK);
    Logger.log(`[ERRO Extrator Doc] ${e.message}\n${e.stack}`);
  }
}

/**
 * Recupera dados do Doc do cache.
 */
function recuperarDadosDocCache() {
  const cache = CacheService.getScriptCache();
  const chunks = cache.get('dados_doc_chunks');
  
  if (!chunks) return null;
  
  if (chunks === '0') {
    const json = cache.get('dados_doc');
    return json ? JSON.parse(json) : null;
  }
  
  const numChunks = parseInt(chunks);
  let jsonStr = '';
  for (let c = 0; c < numChunks; c++) {
    const chunk = cache.get(`dados_doc_${c}`);
    if (!chunk) return null;
    jsonStr += chunk;
  }
  
  return JSON.parse(jsonStr);
}
/**
 * ============================================================
 * MOTOR DE COMPARAÇÃO
 * ============================================================
 * Cruza os dados extraídos das duas fontes e gera relatório
 * de discrepâncias.
 * ============================================================
 */

/**
 * Tipos de discrepância encontrados na comparação.
 */
const TIPO_DISCREPANCIA = {
  SIMULADO_APENAS_SHEETS: 'Simulado apenas no Sheets',
  SIMULADO_APENAS_DOC: 'Simulado apenas no Doc',
  DISCIPLINA_APENAS_SHEETS: 'Disciplina apenas no Sheets',
  DISCIPLINA_APENAS_DOC: 'Disciplina apenas no Doc',
  QUESTOES_DIVERGENTES: 'Nº de questões divergente',
  NUMERACAO_DIVERGENTE: 'Numeração divergente',
  PROFESSOR_DIVERGENTE: 'Professor divergente',
  BLOCO_DIVERGENTE: 'Bloco divergente',
  MATCH_OK: 'OK - Dados conferem'
};

/**
 * Agrupa registros por simulado.
 * @param {Object[]} registros - Array de registros
 * @returns {Map} Mapa de chaveSimulado -> {nomeOriginal, registros[]}
 */
function agruparPorSimulado(registros) {
  const mapa = new Map();
  
  for (const reg of registros) {
    const chave = gerarChaveSimulado(reg.simulado);
    
    if (!mapa.has(chave)) {
      mapa.set(chave, {
        nomeOriginal: reg.simulado,
        registros: []
      });
    }
    
    mapa.get(chave).registros.push(reg);
  }
  
  return mapa;
}

/**
 * Encontra o melhor match de simulado entre duas fontes.
 * @param {string} chave - Chave do simulado a buscar
 * @param {Map} mapaAlvo - Mapa da fonte alvo
 * @returns {string|null} Chave do melhor match ou null
 */
function encontrarMelhorMatch(chave, mapaAlvo) {
  // Match exato
  if (mapaAlvo.has(chave)) return chave;
  
  // Match por similaridade
  let melhorChave = null;
  let melhorScore = 0;
  
  for (const [chaveAlvo, _] of mapaAlvo) {
    const score = calcularSimilaridade(chave, chaveAlvo);
    if (score > melhorScore && score > 0.70) {
      melhorScore = score;
      melhorChave = chaveAlvo;
    }
  }
  
  if (melhorChave) {
    Logger.log(`[Match] "${chave}" -> "${melhorChave}" (score: ${melhorScore.toFixed(2)})`);
  }
  
  return melhorChave;
}

/**
 * Compara disciplinas de um mesmo simulado entre as duas fontes.
 * @param {Object[]} regsSheets - Registros do Sheets
 * @param {Object[]} regsDoc - Registros do Doc
 * @param {string} nomeSimulado - Nome do simulado
 * @returns {Object[]} Array de resultados de comparação
 */
function compararDisciplinas(regsSheets, regsDoc, nomeSimulado) {
  const resultados = [];
  const docUsados = new Set();
  
  // Para cada disciplina no Sheets, buscar correspondente no Doc
  for (const regS of regsSheets) {
    const chaveDiscS = gerarChaveDisciplina(regS.disciplina);
    let melhorMatch = null;
    let melhorScore = 0;
    let melhorIdx = -1;
    
    for (let j = 0; j < regsDoc.length; j++) {
      if (docUsados.has(j)) continue;
      
      const regD = regsDoc[j];
      const chaveDiscD = gerarChaveDisciplina(regD.disciplina);
      
      // Calcular similaridade
      let score = calcularSimilaridade(chaveDiscS, chaveDiscD);
      
      // Bonus se numeração bate
      if (regS.numeracao && regD.numeracao && regS.numeracao === regD.numeracao) {
        score += 0.2;
      }
      
      if (score > melhorScore && score > 0.55) {
        melhorScore = score;
        melhorMatch = regD;
        melhorIdx = j;
      }
    }
    
    if (melhorMatch && melhorIdx >= 0) {
      docUsados.add(melhorIdx);
      
      // Comparar campos
      const discrepancias = [];
      
      if (regS.questoes !== melhorMatch.questoes) {
        discrepancias.push(TIPO_DISCREPANCIA.QUESTOES_DIVERGENTES);
      }
      
      if (regS.numeracao !== melhorMatch.numeracao) {
        discrepancias.push(TIPO_DISCREPANCIA.NUMERACAO_DIVERGENTE);
      }
      
      if (regS.professor.toLowerCase() !== melhorMatch.professor.toLowerCase()) {
        // Verificar similaridade do nome do professor
        const simProf = calcularSimilaridade(regS.professor.toLowerCase(), melhorMatch.professor.toLowerCase());
        if (simProf < 0.85) {
          discrepancias.push(TIPO_DISCREPANCIA.PROFESSOR_DIVERGENTE);
        }
      }
      
      // Comparar blocos (normalizado)
      const blocoS = normalizarBloco(regS.bloco).toLowerCase();
      const blocoD = normalizarBloco(melhorMatch.bloco).toLowerCase();
      if (blocoS !== blocoD) {
        const simBloco = calcularSimilaridade(blocoS, blocoD);
        if (simBloco < 0.75) {
          discrepancias.push(TIPO_DISCREPANCIA.BLOCO_DIVERGENTE);
        }
      }
      
      resultados.push({
        simulado: nomeSimulado,
        status: discrepancias.length === 0 ? TIPO_DISCREPANCIA.MATCH_OK : discrepancias.join(' | '),
        disciplina_sheets: regS.disciplina,
        disciplina_doc: melhorMatch.disciplina,
        bloco_sheets: regS.bloco,
        bloco_doc: melhorMatch.bloco,
        questoes_sheets: regS.questoes,
        questoes_doc: melhorMatch.questoes,
        numeracao_sheets: regS.numeracao,
        numeracao_doc: melhorMatch.numeracao,
        professor_sheets: regS.professor,
        professor_doc: melhorMatch.professor,
        similaridade: melhorScore.toFixed(2)
      });
    } else {
      // Disciplina apenas no Sheets
      resultados.push({
        simulado: nomeSimulado,
        status: TIPO_DISCREPANCIA.DISCIPLINA_APENAS_SHEETS,
        disciplina_sheets: regS.disciplina,
        disciplina_doc: '',
        bloco_sheets: regS.bloco,
        bloco_doc: '',
        questoes_sheets: regS.questoes,
        questoes_doc: '',
        numeracao_sheets: regS.numeracao,
        numeracao_doc: '',
        professor_sheets: regS.professor,
        professor_doc: '',
        similaridade: '0'
      });
    }
  }
  
  // Disciplinas apenas no Doc
  for (let j = 0; j < regsDoc.length; j++) {
    if (docUsados.has(j)) continue;
    
    const regD = regsDoc[j];
    resultados.push({
      simulado: nomeSimulado,
      status: TIPO_DISCREPANCIA.DISCIPLINA_APENAS_DOC,
      disciplina_sheets: '',
      disciplina_doc: regD.disciplina,
      bloco_sheets: '',
      bloco_doc: regD.bloco,
      questoes_sheets: '',
      questoes_doc: regD.questoes,
      numeracao_sheets: '',
      numeracao_doc: regD.numeracao,
      professor_sheets: '',
      professor_doc: regD.professor,
      similaridade: '0'
    });
  }
  
  return resultados;
}

/**
 * Executa a comparação completa entre Sheets e Doc.
 * @param {Object[]} dadosSheets - Registros do Sheets
 * @param {Object[]} dadosDoc - Registros do Doc
 * @returns {Object[]} Todos os resultados de comparação
 */
function compararFontes(dadosSheets, dadosDoc) {
  const mapaSheets = agruparPorSimulado(dadosSheets);
  const mapaDoc = agruparPorSimulado(dadosDoc);
  
  const todosResultados = [];
  const docMatcheados = new Set();
  
  Logger.log(`[Comparador] Sheets: ${mapaSheets.size} simulados | Doc: ${mapaDoc.size} simulados`);
  
  // Para cada simulado no Sheets, buscar no Doc
  for (const [chaveS, grupoS] of mapaSheets) {
    const chaveMatchDoc = encontrarMelhorMatch(chaveS, mapaDoc);
    
    if (chaveMatchDoc) {
      docMatcheados.add(chaveMatchDoc);
      const grupoD = mapaDoc.get(chaveMatchDoc);
      
      const resultados = compararDisciplinas(
        grupoS.registros,
        grupoD.registros,
        grupoS.nomeOriginal
      );
      
      todosResultados.push(...resultados);
    } else {
      // Simulado apenas no Sheets
      for (const reg of grupoS.registros) {
        todosResultados.push({
          simulado: grupoS.nomeOriginal,
          status: TIPO_DISCREPANCIA.SIMULADO_APENAS_SHEETS,
          disciplina_sheets: reg.disciplina,
          disciplina_doc: '',
          bloco_sheets: reg.bloco,
          bloco_doc: '',
          questoes_sheets: reg.questoes,
          questoes_doc: '',
          numeracao_sheets: reg.numeracao,
          numeracao_doc: '',
          professor_sheets: reg.professor,
          professor_doc: '',
          similaridade: '0'
        });
      }
    }
  }
  
  // Simulados apenas no Doc
  for (const [chaveD, grupoD] of mapaDoc) {
    if (docMatcheados.has(chaveD)) continue;
    
    for (const reg of grupoD.registros) {
      todosResultados.push({
        simulado: grupoD.nomeOriginal,
        status: TIPO_DISCREPANCIA.SIMULADO_APENAS_DOC,
        disciplina_sheets: '',
        disciplina_doc: reg.disciplina,
        bloco_sheets: '',
        bloco_doc: reg.bloco,
        questoes_sheets: '',
        questoes_doc: reg.questoes,
        numeracao_sheets: '',
        numeracao_doc: reg.numeracao,
        professor_sheets: '',
        professor_doc: reg.professor,
        similaridade: '0'
      });
    }
  }
  
  return todosResultados;
}
/**
 * ============================================================
 * SAÍDA DE RESULTADOS
 * ============================================================
 * Grava os resultados da comparação na aba de resultados
 * com formatação visual (cores, filtros, resumo).
 * ============================================================
 */

/**
 * Grava os resultados na aba de comparação.
 * @param {Object[]} resultados - Array de resultados da comparação
 */
function gravarResultados(resultados) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let ws = ss.getSheetByName(CONFIG.ABA_RESULTADOS);
  
  // Criar ou limpar a aba
  if (ws) {
    ws.clear();
    ws.clearFormats();
  } else {
    ws = ss.insertSheet(CONFIG.ABA_RESULTADOS);
  }
  
  // ==================== RESUMO ====================
  const resumo = gerarResumo(resultados);
  
  // Título
  ws.getRange('A1').setValue('📊 COMPARADOR IA DE SIMULADOS - RELATÓRIO');
  ws.getRange('A1:N1').merge();
  ws.getRange('A1').setFontSize(14).setFontWeight('bold').setBackground('#1a73e8').setFontColor('white');
  
  // Data/hora
  ws.getRange('A2').setValue(`Gerado em: ${new Date().toLocaleString('pt-BR')}`);
  ws.getRange('A2:N2').merge();
  ws.getRange('A2').setFontSize(10).setFontColor('#666666');
  
  // Resumo
  const resumoInicio = 4;
  ws.getRange(resumoInicio, 1).setValue('RESUMO');
  ws.getRange(resumoInicio, 1, 1, 4).merge();
  ws.getRange(resumoInicio, 1).setFontSize(12).setFontWeight('bold').setBackground('#e8eaf6');
  
  const dadosResumo = [
    ['Total de registros comparados', resumo.total],
    ['✅ Dados conferem (OK)', resumo.ok],
    ['⚠️ Com discrepâncias', resumo.comDiscrepancia],
    ['🔴 Apenas no Sheets', resumo.apenasSheets],
    ['🔵 Apenas no Doc', resumo.apenasDoc],
    ['📋 Simulados no Sheets', resumo.simuladosSheets],
    ['📄 Simulados no Doc', resumo.simuladosDoc],
    ['🔗 Simulados pareados', resumo.simuladosPareados]
  ];
  
  for (let i = 0; i < dadosResumo.length; i++) {
    ws.getRange(resumoInicio + 1 + i, 1).setValue(dadosResumo[i][0]);
    ws.getRange(resumoInicio + 1 + i, 2).setValue(dadosResumo[i][1]);
    ws.getRange(resumoInicio + 1 + i, 2).setFontWeight('bold');
  }
  
  // ==================== TABELA DE DADOS ====================
  const tabelaInicio = resumoInicio + dadosResumo.length + 3;
  
  // Cabeçalho
  const cabecalho = [
    'Simulado',
    'Status',
    'Disciplina (Sheets)',
    'Disciplina (Doc)',
    'Bloco (Sheets)',
    'Bloco (Doc)',
    'Questões (Sheets)',
    'Questões (Doc)',
    'Numeração (Sheets)',
    'Numeração (Doc)',
    'Professor (Sheets)',
    'Professor (Doc)',
    'Similaridade'
  ];
  
  ws.getRange(tabelaInicio, 1, 1, cabecalho.length).setValues([cabecalho]);
  ws.getRange(tabelaInicio, 1, 1, cabecalho.length)
    .setFontWeight('bold')
    .setBackground('#34a853')
    .setFontColor('white')
    .setHorizontalAlignment('center');
  
  // Dados
  if (resultados.length > 0) {
    const dados = resultados.map(r => [
      r.simulado,
      r.status,
      r.disciplina_sheets,
      r.disciplina_doc,
      r.bloco_sheets,
      r.bloco_doc,
      r.questoes_sheets,
      r.questoes_doc,
      r.numeracao_sheets,
      r.numeracao_doc,
      r.professor_sheets,
      r.professor_doc,
      r.similaridade
    ]);
    
    ws.getRange(tabelaInicio + 1, 1, dados.length, cabecalho.length).setValues(dados);
    
    // Formatação condicional por status
    for (let i = 0; i < dados.length; i++) {
      const linhaAtual = tabelaInicio + 1 + i;
      const status = dados[i][1];
      const range = ws.getRange(linhaAtual, 1, 1, cabecalho.length);
      
      if (status === TIPO_DISCREPANCIA.MATCH_OK) {
        range.setBackground('#e6f4ea'); // Verde claro
      } else if (status === TIPO_DISCREPANCIA.SIMULADO_APENAS_SHEETS || 
                 status === TIPO_DISCREPANCIA.DISCIPLINA_APENAS_SHEETS) {
        range.setBackground('#fce8e6'); // Vermelho claro
      } else if (status === TIPO_DISCREPANCIA.SIMULADO_APENAS_DOC || 
                 status === TIPO_DISCREPANCIA.DISCIPLINA_APENAS_DOC) {
        range.setBackground('#e8f0fe'); // Azul claro
      } else {
        range.setBackground('#fff3e0'); // Laranja claro (discrepâncias)
      }
    }
    
    // Destacar células com diferenças específicas
    for (let i = 0; i < dados.length; i++) {
      const linhaAtual = tabelaInicio + 1 + i;
      const status = dados[i][1];
      
      if (status.includes('questões divergente')) {
        ws.getRange(linhaAtual, 7).setFontWeight('bold').setFontColor('#d32f2f');
        ws.getRange(linhaAtual, 8).setFontWeight('bold').setFontColor('#d32f2f');
      }
      if (status.includes('Numeração divergente')) {
        ws.getRange(linhaAtual, 9).setFontWeight('bold').setFontColor('#e65100');
        ws.getRange(linhaAtual, 10).setFontWeight('bold').setFontColor('#e65100');
      }
      if (status.includes('Professor divergente')) {
        ws.getRange(linhaAtual, 11).setFontWeight('bold').setFontColor('#6a1b9a');
        ws.getRange(linhaAtual, 12).setFontWeight('bold').setFontColor('#6a1b9a');
      }
      if (status.includes('Bloco divergente')) {
        ws.getRange(linhaAtual, 5).setFontWeight('bold').setFontColor('#1565c0');
        ws.getRange(linhaAtual, 6).setFontWeight('bold').setFontColor('#1565c0');
      }
    }
  }
  
  // ==================== FORMATAÇÃO GERAL ====================
  
  // Ajustar larguras de coluna
  ws.setColumnWidth(1, 350); // Simulado
  ws.setColumnWidth(2, 250); // Status
  ws.setColumnWidth(3, 200); // Disciplina Sheets
  ws.setColumnWidth(4, 200); // Disciplina Doc
  ws.setColumnWidth(5, 150); // Bloco Sheets
  ws.setColumnWidth(6, 150); // Bloco Doc
  ws.setColumnWidth(7, 100); // Questões Sheets
  ws.setColumnWidth(8, 100); // Questões Doc
  ws.setColumnWidth(9, 120); // Numeração Sheets
  ws.setColumnWidth(10, 120); // Numeração Doc
  ws.setColumnWidth(11, 180); // Professor Sheets
  ws.setColumnWidth(12, 180); // Professor Doc
  ws.setColumnWidth(13, 100); // Similaridade
  
  // Congelar cabeçalho
  ws.setFrozenRows(tabelaInicio);
  
  // Adicionar filtro
  if (resultados.length > 0) {
    const rangeTotal = ws.getRange(tabelaInicio, 1, resultados.length + 1, cabecalho.length);
    rangeTotal.createFilter();
  }
  
  // Ativar a aba
  ws.activate();
  
  Logger.log(`[Resultados] ${resultados.length} linhas gravadas na aba "${CONFIG.ABA_RESULTADOS}".`);
}

/**
 * Gera o resumo estatístico dos resultados.
 */
function gerarResumo(resultados) {
  const simuladosSheets = new Set();
  const simuladosDoc = new Set();
  const simuladosPareados = new Set();
  
  let ok = 0;
  let comDiscrepancia = 0;
  let apenasSheets = 0;
  let apenasDoc = 0;
  
  for (const r of resultados) {
    if (r.status === TIPO_DISCREPANCIA.MATCH_OK) {
      ok++;
      simuladosSheets.add(r.simulado);
      simuladosDoc.add(r.simulado);
      simuladosPareados.add(r.simulado);
    } else if (r.status === TIPO_DISCREPANCIA.SIMULADO_APENAS_SHEETS) {
      apenasSheets++;
      simuladosSheets.add(r.simulado);
    } else if (r.status === TIPO_DISCREPANCIA.SIMULADO_APENAS_DOC) {
      apenasDoc++;
      simuladosDoc.add(r.simulado);
    } else if (r.status === TIPO_DISCREPANCIA.DISCIPLINA_APENAS_SHEETS) {
      apenasSheets++;
      simuladosSheets.add(r.simulado);
      simuladosPareados.add(r.simulado);
    } else if (r.status === TIPO_DISCREPANCIA.DISCIPLINA_APENAS_DOC) {
      apenasDoc++;
      simuladosDoc.add(r.simulado);
      simuladosPareados.add(r.simulado);
    } else {
      comDiscrepancia++;
      simuladosSheets.add(r.simulado);
      simuladosDoc.add(r.simulado);
      simuladosPareados.add(r.simulado);
    }
  }
  
  return {
    total: resultados.length,
    ok: ok,
    comDiscrepancia: comDiscrepancia,
    apenasSheets: apenasSheets,
    apenasDoc: apenasDoc,
    simuladosSheets: simuladosSheets.size,
    simuladosDoc: simuladosDoc.size,
    simuladosPareados: simuladosPareados.size
  };
}

/**
 * Limpa a aba de resultados.
 */
function limparResultados() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ws = ss.getSheetByName(CONFIG.ABA_RESULTADOS);
  
  if (ws) {
    ws.clear();
    ws.clearFormats();
    SpreadsheetApp.getUi().alert('🗑️ Resultados limpos com sucesso.');
  } else {
    SpreadsheetApp.getUi().alert('ℹ️ Nenhuma aba de resultados encontrada.');
  }
}
/**
 * ============================================================
 * ORQUESTRADOR PRINCIPAL
 * ============================================================
 * Integra todos os módulos e executa o fluxo completo
 * de comparação.
 * ============================================================
 */

/**
 * Executa o fluxo completo de comparação:
 * 1. Extrai dados do Sheets (Fonte A)
 * 2. Extrai dados do Doc (Fonte B) via Gemini
 * 3. Compara as duas fontes
 * 4. Grava resultados formatados
 */
function executarComparacaoCompleta() {
  const ui = SpreadsheetApp.getUi();
  const inicio = new Date();
  
  try {
    // Verificar API Key antes de começar
    getApiKey();
    
    // ==================== ETAPA 1: SHEETS ====================
    Logger.log('========== ETAPA 1: Extração Sheets ==========');
    SpreadsheetApp.getActiveSpreadsheet().toast('Etapa 1/4: Extraindo dados do Sheets...', '🔍 Comparador', -1);
    
    const dadosSheets = extrairDadosSheets();
    Logger.log(`Sheets: ${dadosSheets.length} registros de ${contarSimuladosUnicos(dadosSheets)} simulados.`);
    
    // ==================== ETAPA 2: DOC (IA) ====================
    Logger.log('========== ETAPA 2: Extração Doc (IA) ==========');
    SpreadsheetApp.getActiveSpreadsheet().toast('Etapa 2/4: Extraindo dados do Doc via IA (pode demorar)...', '🔍 Comparador', -1);
    
    const dadosDoc = extrairDadosDoc();
    Logger.log(`Doc: ${dadosDoc.length} registros de ${contarSimuladosUnicos(dadosDoc)} simulados.`);
    
    // ==================== ETAPA 3: COMPARAÇÃO ====================
    Logger.log('========== ETAPA 3: Comparação ==========');
    SpreadsheetApp.getActiveSpreadsheet().toast('Etapa 3/4: Comparando fontes...', '🔍 Comparador', -1);
    
    const resultados = compararFontes(dadosSheets, dadosDoc);
    Logger.log(`Comparação: ${resultados.length} linhas de resultado.`);
    
    // ==================== ETAPA 4: RESULTADOS ====================
    Logger.log('========== ETAPA 4: Gravando Resultados ==========');
    SpreadsheetApp.getActiveSpreadsheet().toast('Etapa 4/4: Gravando resultados...', '🔍 Comparador', -1);
    
    gravarResultados(resultados);
    
    // ==================== CONCLUSÃO ====================
    const duracao = ((new Date() - inicio) / 1000).toFixed(1);
    const resumo = gerarResumo(resultados);
    
    SpreadsheetApp.getActiveSpreadsheet().toast('', '', 1); // Limpar toast
    
    ui.alert(
      '✅ Comparação Concluída!',
      `Tempo total: ${duracao}s\n\n` +
      `📊 RESUMO:\n` +
      `• Total de registros: ${resumo.total}\n` +
      `• ✅ OK (conferem): ${resumo.ok}\n` +
      `• ⚠️ Discrepâncias: ${resumo.comDiscrepancia}\n` +
      `• 🔴 Apenas Sheets: ${resumo.apenasSheets}\n` +
      `• 🔵 Apenas Doc: ${resumo.apenasDoc}\n\n` +
      `Veja a aba "${CONFIG.ABA_RESULTADOS}" para detalhes.`,
      ui.ButtonSet.OK
    );
    
  } catch (e) {
    SpreadsheetApp.getActiveSpreadsheet().toast('', '', 1);
    ui.alert('❌ Erro na Comparação', `${e.message}\n\nVerifique o log para mais detalhes.`, ui.ButtonSet.OK);
    Logger.log(`[ERRO PRINCIPAL] ${e.message}\n${e.stack}`);
  }
}

/**
 * Executa apenas a comparação (usando dados já extraídos do cache).
 */
function executarComparacao() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    // Tentar recuperar do cache
    const cache = CacheService.getScriptCache();
    const sheetsJson = cache.get('dados_sheets');
    const dadosDoc = recuperarDadosDocCache();
    
    if (!sheetsJson || !dadosDoc) {
      ui.alert(
        '⚠️ Dados não encontrados',
        'Execute primeiro as etapas 1 e 2 (Extração Sheets e Doc) ou use "Executar Comparação Completa".',
        ui.ButtonSet.OK
      );
      return;
    }
    
    const dadosSheets = JSON.parse(sheetsJson);
    
    SpreadsheetApp.getActiveSpreadsheet().toast('Comparando fontes...', '🔍 Comparador', -1);
    
    const resultados = compararFontes(dadosSheets, dadosDoc);
    gravarResultados(resultados);
    
    SpreadsheetApp.getActiveSpreadsheet().toast('', '', 1);
    
    const resumo = gerarResumo(resultados);
    ui.alert(
      '✅ Comparação Concluída!',
      `Total: ${resumo.total} | OK: ${resumo.ok} | Discrepâncias: ${resumo.comDiscrepancia}\n` +
      `Apenas Sheets: ${resumo.apenasSheets} | Apenas Doc: ${resumo.apenasDoc}`,
      ui.ButtonSet.OK
    );
    
  } catch (e) {
    ui.alert('❌ Erro', e.message, ui.ButtonSet.OK);
    Logger.log(`[ERRO] ${e.message}\n${e.stack}`);
  }
}
