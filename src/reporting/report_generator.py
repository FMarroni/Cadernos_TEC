# Ficheiro: src/reporting/report_generator.py
# (VERSÃO 7 - Layout de HTML com mais colunas)

import os
import jinja2
from datetime import datetime
from typing import List, Dict, Any, Callable
import traceback

# --- TEMPLATE HTML ATUALIZADO (REQ 1, 2, 3) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Geração de Cadernos</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 1400px; margin: auto; color: #333; }
        h1 { color: #005a9c; border-bottom: 2px solid #005a9c; padding-bottom: 5px; }
        h2 { color: #444; border-bottom: 1px solid #eee; padding-bottom: 3px; }
        .container { background: #fdfdfd; border: 1px solid #ddd; border-radius: 8px; padding: 25px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .filtros { background: #f9f9f9; border: 1px solid #eee; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .filtros p { margin: 5px 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9em; }
        th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; }
        th { background-color: #f4f4f4; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .status-sucesso { color: #28a745; font-weight: bold; }
        .status-falha { color: #dc3545; font-weight: bold; }
        .link-caderno { word-break: break-all; }
        a { color: #007bff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        /* Colunas com largura definida */
        col.col-aula { width: 30%; }
        col.col-status { width: 8%; }
        col.col-qtd { width: 8%; }
        col.col-filtros { width: 30%; }
        col.col-link { width: 24%; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Relatório de Geração de Cadernos</h1>
        
        <div class="filtros">
            <h2>Filtros Aplicados (Padrão)</h2>
            <p><strong>Curso:</strong> {{ nome_curso }}</p>
            <p><strong>Data de Geração:</strong> {{ data_geracao }}</p>
            <hr>
            <p><strong>Bancas:</strong> {{ bancas }}</p>
            <p><strong>Anos:</strong> {{ anos }}</p>
            <p><strong>Escolaridade:</strong> {{ escolaridade }}</p>
        </div>

        <h2>Resultados da Automação</h2>
        <table>
            <colgroup>
                <col class="col-aula">
                <col class="col-status">
                <col class="col-qtd">
                <col class="col-filtros">
                <col class="col-link">
            </colgroup>
            <thead>
                <tr>
                    <th>Aula (Nome do Caderno)</th>
                    <th>Status</th>
                    <th>Qtd. Questões</th>
                    <th>Filtros (IA)</th>
                    <th>Link / Observação</th>
                </tr>
            </thead>
            <tbody>
                {% for item in resultados %}
                <tr>
                    <!-- Aula -->
                    <td>{{ item.nome | e }}</td>
                    
                    <!-- Status -->
                    {% if item.success %}
                        <td class="status-sucesso">✅ Sucesso</td>
                    {% else %}
                        <td class="status-falha">❌ Falha</td>
                    {% endif %}
                    
                    <!-- Qtd. Questões -->
                    <td>{{ item.num_questoes if item.num_questoes > 0 else 'N/A' }}</td>
                    
                    <!-- Filtros (IA) -->
                    <td>{{ item.filtros_ia | e }}</td>
                    
                    <!-- Link / Observação (Erro) -->
                    {% if item.success %}
                        <td class="link-caderno"><a href="{{ item.url }}" target="_blank">{{ item.url }}</a></td>
                    {% else %}
                        <td>{{ item.erro | e }}</td> <!-- Mensagem de erro limpa -->
                    {% endif %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
# --- FIM DO TEMPLATE ---

class ReportGenerator:
    """
    Responsável por gerar o relatório final em .html usando um template Jinja2.
    """

    def __init__(self, log_callback: Callable[..., None]):
        """
        Inicializa o gerador de relatório.
        """
        self.log = log_callback
        self.log("Gerador de Relatório HTML inicializado.")
        
        try:
            # Carrega o template Jinja2 a partir da string
            self.template = jinja2.Template(HTML_TEMPLATE)
        except Exception as e:
            self.log(f"❌ ERRO CRÍTICO: Falha ao carregar template Jinja2 incorporado: {e}")
            raise

    def generate_report(self, user_data: Dict[str, Any], resultados: List[Dict[str, Any]], output_dir: str = "relatorios") -> str:
        """
        Gera o relatório .html preenchendo o template com os dados.
        """
        self.log(f"Iniciando geração do relatório em HTML...")
        
        try:
            course_id = user_data.get('course_url', 'ID_DESCONHECIDO').split('id=')[-1]

            context = {
                "nome_curso": f"Curso ID: {course_id}",
                "data_geracao": datetime.now().strftime("%d/%m/%Y às %H:%M:%S"),
                "bancas": user_data.get("report_bancas", "N/A") or "N/A",
                "anos": user_data.get("report_anos", "N/A") or "N/A",
                "escolaridade": user_data.get("report_escolaridade", "N/A") or "N/A",
                "resultados": resultados # A lista já vem formatada pelo Orquestrador
            }
            
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                self.log(f"Pasta de relatórios criada em: {output_dir}")

            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            output_filename = f"Relatorio_Cadernos_{course_id}_{timestamp}.html"
            output_path = os.path.join(output_dir, output_filename)

            html_content = self.template.render(context)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            absolute_path = os.path.abspath(output_path)
            
            self.log("\n" + "="*80)
            self.log(f"✅ RELATÓRIO FINAL GERADO COM SUCESSO!")
            self.log(f"Arquivo salvo em: {absolute_path}")
            self.log("="*80)
            
            return absolute_path

        except Exception as e:
            self.log(f"❌ ERRO CRÍTICO ao gerar relatório HTML: {e}")
            self.log(traceback.format_exc())
            return None