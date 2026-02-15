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
