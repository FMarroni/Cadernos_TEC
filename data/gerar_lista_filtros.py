#!/usr/bin/env python3.11
"""
Script para converter o JSON consolidado em uma lista Python de filtros
para uso no sistema de matching de IA.

Gera dois arquivos:
1. filtros_tec_completo.py - Lista completa (matérias + assuntos)
2. filtros_tec_materias.py - Apenas matérias (para matching mais rápido)
"""

import json
from pathlib import Path

def gerar_lista_filtros():
    """
    Lê o JSON consolidado e gera listas Python de filtros
    """
    print("\n" + "=" * 80)
    print("📝 GERANDO LISTAS DE FILTROS PARA O SISTEMA")
    print("=" * 80)
    
    # Caminho do JSON consolidado
    json_path = Path(__file__).parent / "materias_assuntos_CONSOLIDADO.json"
    
    if not json_path.exists():
        print(f"\n❌ Arquivo não encontrado: {json_path}")
        print("   Copie o arquivo 'materias_assuntos_CONSOLIDADO_*.json' para este diretório")
        print("   e renomeie para 'materias_assuntos_CONSOLIDADO.json'")
        return
    
    print(f"\n[1/4] Carregando dados de: {json_path.name}")
    with open(json_path, 'r', encoding='utf-8') as f:
        materias = json.load(f)
    
    print(f"   ✓ {len(materias)} matérias carregadas")
    
    # Gerar lista de APENAS MATÉRIAS
    print("\n[2/4] Gerando lista de matérias...")
    lista_materias = []
    for materia in materias:
        nome = materia.get('nome', '').strip()
        if nome:
            lista_materias.append(nome)
    
    print(f"   ✓ {len(lista_materias)} matérias únicas")
    
    # Gerar lista COMPLETA (matérias + assuntos)
    print("\n[3/4] Gerando lista completa (matérias + assuntos)...")
    lista_completa = []
    total_assuntos = 0
    
    for materia in materias:
        nome_materia = materia.get('nome', '').strip()
        if nome_materia:
            lista_completa.append(nome_materia)
        
        assuntos = materia.get('assuntos', [])
        for assunto in assuntos:
            nome_assunto = assunto.get('nome', '').strip()
            if nome_assunto:
                lista_completa.append(nome_assunto)
                total_assuntos += 1
    
    print(f"   ✓ {len(lista_completa)} filtros totais ({len(lista_materias)} matérias + {total_assuntos} assuntos)")
    
    # Salvar arquivos Python
    print("\n[4/4] Salvando arquivos...")
    
    # Arquivo 1: Apenas matérias
    output_materias = Path(__file__).parent / "filtros_tec_materias.py"
    with open(output_materias, 'w', encoding='utf-8') as f:
        f.write('"""\n')
        f.write('Lista de MATÉRIAS do TEC Concursos\n')
        f.write('Gerado automaticamente a partir dos dados extraídos\n')
        f.write(f'Total: {len(lista_materias)} matérias\n')
        f.write('"""\n\n')
        f.write('from typing import Final, List\n\n')
        f.write('LISTA_MATERIAS_TEC: Final[List[str]] = [\n')
        for materia in lista_materias:
            # Escapar aspas simples
            materia_escaped = materia.replace("'", "\\'")
            f.write(f"    '{materia_escaped}',\n")
        f.write(']\n')
    
    print(f"   ✅ Salvo: {output_materias.name}")
    
    # Arquivo 2: Lista completa (matérias + assuntos)
    output_completo = Path(__file__).parent / "filtros_tec_completo.py"
    with open(output_completo, 'w', encoding='utf-8') as f:
        f.write('"""\n')
        f.write('Lista COMPLETA de filtros do TEC Concursos (Matérias + Assuntos)\n')
        f.write('Gerado automaticamente a partir dos dados extraídos\n')
        f.write(f'Total: {len(lista_completa)} filtros ({len(lista_materias)} matérias + {total_assuntos} assuntos)\n')
        f.write('\n')
        f.write('ATENÇÃO: Esta lista é muito grande e pode deixar o matching mais lento.\n')
        f.write('Considere usar LISTA_MATERIAS_TEC se o desempenho for um problema.\n')
        f.write('"""\n\n')
        f.write('from typing import Final, List\n\n')
        f.write('LISTA_COMPLETA_FILTROS_TEC: Final[List[str]] = [\n')
        for filtro in lista_completa:
            # Escapar aspas simples
            filtro_escaped = filtro.replace("'", "\\'")
            f.write(f"    '{filtro_escaped}',\n")
        f.write(']\n')
    
    print(f"   ✅ Salvo: {output_completo.name}")
    
    # Estatísticas
    print("\n" + "=" * 80)
    print("📊 ESTATÍSTICAS")
    print("=" * 80)
    print(f"Matérias: {len(lista_materias)}")
    print(f"Assuntos: {total_assuntos}")
    print(f"Total de filtros: {len(lista_completa)}")
    
    print("\n🎯 RECOMENDAÇÃO DE USO:")
    print("  • Para matching RÁPIDO: use LISTA_MATERIAS_TEC (143 filtros)")
    print("  • Para matching PRECISO: use LISTA_COMPLETA_FILTROS_TEC (13.486 filtros)")
    
    print("\n✅ Arquivos gerados com sucesso!")
    print(f"📁 Diretório: {Path(__file__).parent}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    gerar_lista_filtros()
