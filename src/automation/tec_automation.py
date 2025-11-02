# Ficheiro: src/automation/tec_automation.py

import re
from typing import List, Dict, Any, Callable
from playwright.sync_api import Page

class TecAutomationPerfeito:
    """
    Responsável por toda a automação no site TEC Concursos.
    Usa o log_callback injetado para reportar o progresso para a GUI.
    """

    def __init__(self, page: Page, log_callback: Callable[..., None], filtros_padrao: Dict = None):
        """
        Inicializa o robô do TEC Concursos.
        
        Args:
            page: A página do Playwright que será controlada.
            log_callback (Callable): Função da GUI para enviar mensagens de log.
            filtros_padrao: Dicionário com filtros padrão (bancas, anos, escolaridades).
        """
        self.page = page
        self.log = log_callback
        self.filtros_padrao = filtros_padrao or {}

    def login(self, username: str, password: str) -> bool:
        """
        Preenche as credenciais e pausa para o usuário completar o login (CAPTCHA).
        
        Returns:
            True se o login foi confirmado pelo operador, False caso contrário.
        """
        try:
            self.log("Navegando até a página de login do TEC...")
            self.page.goto("https://www.tecconcursos.com.br/login")
            self.page.wait_for_load_state("domcontentloaded")
            
            self.log("Preenchendo credenciais...")
            self.page.get_by_role("textbox", name="Endereço de e-mail").fill(username)
            self.page.get_by_role("textbox", name="Senha de acesso").fill(password)
            
            # Envia as instruções de ação manual para o log da GUI
            self.log("\n" + "="*80)
            self.log("⏸  AÇÃO MANUAL NECESSÁRIA NA JANELA DO NAVEGADOR:")
            self.log("  1. Resolva o CAPTCHA manualmente")
            self.log("  2. Clique no botão 'Entrar no site'")
            self.log("  3. Aguarde até estar logado")
            self.log("  4. Feche a janela 'Playwright Inspector' para continuar")
            self.log("="*80 + "\n")
            
            # page.pause() abre o inspetor do Playwright e pausa a execução
            # A automação continuará quando o usuário fechar o inspetor.
            self.page.pause()
            
            self.log("\n✅ Login confirmado pelo operador. Prosseguindo...")
            return True
            
        except Exception as e:
            self.log(f"\n❌ ERRO NO LOGIN: {e}")
            return False

    def _clicar_filtro_lateral(self, nome_filtro: str) -> bool:
        """
        Clica em uma categoria de filtro na barra lateral esquerda.
        """
        try:
            self.log(f"  > Clicando na categoria de filtro: '{nome_filtro}'")
            self.page.get_by_text(nome_filtro, exact=True).first.click(timeout=10000)
            self.page.wait_for_timeout(1000) # Substitui time.sleep(1)
            return True
        except Exception as e:
            self.log(f"  ✗ Erro ao clicar na categoria '{nome_filtro}': {e}")
            return False

    def _pesquisar_e_selecionar_item(self, item_busca: str):
        """
        Ativa a busca, digita o termo e clica no item de lista correspondente.
        VERSÃO CORRIGIDA: Usa a lógica descoberta pelo Playwright Codegen (span.nth(3)).
        """
        try:
            # Passo 1: Ativar o campo de busca
            self.log(f"    - Ativando busca para: '{item_busca}'")
            self.page.get_by_text("Pesquisar por nome").first.click(timeout=5000)
            self.page.wait_for_timeout(500)
            
            # Passo 2: Localizar o campo de texto e digitar o termo
            input_busca = self.page.get_by_role("textbox", name="Digite pelo menos três")
            input_busca.fill("")  # Limpa o campo
            self.page.wait_for_timeout(200)
            input_busca.fill(item_busca)
            self.page.wait_for_timeout(1500) # Aguarda os resultados aparecerem
            
            # Passo 3: LÓGICA CORRIGIDA - Clicar no span dentro do listitem
            # O nth(3) representa o 4º span (ícone de adicionar)
            self.log(f"    - Selecionando item '{item_busca}' da lista...")
            
            listitem = self.page.get_by_role("listitem").filter(
                has_text=re.compile(f"^{re.escape(item_busca)}$", re.IGNORECASE)
            )
            
            listitem.locator("span").nth(3).click(timeout=5000)
            
            self.page.wait_for_timeout(500)
            self.log(f"    ✓ '{item_busca}' selecionado com sucesso")
            return True
            
        except Exception as e:
            self.log(f"    ✗ Erro ao buscar e selecionar '{item_busca}': {e}")
            self.log(f"    Detalhes: Tentando localizar listitem com texto '{item_busca}' e clicar no span.nth(3)")
            return False

    def _selecionar_item_lista_simples(self, texto_item: str):
        """
        Clica diretamente em um item de lista (para Ano e Escolaridade).
        """
        try:
            self.page.get_by_text(texto_item, exact=True).first.click(timeout=5000)
            self.page.wait_for_timeout(500)
            self.log(f"    ✓ '{texto_item}' selecionado")
            return True
        except Exception as e:
            self.log(f"    ✗ Erro ao selecionar item de lista '{texto_item}': {e}")
            return False

    def create_notebook(self, nome_caderno: str, materias: List[str]) -> Dict[str, Any]:
        """
        Cria um único caderno de questões usando a arquitetura de filtragem consolidada.
        """
        self.log(f"\n{'='*80}\nCriando caderno: {nome_caderno[:70]}...")
        
        try:
            # [1/4] Navegação
            self.log("[1/4] Navegando para página de criação...")
            self.page.goto("https://www.tecconcursos.com.br/questoes/cadernos/novo")
            self.page.wait_for_selector('button:has-text("Gerar Caderno")', timeout=20000)
            
            # [2/4] Aplicação de filtros
            self.log("\n[2/4] Aplicando filtros...")
            
            # Filtro de Matéria (usa busca)
            if materias and self._clicar_filtro_lateral("Matéria e assunto"):
                for materia in materias:
                    self._pesquisar_e_selecionar_item(materia)
            
            # Filtro de Banca (usa busca)
            if self.filtros_padrao.get("bancas") and self._clicar_filtro_lateral("Banca"):
                for banca in self.filtros_padrao["bancas"]:
                    self._pesquisar_e_selecionar_item(banca)
            
            # Filtro de Ano (lista simples)
            if self.filtros_padrao.get("anos") and self._clicar_filtro_lateral("Ano"):
                for ano in self.filtros_padrao["anos"]:
                    self._selecionar_item_lista_simples(str(ano))
            
            # Filtro de Escolaridade (lista simples)
            if self.filtros_padrao.get("escolaridades") and self._clicar_filtro_lateral("Escolaridade"):
                mapa_escolaridade = {
                    "Médio": "Ensino Médio",
                    "Superior": "Superior"
                }
                for esc in self.filtros_padrao["escolaridades"]:
                    texto_escolaridade = mapa_escolaridade.get(esc, esc)
                    self._selecionar_item_lista_simples(texto_escolaridade)
            
            self.page.wait_for_timeout(2000)
            
            # [3/4] Preenchimento do nome e geração
            self.log("\n[3/4] Preenchendo nome e gerando caderno...")
            self.page.locator('input[ng-model*="nomeCaderno"]').first.fill(nome_caderno)
            self.page.wait_for_timeout(500)
            
            gerar_btn = self.page.get_by_text("Gerar Caderno", exact=True)
            gerar_btn.wait_for(state="enabled", timeout=15000)
            gerar_btn.click()
            
            # [44] Aguardar criação
            self.log("\n[4/4] Aguardando criação do caderno...")
            self.page.wait_for_url("**/cadernos/*", timeout=30000)
            url_final = self.page.url
            
            if "cadernos/" in url_final and "novo" not in url_final:
                self.log(f"\n✅ CADERNO CRIADO COM SUCESSO! URL: {url_final}")
                return {
                    "success": True,
                    "url": url_final,
                    "nome": nome_caderno
                }
            else:
                raise Exception("A URL final não corresponde a um caderno criado.")
                
        except Exception as e:
            self.log(f"\n❌ ERRO GERAL AO CRIAR CADERNO '{nome_caderno}': {e}")
            return {
                "success": False,
                "url": self.page.url,
                "nome": nome_caderno,
                "erro": str(e)
            }

    def criar_multiplos_cadernos(self, lista_aulas: List[Dict]) -> List[Dict]:
        """
        Orquestra a criação de múltiplos cadernos em sequência.
        """
        resultados = []
        total = len(lista_aulas)
        
        self.log(f"\n{'='*80}\nINICIANDO CRIAÇÃO DE {total} CADERNOS\n{'='*80}")
        
        for i, aula in enumerate(lista_aulas, 1):
            self.log(f"\n\n{'#'*80}\n# CADERNO {i}/{total}: {aula.get('nome_caderno', 'Sem nome')[:70]}\n{'#'*80}")
            
            resultado = self.create_notebook(
                nome_caderno=aula.get("nome_caderno", ""),
                materias=aula.get("materias", [])
            )
            
            resultados.append(resultado)
            
            if i < total:
                self.log(f"\nAguardando 3 segundos antes do próximo caderno...")
                self.page.wait_for_timeout(3000)
        
        return resultados
