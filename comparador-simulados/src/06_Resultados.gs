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
