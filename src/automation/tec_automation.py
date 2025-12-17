# src/automation/tec_automation.py

import re
import traceback
from typing import List, Dict, Any, Callable
from playwright.sync_api import Page, expect

class TecAutomationPerfeito:
    def __init__(self, page: Page, log_callback: Callable[..., None], filtros_padrao: Dict = None):
        self.page = page
        self.log = log_callback
        self.filtros_padrao = filtros_padrao or {}

    def login(self, username, password):
        try:
            self.log("Login no TEC...")
            self.page.goto("https://www.tecconcursos.com.br/login")
            self.page.get_by_role("textbox", name="Endereço de e-mail").fill(username)
            self.page.get_by_role("textbox", name="Senha de acesso").fill(password)
            
            self.log("⏸ PAUSA PARA CAPTCHA. Resolva e clique em Entrar.")
            self.page.pause()
            return True
        except Exception as e:
            self.log(f"❌ Erro Login: {e}")
            return False

    def _clicar_filtro_lateral(self, nome):
        try:
            self.log(f"  > Filtro: '{nome}'")
            # Tenta clicar no filtro lateral pelo nome (ex: "Área", "Banca", "Ano")
            self.page.get_by_role("listitem", name=re.compile(nome, re.IGNORECASE)).click(timeout=5000)
            self.page.wait_for_timeout(1000)
            return True
        except:
            try:
                self.log(f"    (Tentando clique alternativo no filtro '{nome}')")
                self.page.locator(f"li:has-text('{nome}')").first.click(timeout=3000)
                self.page.wait_for_timeout(1000)
                return True
            except:
                return False

    def _selecionar_area_especifica(self, item_original: str):
        """
        Método EXCLUSIVO para o filtro de ÁREA.
        Lógica: 
        1. Cria um filtro flexível (Regex) para aceitar aspas simples ou duplas.
        2. Tenta clicar no item.
        3. Se não achar, expande a pasta pai e tenta novamente.
        """
        self.log(f"    - Tentando selecionar Área: '{item_original}'")
        
        # Container da árvore para garantir escopo
        wrapper_selector = "div.arvore-wrapper"
        wrapper = self.page.locator(wrapper_selector)

        # 1. Preparação do Filtro Flexível (Tratamento de Aspas)
        pasta_pai = None
        filter_criteria = item_original # Padrão: texto exato

        # Verifica se segue o padrão "Todo o conteúdo de 'PASTA'"
        match = re.search(r"Todo o conteúdo de '(.+)'", item_original)
        if match:
            pasta_pai = match.group(1)
            # Cria regex que aceita tanto ' quanto " em volta do nome da pasta
            # Ex: aceita "Todo o conteúdo de 'Educação'" E "Todo o conteúdo de "Educação""
            pattern_str = rf"Todo o conteúdo de ['\"]{re.escape(pasta_pai)}['\"]"
            filter_criteria = re.compile(pattern_str)

        # Locator para o ITEM ALVO usando o critério flexível
        item_locator = wrapper.locator("span.arvore-item-nome").filter(has_text=filter_criteria).first

        # TENTATIVA 1: Clique direto (caso já esteja visível)
        if item_locator.is_visible():
            item_locator.click()
            self.log(f"    ✓ '{item_original}' clicado diretamente.")
            return True
        
        # TENTATIVA 2: Expandir pasta pai (Se identificada)
        if pasta_pai:
            self.log(f"    ⚠️ Item alvo não visível. Verificando pasta pai: '{pasta_pai}'...")
            
            # Localiza a pasta pai (busca pelo nome da pasta)
            pasta_locator = wrapper.locator("span.arvore-item-nome").filter(has_text=pasta_pai).first
            
            # Garante que a pasta esteja na tela
            if not pasta_locator.is_visible():
                try: pasta_locator.scroll_into_view_if_needed(timeout=3000)
                except: pass

            if pasta_locator.is_visible():
                # Clica na PASTA para expandir
                pasta_locator.click()
                self.page.wait_for_timeout(1000) # Espera animação da árvore
                
                # Agora tenta achar o item filho novamente com o filtro flexível
                if item_locator.is_visible():
                    item_locator.click()
                    self.log(f"    ✓ '{item_original}' clicado após expansão.")
                    return True
                else:
                    # Se ainda não está visível, tenta rolar para o filho
                    try: 
                        item_locator.scroll_into_view_if_needed(timeout=3000)
                        item_locator.click()
                        self.log(f"    ✓ '{item_original}' clicado após scroll no item expandido.")
                        return True
                    except: pass
            else:
                self.log(f"    ❌ Pasta pai '{pasta_pai}' não encontrada.")
        
        # TENTATIVA 3: Scroll desesperado no item
        try:
            item_locator.scroll_into_view_if_needed(timeout=3000)
            if item_locator.is_visible():
                item_locator.click()
                self.log(f"    ✓ '{item_original}' clicado após scroll forçado.")
                return True
        except: pass

        self.log(f"    ❌ Falha fatal: Não foi possível selecionar '{item_original}'.")
        return False

    def _selecionar_item(self, item):
        """
        Método genérico para Bancas, Matérias, Assuntos (COM BUSCA).
        """
        try:
            self.log(f"    - Buscando: '{item}'")
            
            # 1. Tenta selecionar direto se já estiver visível na lista
            try:
                self.page.locator("span.arvore-item-nome").filter(has_text=item).first.click(timeout=2000)
                self.log(f"    ✓ '{item}' selecionado (lista direta)")
                return True
            except:
                pass 

            # 2. Usa a caixa de busca
            input_busca = self.page.get_by_role("textbox", name="Digite pelo menos três")
            if not input_busca.is_visible():
                # Tenta clicar no ícone de lupa ou texto se o input não estiver visível
                try: self.page.get_by_text("Pesquisar por nome").first.click(timeout=1000)
                except: pass
            
            # Limpa e preenche
            input_busca.fill("")
            input_busca.fill(item)
            self.page.wait_for_timeout(1500) # Espera a árvore ser filtrada
            
            # --- LÓGICA DE SELEÇÃO ---
            base_arvore = "div.arvore-wrapper > div > ul"
            candidatos = self.page.locator(f"{base_arvore} span.arvore-item-nome").filter(has_text=item).all()
            
            alvo_clique = None
            
            if not candidatos:
                self.log(f"    ⚠️ Item '{item}' não encontrado na busca.")
                try: self.page.get_by_role("link", name="Voltar").click(timeout=500)
                except: pass
                return False

            for cand in candidatos:
                # Verifica se este item tem um botão de "adicionar" (+)
                pai = cand.locator("xpath=..")
                botao_mais = pai.locator("span.arvore-item-icone-operacao")
                
                if botao_mais.count() > 0 and botao_mais.is_visible():
                    self.log(f"    - Encontrado botão '+' para '{item}'. Clicando nele.")
                    botao_mais.first.click()
                    alvo_clique = "feito"
                    break
            
            if not alvo_clique:
                self.log(f"    - Clicando no texto do item '{item}' (assumindo o mais específico)")
                candidatos[-1].click()

            self.log(f"    ✓ '{item}' selecionado (busca)")
            
            # Fecha busca se tiver botão voltar
            try: self.page.get_by_role("link", name="Voltar").click(timeout=500)
            except: pass
            
            return True
            
        except Exception as e:
            self.log(f"    ✗ Erro ao selecionar '{item}': {e}")
            try: self.page.get_by_role("link", name="Voltar").click(timeout=500)
            except: pass
            return False

    def _selecionar_escolaridade_exata(self, nivel_texto: str):
        """
        Seleciona a escolaridade usando os SELETORES CSS EXATOS.
        """
        self.log(f"    - Selecionando Escolaridade (Modo Exato): '{nivel_texto}'")
        
        base_selector = "#caderno-novo > div > div > div.gerador-caderno-novo > div > div.gerador-conteudo.ng-scope.ng-isolate-scope > div > div.ng-scope.ng-isolate-scope > div.gerador-conteudo-canvas.gerador-box.ng-class\\:\\{\\'resize\\'\\:.vm\\.resizeBuscador.\\} > div > div.ng-isolate-scope.caixaBusca > div > div.arvore-wrapper > div > ul"

        mapa_seletores = {
            "Doutorado": f"{base_selector} > li", 
            "Ensino Fundamental": f"{base_selector} > li:nth-child(2)",
            "Fundamental": f"{base_selector} > li:nth-child(2)",
            "Ensino Médio": f"{base_selector} > li:nth-child(3)",
            "Médio": f"{base_selector} > li:nth-child(3)",
            "Especialização": f"{base_selector} > li:nth-child(4)",
            "Mestrado": f"{base_selector} > li:nth-child(5)",
            "Superior": f"{base_selector} > li:nth-child(6)",
            "Ensino Superior": f"{base_selector} > li:nth-child(6)"
        }

        seletor_base_item = mapa_seletores.get(nivel_texto)
        
        if not seletor_base_item:
            self.log(f"    ⚠️ Nível '{nivel_texto}' não mapeado. Tentando método genérico.")
            return self._selecionar_item(nivel_texto)

        try:
            seletor_final = f"{seletor_base_item} > div > span.arvore-item-icone-nome-wrap > span.arvore-item-nome"
            self.page.locator(seletor_final).wait_for(state="visible", timeout=5000)
            self.page.locator(seletor_final).click()
            self.log(f"    ✓ '{nivel_texto}' selecionado com sucesso (Seletor Exato).")
            return True
        except Exception as e:
            self.log(f"    ✗ Falha ao clicar no seletor exato para '{nivel_texto}'. Erro: {e}")
            return self._selecionar_item(nivel_texto)

    def create_notebook(self, nome_caderno: str, materias: List[str]) -> Dict:
        self.log(f"\nCriando: {nome_caderno[:50]}...")
        try:
            self.page.goto("https://www.tecconcursos.com.br/questoes/cadernos/novo")
            self.page.wait_for_selector('button:has-text("Gerar Caderno")', timeout=20000)

            # 1. Filtro: Área (USANDO LÓGICA DE EXPANSÃO)
            if self.filtros_padrao.get("areas"):
                if self._clicar_filtro_lateral("Área"): 
                    for area in self.filtros_padrao["areas"]:
                        # Usa o método específico
                        self._selecionar_area_especifica(area)

            # 2. Filtro: Matéria e Assunto
            if materias:
                if self._clicar_filtro_lateral("Matéria e assunto"):
                    for m in materias: self._selecionar_item(m)

            # 3. Filtro: Banca
            if self.filtros_padrao.get("bancas"):
                if self._clicar_filtro_lateral("Banca"):
                    for b in self.filtros_padrao["bancas"]: self._selecionar_item(b)

            # 4. Filtro: Ano
            if self.filtros_padrao.get("anos"):
                if self._clicar_filtro_lateral("Ano"):
                    for a in self.filtros_padrao["anos"]: self._selecionar_item(str(a))

            # 5. Filtro: Escolaridade
            if self.filtros_padrao.get("escolaridades"):
                if self._clicar_filtro_lateral("Escolaridade"):
                    for esc in self.filtros_padrao["escolaridades"]:
                        self._selecionar_escolaridade_exata(esc)

            self.page.wait_for_timeout(2000)

            try:
                contador = self.page.locator(".gerador-filtrador-resultado strong").first
                texto_contador = contador.inner_text().strip().lower()
                if "uma" in texto_contador: num = 1
                elif "nenhuma" in texto_contador: num = 0
                else: num = int(texto_contador.replace(".",""))
            except:
                num = 0

            if num == 0:
                self.log("❌ 0 questões encontradas. Pulando.")
                return {
                    "success": False, 
                    "erro": "0 questões encontradas", 
                    "num_questoes": 0, 
                    "filtros_usados": materias,
                    "nome_caderno": nome_caderno,
                    "url": self.page.url
                }

            self.log(f"✅ {num} questões.")
            self.page.get_by_role("textbox", name="Nome do caderno").fill(nome_caderno)
            
            btn_gerar = self.page.get_by_role("button", name="Gerar Caderno")
            expect(btn_gerar).to_be_enabled(timeout=5000)
            btn_gerar.click()
            self.page.wait_for_url(re.compile(r".*/cadernos/(?!novo)"), timeout=30000)
            
            return {
                "success": True, 
                "url": self.page.url, 
                "nome_caderno": nome_caderno, 
                "num_questoes": num, 
                "filtros_usados": materias
            }

        except Exception as e:
            self.log(f"Erro: {e}")
            return {
                "success": False, 
                "erro": str(e)[:100], 
                "num_questoes": 0, 
                "filtros_usados": materias,
                "nome_caderno": nome_caderno, 
                "url": self.page.url
            }

    def criar_multiplos_cadernos(self, lista_aulas):
        res = []
        total = len(lista_aulas)
        for i, aula in enumerate(lista_aulas, 1):
            self.log(f"\n--- Caderno {i}/{total} ---")
            res.append(self.create_notebook(aula["nome_caderno"], aula["materias"]))
            if i < total: self.page.wait_for_timeout(2000)
        return res