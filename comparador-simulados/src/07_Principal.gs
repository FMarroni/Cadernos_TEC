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
