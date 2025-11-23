# src/reporting/report_generator.py (VERSÃO FINAL - CABEÇALHO COMPLETO)

import os
from datetime import datetime
from typing import List, Dict, Any, Callable

class ReportGenerator:
    def __init__(self, log_callback: Callable[..., None]):
        self.log = log_callback
        self.template_path = os.path.join("templates", "template_relatorio.html") # Usando HTML puro agora
        self.output_dir = "relatorios"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(self, user_data: Dict[str, Any], resultados: List[Dict[str, Any]]) -> str:
        """
        Gera um relatório HTML rico com os resultados.
        """
        self.log("Gerador de Relatório HTML inicializado.")
        self.log("Iniciando geração do relatório em HTML...")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        # Extrai ID do curso se possível para o nome do arquivo
        curso_id = "Curso"
        try:
            if 'id=' in user_data.get('course_url', ''):
                curso_id = user_data['course_url'].split('id=')[-1]
        except: pass
        
        filename = f"Relatorio_Cadernos_{curso_id}_{timestamp}.html"
        filepath = os.path.join(self.output_dir, filename)

        # --- Extração de Filtros para o Cabeçalho ---
        # Garante que apareça "Nenhum" se estiver vazio
        banca_display = user_data.get('banca') or "Todas"
        ano_display = user_data.get('ano') or "Todos"
        
        # Escolaridade vem como string da GUI nova
        esc_raw = user_data.get('escolaridade', '')
        escolaridade_display = esc_raw if esc_raw else "Todas"

        # Estatísticas
        total = len(resultados)
        sucessos = sum(1 for r in resultados if r.get('success'))
        falhas = total - sucessos

        # --- Montagem do HTML ---
        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-br">
        <head>
            <meta charset="UTF-8">
            <title>Relatório de Cadernos TEC</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f4f4f9; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                .stats-box {{ display: flex; gap: 20px; margin-bottom: 20px; }}
                .stat {{ background: #ecf0f1; padding: 15px; border-radius: 5px; flex: 1; text-align: center; }}
                .stat strong {{ display: block; font-size: 24px; color: #2c3e50; }}
                .filters-box {{ background: #e8f4f8; padding: 15px; border-radius: 5px; margin-bottom: 30px; border-left: 5px solid #3498db; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #34495e; color: white; }}
                tr:hover {{ background-color: #f1f1f1; }}
                .status-ok {{ color: #27ae60; font-weight: bold; }}
                .status-fail {{ color: #c0392b; font-weight: bold; }}
                a {{ color: #3498db; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Relatório de Geração de Cadernos</h1>
                
                <div class="filters-box">
                    <h3>⚙️ Filtros Aplicados</h3>
                    <p><strong>Banca:</strong> {banca_display}</p>
                    <p><strong>Ano:</strong> {ano_display}</p>
                    <p><strong>Escolaridade:</strong> {escolaridade_display}</p>
                    <p><strong>Data:</strong> {datetime.now().strftime("%d/%m/%Y às %H:%M")}</p>
                </div>

                <div class="stats-box">
                    <div class="stat"><strong>{total}</strong> Aulas Processadas</div>
                    <div class="stat" style="color: #27ae60;"><strong>{sucessos}</strong> Cadernos Criados</div>
                    <div class="stat" style="color: #c0392b;"><strong>{falhas}</strong> Falhas</div>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>Aula (Nome do Caderno)</th>
                            <th>Status</th>
                            <th>Questões</th>
                            <th width="30%">Filtros Usados (IA)</th>
                            <th>Link / Erro</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for r in resultados:
            nome = r.get('nome_caderno', 'Sem Nome')
            status = "✅ Sucesso" if r.get('success') else "❌ Falha"
            status_class = "status-ok" if r.get('success') else "status-fail"
            qtd = r.get('num_questoes', 0)
            
            # Filtros IA (Assuntos)
            filtros = r.get('filtros_ia', 'N/A')
            
            # Link ou Erro
            if r.get('success'):
                link = r.get('url', '#')
                acao = f'<a href="{link}" target="_blank">Abrir Caderno 🔗</a>'
            else:
                erro = r.get('erro', 'Erro desconhecido')
                acao = f'<span style="color:red">{erro}</span>'

            html_content += f"""
                        <tr>
                            <td>{nome}</td>
                            <td class="{status_class}">{status}</td>
                            <td>{qtd}</td>
                            <td style="font-size: 0.9em; color: #555;">{filtros}</td>
                            <td>{acao}</td>
                        </tr>
            """

        html_content += """
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            self.log("✅ RELATÓRIO FINAL GERADO COM SUCESSO!")
            self.log(f"Arquivo salvo em: {filepath}")
            return filepath
        except Exception as e:
            self.log(f"❌ Erro ao salvar relatório HTML: {e}")
            return None