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
