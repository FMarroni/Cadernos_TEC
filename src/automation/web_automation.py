# Ficheiro: src/automation/web_automation.py

from playwright.sync_api import (
    sync_playwright,
    Page,
    Browser,
    BrowserContext,
    Playwright
)
from typing import Optional, Callable

class WebAutomation:
    """
    Classe base para automação web. Gerencia o ciclo de vida do Playwright.
    
    Esta classe pode ser usada manualmente (chamando start() e stop())
    ou como um context manager (usando 'with WebAutomation(...) as automacao:').
    """
    
    def __init__(self, log_callback: Callable[..., None], headless: bool = False):
        """
        Inicializa a automação web.

        Args:
            log_callback (Callable): Função da GUI para enviar mensagens de log.
            headless (bool): Define se o navegador será executado em modo invisível.
        """
        self.log = log_callback
        self.headless = headless

        # Atributos do Playwright que serão inicializados
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start(self):
        """Inicia o Playwright, abre o navegador e cria uma nova página."""
        self.log("Iniciando automação web...")
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            self.log("✅ Navegador iniciado com sucesso.")
        except Exception as e:
            self.log(f"❌ Erro crítico ao iniciar o Playwright: {e}")
            # Re-lança a exceção para que o Orquestrador possa capturá-la
            raise

    def stop(self):
        """Fecha o navegador e finaliza o Playwright de forma segura."""
        self.log("Finalizando automação web...")
        try:
            # Fecha os recursos na ordem inversa de criação
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.log("Navegador fechado com segurança.")
        except Exception as e:
            # Loga o erro, mas não lança exceção, pois estamos apenas limpando
            self.log(f"⚠️ Erro (não-crítico) ao fechar o navegador: {e}")

    def __enter__(self):
        """Permite o uso com 'with WebAutomation(...) as automacao:'"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Garante que self.stop() seja chamado ao sair do 'with'."""
        self.stop()
