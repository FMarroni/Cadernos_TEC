# src/automation/tec_automation.py (CORRIGIDO - KEYERROR RESOLVIDO)

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

    def _selecionar_item(self, item):
        """
        Método genérico para Bancas, Matérias e Assuntos.
        REFINADO COM SELETORES DO USUÁRIO PARA EVITAR SELEÇÃO DE PASTA.
        """
        try:
            self.log(f"    - Buscando: '{item}'")
            
            # 1. Tenta selecionar direto se já estiver visível na lista (comum para Anos/Bancas Populares)
            try:
                # Tenta clicar especificamente no texto do nome
                self.page.locator("span.arvore-item-nome").filter(has_text=item).first.click(timeout=2000)
                self.log(f"    ✓ '{item}' selecionado (lista direta)")
                return True
            except:
                pass 

            # 2. Usa a caixa de busca
            input_busca = self.page.get_by_role("textbox", name="Digite pelo menos três")
            if not input_busca.is_visible():
                self.page.get_by_text("Pesquisar por nome").first.click()
            
            # Limpa e preenche
            input_busca.fill("")
            input_busca.fill(item)
            self.page.wait_for_timeout(1500) # Espera a árvore ser filtrada
            
            # --- LÓGICA DE SELEÇÃO COM SELETORES ESPECÍFICOS ---
            
            # O seletor base para a área de resultados da busca (árvore)
            base_arvore = "div.arvore-wrapper > div > ul"
            
            # Localiza todos os spans com o nome do item
            candidatos = self.page.locator(f"{base_arvore} span.arvore-item-nome").filter(has_text=item).all()
            
            alvo_clique = None
            
            if not candidatos:
                self.log(f"    ⚠️ Item '{item}' não encontrado na busca.")
                try: self.page.get_by_role("link", name="Voltar").click(timeout=500)
                except: pass
                return False

            # Se houver mais de um (ex: pasta com mesmo nome do filho), tenta desambiguar
            for cand in candidatos:
                # Verifica se este item tem um botão de "adicionar" (+) associado
                pai = cand.locator("xpath=..") # Sobe um nível
                botao_mais = pai.locator("span.arvore-item-icone-operacao")
                
                if botao_mais.count() > 0 and botao_mais.is_visible():
                    # Achamos! É um item selecionável com o botão +
                    self.log(f"    - Encontrado botão '+' para '{item}'. Clicando nele.")
                    botao_mais.first.click()
                    alvo_clique = "feito" # Marca como resolvido
                    break
            
            # Se não clicou no botão +, tenta clicar no texto do item mais profundo/específico
            if not alvo_clique:
                # Geralmente o último da lista é o mais específico na hierarquia visual
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

            if materias:
                if self._clicar_filtro_lateral("Matéria e assunto"):
                    for m in materias: self._selecionar_item(m)

            if self.filtros_padrao.get("bancas"):
                if self._clicar_filtro_lateral("Banca"):
                    for b in self.filtros_padrao["bancas"]: self._selecionar_item(b)

            if self.filtros_padrao.get("anos"):
                if self._clicar_filtro_lateral("Ano"):
                    for a in self.filtros_padrao["anos"]: self._selecionar_item(str(a))

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
                    "nome_caderno": nome_caderno, # <--- ADICIONADO
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