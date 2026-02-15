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
