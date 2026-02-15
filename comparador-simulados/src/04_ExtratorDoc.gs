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
