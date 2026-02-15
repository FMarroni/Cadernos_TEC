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
