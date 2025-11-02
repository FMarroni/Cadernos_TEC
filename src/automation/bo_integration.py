# Ficheiro: src/automation/bo_integration.py

from typing import List, Callable
from playwright.sync_api import Page

class BoAutomation:
    """
    Responsável por toda a automação no site do Back Office (BO).
    Usa o log_callback injetado para reportar o progresso para a GUI.
    """

    def __init__(self, page: Page, log_callback: Callable[..., None]):
        """
        Inicializa o robô do Back Office.
        
        Args:
            page (Page): A página do Playwright que será controlada.
            log_callback (Callable): Função da GUI para enviar mensagens de log.
        """
        self.page = page
        self.log = log_callback

    def login(self, username, password):
        """
        Preenche as credenciais e pausa para o usuário fazer o login manualmente.
        """
        self.log("Navegando até a página de login do BO...")
        self.page.goto("https://estrategiaconcursos.com.br/adminProf")
        self.page.wait_for_load_state("domcontentloaded")

        self.log("Preenchendo credenciais...")
        self.page.locator('input[name="login"]').fill(username)
        self.page.locator('#txt_senha').fill(password)
        
        # --- Instruções para a GUI ---
        self.log("\n" + "!"*80)
        self.log("!!       O ROBÔ ESTÁ PAUSADO E ESPERANDO       !!")
        self.log("!"*80)
        self.log("\n--- AÇÃO MANUAL NECESSÁRIA NA JANELA DO NAVEGADOR ---")
        self.log("1. CLIQUE NO BOTÃO 'ENTRAR' manualmente.")
        self.log("2. Faça o login completo (resolva CAPTCHA, SMS, etc.).")
        self.log("3. AGUARDE a página principal do Admin carregar.")
        self.log("4. Feche a janela 'Playwright Inspector' para continuar.")
        
        # Pausa a execução e abre o Inspector
        self.page.pause()

        self.log("\nContinuando automação após confirmação do operador...")
        
        self.page.wait_for_load_state("networkidle", timeout=60000)

        self.log("Verificando se o login foi bem-sucedido...")
        try:
            self.page.wait_for_url("**/admin/**", timeout=10000)
            self.log("\n-----------------------------------------")
            self.log("✅ SUCESSO! Login completo e confirmado.")
            self.log("-----------------------------------------")
        except Exception:
            self.log("\n-----------------------------------------")
            self.log("⚠️ AVISO: Não foi possível confirmar a URL final após o login.")
            self.log(f"URL atual: {self.page.url}")
            self.log("-----------------------------------------")

    def get_aulas(self, course_code: str) -> List[str]:
        """Extrai os nomes das aulas de um curso específico no Back Office."""
        self.log(f"\nIniciando extração para o curso de código: {course_code}")
        url_curso = f"https://www.estrategiaconcursos.com.br/admin/produto-curso/?codigo={course_code}"
        self.log(f"Navegando para: {url_curso}")
        self.page.goto(url_curso)
        self.page.wait_for_load_state("domcontentloaded")
        
        seletor_container_aula = "div.blocoLink"
        seletor_nome_aula = "table > tbody > tr:nth-child(3) > td"
        seletor_conteudo_aula = "table > tbody > tr:nth-child(4) > td"
        
        self.log("Procurando por aulas na página...")
        lista_de_aulas = []
        
        try:
            self.page.wait_for_selector(seletor_container_aula, timeout=15000)
            containers_de_aula = self.page.locator(seletor_container_aula).all()
        except Exception:
            self.log("❌ Nenhum container de aula encontrado. Verifique o código do curso ou o HTML da página.")
            return []
            
        self.log(f"Encontrado(s) {len(containers_de_aula)} elemento(s) de aula. Extraindo dados...")
        for container in containers_de_aula:
            try:
                nome_aula = container.locator(seletor_nome_aula).inner_text()
                conteudo_aula = container.locator(seletor_conteudo_aula).inner_text()
                conteudo_limpo = " ".join(conteudo_aula.strip().split())
                aula_completa = f"{nome_aula.strip()}: {conteudo_limpo}"
                lista_de_aulas.append(aula_completa)
            except Exception as e:
                # Loga como aviso, mas continua tentando as outras aulas
                self.log(f"⚠️ Erro ao extrair dados de uma aula: {e}")
                
        return lista_de_aulas
