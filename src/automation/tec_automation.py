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
        """
        try:
            self.log("Navegando até a página de login do TEC...")
            self.page.goto("https://www.tecconcursos.com.br/login")
            self.page.wait_for_load_state("domcontentloaded")
            
            self.log("Preenchendo credenciais...")
            self.page.get_by_role("textbox", name="Endereço de e-mail").fill(username)
            self.page.get_by_role("textbox", name="Senha de acesso").fill(password)
            
            self.log("\n" + "="*80)
            self.log("⏸  AÇÃO MANUAL NECESSÁRIA NA JANELA DO NAVEGADOR:")
            self.log("  1. Resolva o CAPTCHA manualmente")
            self.log("  2. Clique no botão 'Entrar no site'")
            self.log("  3. Aguarde até estar logado")
            self.log("  4. Feche a janela 'Playwright Inspector' para continuar")
            self.log("="*80 + "\n")
            
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
            # Usamos o seletor 'name=' que o seu gravador descobriu
            self.page.get_by_role("listitem", name=re.compile(nome_filtro, re.IGNORECASE)).click(timeout=10000)
            self.page.wait_for_timeout(1000) 
            return True
        except Exception:
            # Fallback para o método antigo se 'name=' falhar
            self.log(f"  > (Fallback) Tentando clicar por texto: '{nome_filtro}'")
            try:
                self.page.get_by_text(nome_filtro, exact=True).first.click(timeout=5000)
                self.page.wait_for_timeout(1000)
                return True
            except Exception as e:
                self.log(f"  ✗ Erro ao clicar na categoria '{nome_filtro}': {e}")
                return False


    def _pesquisar_e_selecionar_item(self, item_busca: str) -> bool:
        """
        Ativa a busca, digita o termo e clica no item correspondente na lista de resultados.
        Refatorado com a lógica descoberta pelo Playwright Inspector.
        """
        try:
            # Passo 1: Ativar o campo de busca (se ainda não estiver visível)
            self.log(f"    - Ativando busca para: '{item_busca}'")
            input_busca = self.page.get_by_role("textbox", name="Digite pelo menos três")
            
            if not input_busca.is_visible():
                self.page.get_by_text("Pesquisar por nome").first.click(timeout=5000)
                input_busca.wait_for(state="visible", timeout=5000)
                
            # Passo 2: Limpar e digitar o termo no campo de busca
            input_busca.fill("")
            self.page.wait_for_timeout(200) # Pausa curta para o Angular limpar
            input_busca.fill(item_busca)
        
            # Passo 3: Aguarda aparecer um resultado que CONTENHA o texto de busca.
            self.log(f"    - Aguardando resultado que contenha '{item_busca}'...")
            
            # --- CORREÇÃO FINAL (v6) - BASEADA NA SUA OBSERVAÇÃO ---
            # Filtra os resultados para EXCLUIR os itens que são "pastas"
            # (que contêm o texto "Assuntos contendo").
            resultado_locator = self.page.get_by_role("listitem").filter(
                has_text=item_busca
            ).filter(
                has_not_text="Assuntos contendo"
            )
            
            # Espera o item (não-pasta) aparecer na lista de resultados
            self.log(f"    - Esperando pelo PRIMEIRO item (não-pasta) que bate com a busca...")
            resultado_locator.first.wait_for(state="visible", timeout=10000) 
            
            # Passo 4: Clicar no ícone de adicionar (span.nth(3))
            self.log(f"    - Selecionando item '{item_busca}' da lista...")
            resultado_locator.first.locator("span").nth(3).click(timeout=5000)
        
            # O log anterior mostrou que o clique foi sucesso, mas a espera 'hidden' falhou.
            # Agora só esperamos um tempo fixo para o Angular processar.
            self.page.wait_for_timeout(500) # Meio segundo
            
            self.log(f"    ✓ '{item_busca}' selecionado com sucesso")
            
            # Passo 5: Corrigindo o Bug do Loop
            # Clica em "Voltar" para resetar o painel para a próxima busca.
            try:
                self.page.get_by_role("link", name="Voltar").click(timeout=1000)
            except Exception as e:
                self.log(f"    - (Info) Não foi necessário clicar em 'Voltar'.")
                
            return True
            
        except Exception as e:
            # Tratamento de erro e log
            self.log(f"    ✗ Erro ao buscar/selecionar '{item_busca}': {e}")
            try:
                # Tenta resetar o estado mesmo se falhar
                self.page.get_by_role("link", name="Voltar").click(timeout=1000)
            except Exception: 
                pass # Ignora erros ao tentar resetar
            return False

    def _selecionar_item_lista_simples(self, texto_item: str):
        """
        Clica diretamente no ÍCONE de um item de lista (para Ano e Escolaridade).
        """
        try:
            # Esta é a lógica CORRETA (clicar no ícone, não no texto)
            self.log(f"    - Selecionando item de lista: '{texto_item}'")
            list_item = self.page.get_by_role("listitem").filter(has_text=texto_item)
            list_item.locator("span").nth(3).click(timeout=5000)

            # Removemos o fallback (que causava o "seleciona/cancela")
            # e a espera 'hidden' (que causava o timeout).
            self.page.wait_for_timeout(500) # Pausa para o Angular processar
            
            self.log(f"    ✓ '{texto_item}' selecionado")
            return True
        except Exception as e:
            # Se a lógica principal (clicar no ícone) falhar, logamos o erro.
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
            
            if materias and self._clicar_filtro_lateral("Matéria e assunto"):
                for materia in materias:
                    self._pesquisar_e_selecionar_item(materia)
            
            if self.filtros_padrao.get("bancas") and self._clicar_filtro_lateral("Banca"):
                for banca in self.filtros_padrao["bancas"]:
                    self._pesquisar_e_selecionar_item(banca)
            
            if self.filtros_padrao.get("anos") and self._clicar_filtro_lateral("Ano"):
                for ano in self.filtros_padrao["anos"]:
                    self._selecionar_item_lista_simples(str(ano))
            
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
            self.page.get_by_role("textbox", name="Nome do caderno").fill(nome_caderno)
            self.page.wait_for_timeout(500)
            
            gerar_btn = self.page.get_by_role("button", name="Gerar Caderno")
            
            # Removemos as chamadas 'wait_for' redundantes 
            # O .click() do Playwright já espera automaticamente.
            self.log("    - Clicando em 'Gerar Caderno' (aguardando ficar pronto)...")
            gerar_btn.click(timeout=15000)
            
            # [4/4] Aguardar criação
            self.log("\n[4/4] Aguardando criação do caderno...")
            # Espera por uma URL que contenha /cadernos/ e não seja /novo/
            self.page.wait_for_url(re.compile(r".*/cadernos/(?!novo)"), timeout=30000)
            url_final = self.page.url
            
            self.log(f"\n✅ CADERNO CRIADO COM SUCESSO! URL: {url_final}")
            return {
                "success": True,
                "url": url_final,
                "nome": nome_caderno
            }
                
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

