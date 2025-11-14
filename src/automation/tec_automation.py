# Ficheiro: src/automation/tec_automation.py
# (VERSÃO 14)

import re
import traceback
from typing import List, Dict, Any, Callable
from playwright.sync_api import Page, expect

class TecAutomationPerfeito:
    """
    Responsável por toda a automação no site TEC Concursos.
    Usa o log_callback injetado para reportar o progresso para a GUI.
    """

    def __init__(self, page: Page, log_callback: Callable[..., None], filtros_padrao: Dict = None):
        self.page = page
        self.log = log_callback
        self.filtros_padrao = filtros_padrao or {}

    def _traduzir_erro(self, erro_tecnico: str) -> str:
        """Converte um erro técnico do Playwright em algo legível."""
        self.log(f"    (Traduzindo erro): {erro_tecnico}")
        
        if "Timeout" in erro_tecnico:
            if "Gerar Caderno" in erro_tecnico or "to_be_enabled" in erro_tecnico:
                return "Não foram encontradas questões (botão 'Gerar' permaneceu desativado)."
            if "wait_for_url" in erro_tecnico:
                return "O TEC demorou demais para criar o caderno. Tente novamente."
            if "listitem" in erro_tecnico or "pesquisar" in erro_tecnico:
                return "Não foi possível encontrar/clicar em um item de filtro (ex: banca/matéria)."
            if "filtros-selecionados--resumo" in erro_tecnico or "#caderno-novo" in erro_tecnico:
                 return "Falha ao ler o contador de questões (elemento não encontrado)."
            return "O site demorou muito para responder (Timeout)."
            
        if "ERR_CONNECTION_REFUSED" in erro_tecnico:
            return "Não foi possível conectar ao TEC. Verifique a internet."
        
        if "invalid literal for int()" in erro_tecnico:
            return f"Erro ao ler o contador (texto inesperado: {erro_tecnico.split(':')[-1].strip()})"

        return erro_tecnico[:100] + "..."

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
            self.page.get_by_role("listitem", name=re.compile(nome_filtro, re.IGNORECASE)).click(timeout=10000)
            self.page.wait_for_timeout(1000) 
            return True
        except Exception:
            try:
                self.log(f"  > (Fallback) Tentando clicar por texto: '{nome_filtro}'")
                self.page.get_by_text(nome_filtro, exact=True).first.click(timeout=5000)
                self.page.wait_for_timeout(1000)
                return True
            except Exception as e:
                self.log(f"  ✗ Erro ao clicar na categoria '{nome_filtro}': {e}")
                return False

    def _pesquisar_e_selecionar_item(self, item_busca: str) -> bool:
        """
        Ativa a busca, digita o termo e clica no item correspondente na lista de resultados.
        """
        try:
            self.log(f"    - Ativando busca para: '{item_busca}'")
            input_busca = self.page.get_by_role("textbox", name="Digite pelo menos três")
            
            if not input_busca.is_visible():
                self.page.get_by_text("Pesquisar por nome").first.click(timeout=5000)
                input_busca.wait_for(state="visible", timeout=5000)
                
            input_busca.fill("")
            self.page.wait_for_timeout(200) 
            input_busca.fill(item_busca)
        
            self.log(f"    - Aguardando resultado que contenha '{item_busca}'...")
            
            resultado_locator = self.page.get_by_role("listitem").filter(
                has_text=item_busca
            ).filter(
                has_not_text="Assuntos contendo"
            )
            
            self.log(f"    - Esperando pelo PRIMEIRO item (não-pasta) que bate com a busca...")
            resultado_locator.first.wait_for(state="visible", timeout=10000) 
            
            self.log(f"    - Selecionando item '{item_busca}' da lista...")
            resultado_locator.first.locator("span").nth(3).click(timeout=5000)
        
            self.page.wait_for_timeout(500) 
            
            self.log(f"    ✓ '{item_busca}' selecionado com sucesso")
            
            try:
                self.page.get_by_role("link", name="Voltar").click(timeout=1000)
            except Exception as e:
                self.log(f"    - (Info) Não foi necessário clicar em 'Voltar'.")
                
            return True
            
        except Exception as e:
            self.log(f"    ✗ Erro ao buscar/selecionar '{item_busca}': {e}")
            try:
                self.page.get_by_role("link", name="Voltar").click(timeout=1000)
            except Exception: 
                pass 
            return False

    def _selecionar_item_lista_simples(self, texto_item: str):
        """
        Clica diretamente no ÍCONE de um item de lista (para Ano e Escolaridade).
        """
        try:
            self.log(f"    - Selecionando item de lista: '{texto_item}'")
            list_item = self.page.get_by_role("listitem").filter(has_text=texto_item)
            list_item.locator("span").nth(3).click(timeout=5000)

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
        num_questoes = 0 # Inicializa a contagem
        
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
            
            # Espera os filtros serem aplicados e a contagem atualizar
            self.page.wait_for_timeout(2000) 
            
            # --- [2.5/4] CAPTURANDO CONTAGEM (LÓGICA VERIFICADA) ---
            self.log("\n[2.5/4] Capturando contagem de questões...")
            try:
                # 1. Usando o seletor exato que você encontrou na inspeção
                selector_exato_do_contador = "#caderno-novo > div > div > div.gerador-caderno-novo > div > div.gerador-conteudo.ng-scope.ng-isolate-scope > div > div.ng-scope.ng-isolate-scope > div.somente-desktop > div > div > div > div.gerador-filtrador.somente-desktop > div.gerador-filtrador-rodape > div.gerador-filtrador-conteudo-rodape-informacoes > div.gerador-filtrador-resultado.ng-isolate-scope > span > span > strong"
                contador_locator = self.page.locator(selector_exato_do_contador)
                
                # 2. Espera que ele esteja visível
                contador_locator.wait_for(state="visible", timeout=15000)
                
                # 3. Lê o número
                texto_contador = contador_locator.inner_text().strip().lower()
                
                # Correção V12 (trata a palavra "uma")
                if texto_contador == "uma":
                    num_questoes = 1
                elif texto_contador == "nenhuma":
                    num_questoes = 0
                else:
                    num_questoes = int(texto_contador.replace(".", "")) 
                
                if num_questoes == 0:
                    self.log("❌ 0 questões encontradas. Interrompendo este caderno.")
                    erro_msg = "Não foram encontradas questões"
                    return {
                        "success": False,
                        "url": self.page.url,
                        "nome": nome_caderno,
                        "erro": erro_msg,
                        "num_questoes": 0,
                        "filtros_usados": materias
                    }
                else:
                    self.log(f"    - ✅ {num_questoes} questões encontradas. Prosseguindo...")
                    
            except Exception as e:
                erro_str_tecnico = str(e)
                self.log(f"    - ⚠️ Erro ao ler contador de questões: {erro_str_tecnico}")
                self.log("    - (Assumindo 0 questões e falhando este caderno por segurança).")
                return {
                    "success": False,
                    "url": self.page.url,
                    "nome": nome_caderno,
                    "erro": self._traduzir_erro(erro_str_tecnico),
                    "num_questoes": 0,
                    "filtros_usados": materias
                }
            # --- FIM DA VERIFICAÇÃO ---

            # [3/4] Preenchimento do nome e geração
            self.log("\n[3/4] Preenchendo nome e gerando caderno...")
            self.page.get_by_role("textbox", name="Nome do caderno").fill(nome_caderno)
            self.page.wait_for_timeout(500)
            
            gerar_btn = self.page.get_by_role("button", name="Gerar Caderno")
            
            # Espera o botão ficar ATIVADO (sabemos que num_questoes > 0)
            expect(gerar_btn).to_be_enabled(timeout=10000)
            
            self.log("    - Clicando em 'Gerar Caderno' (agora que está ativado)...")
            gerar_btn.click(timeout=5000)
            
            # [4/4] Aguardar criação
            self.log("\n[4/4] Aguardando criação do caderno...")
            self.page.wait_for_url(re.compile(r".*/cadernos/(?!novo)"), timeout=30000)
            url_final = self.page.url
            
            # --- BLOCO REMOVIDO (V14) ---
            # A verificação de contagem final foi removida
            # conforme sua solicitação.
            # --- FIM DO BLOCO REMOVIDO ---

            self.log(f"\n✅ CADERNO CRIADO COM SUCESSO! URL: {url_final}")
            return {
                "success": True,
                "url": url_final,
                "nome": nome_caderno,
                "num_questoes": num_questoes, # Usa o número do Passo 2.5
                "filtros_usados": materias
            }
                
        except Exception as e:
            erro_str = str(e)
            self.log(f"\n❌ ERRO GERAL AO CRIAR CADERNO '{nome_caderno}': {erro_str}")
            self.log(traceback.format_exc()) # Manter o log técnico
            erro_traduzido = self._traduzir_erro(erro_str)
            return {
                "success": False,
                "url": self.page.url,
                "nome": nome_caderno,
                "erro": erro_traduzido, # <-- ERRO LIMPO
                "num_questoes": num_questoes, # (Pode ser 0 se falhou antes)
                "filtros_usados": materias
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