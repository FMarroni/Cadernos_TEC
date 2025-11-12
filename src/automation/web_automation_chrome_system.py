# web_automation.py (VERSÃO MODIFICADA PARA USAR CHROME DO SISTEMA)

from playwright.sync_api import (
    sync_playwright,
    Page,
    Browser,
    BrowserContext,
    Playwright
)
from typing import Optional, Callable
import os
import sys
import subprocess

def _find_chrome_executable():
    """
    Encontra o executável do Chrome/Edge instalado no sistema Windows.
    
    Returns:
        str: Caminho para o executável do navegador, ou None se não encontrado
    """
    # Possíveis caminhos do Chrome no Windows
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
    ]
    
    # Possíveis caminhos do Edge no Windows
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
    ]
    
    # Tentar Chrome primeiro
    for path in chrome_paths:
        if os.path.exists(path):
            return path
    
    # Se não encontrou Chrome, tentar Edge
    for path in edge_paths:
        if os.path.exists(path):
            return path
    
    return None


class WebAutomation:
    """
    Classe base para automação web. Gerencia o ciclo de vida do Playwright.
    
    VERSÃO MODIFICADA: Usa Chrome/Edge do sistema ao invés do Playwright bundled.
    Ideal para executáveis PyInstaller.
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
        
        # Encontrar navegador do sistema
        self.chrome_path = _find_chrome_executable()

    def start(self):
        """Inicia o Playwright, abre o navegador e cria uma nova página."""
        self.log("Iniciando automação web...")
        
        # Verificar se encontrou navegador
        if not self.chrome_path:
            error_msg = (
                "❌ Nenhum navegador encontrado!\n\n"
                "Por favor, instale o Google Chrome ou Microsoft Edge:\n"
                "• Chrome: https://www.google.com/chrome/\n"
                "• Edge: https://www.microsoft.com/edge/"
            )
            self.log(error_msg)
            raise FileNotFoundError(error_msg)
        
        self.log(f"✅ Navegador encontrado: {self.chrome_path}")
        
        try:
            self.playwright = sync_playwright().start()
            
            # MODIFICAÇÃO PRINCIPAL: Usar chromium.launch com executable_path
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                executable_path=self.chrome_path,  # ← USA CHROME DO SISTEMA
                args=[
                    '--disable-blink-features=AutomationControlled',  # Evita detecção
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )
            
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.page = self.context.new_page()
            self.log("✅ Navegador iniciado com sucesso.")
            
        except Exception as e:
            self.log(f"❌ Erro crítico ao iniciar o Playwright: {e}")
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
            self.log(f"⚠️ Aviso ao fechar o navegador: {e}")

    # --- Context Manager Support ---
    def __enter__(self):
        """Permite usar 'with WebAutomation(...) as automacao:'"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Garante que o navegador será fechado ao sair do bloco 'with'."""
        self.stop()
        # Retorna False para propagar exceções (se houver)
        return False
