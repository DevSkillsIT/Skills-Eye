"""
Windows Multi-Method Connection Manager
Tenta múltiplos métodos de conexão automaticamente com fallback inteligente

Ordem de tentativas:
1. PSExec (mais comum, não requer WinRM)
2. WinRM (se PSExec falhar)
3. SSH/OpenSSH (último recurso)

Cada tentativa é registrada com logs detalhados para debug
"""
import asyncio
import logging
from typing import Optional, Tuple, List, Dict
from .windows_psexec import WindowsPSExecInstaller
from .windows_winrm import WindowsWinRMInstaller
from .windows_ssh import WindowsSSHInstaller

logger = logging.getLogger(__name__)


class WindowsMultiConnector:
    """
    Gerenciador de conexões Windows com múltiplos métodos e fallback automático
    """
    
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        domain: Optional[str] = None,
        client_id: str = "default",
        ssh_port: int = 22,
        winrm_port: Optional[int] = None,
        winrm_use_ssl: bool = False,
        psexec_path: str = "psexec.exe",
        key_file: Optional[str] = None
    ):
        self.host = host
        
        # 🔧 Extrair domínio do username se presente (DOMAIN\username)
        if "\\" in username and not domain:
            parts = username.split("\\", 1)
            self.domain = parts[0]
            self.username = parts[1]
            logger.info(f"📋 Domínio extraído do username: '{self.domain}', usuário: '{self.username}'")
        else:
            self.username = username
            self.domain = domain
        
        self.password = password
        self.client_id = client_id
        self.ssh_port = ssh_port
        self.winrm_port = winrm_port or (5986 if winrm_use_ssl else 5985)
        self.winrm_use_ssl = winrm_use_ssl
        self.psexec_path = psexec_path
        self.key_file = key_file
        
        self.active_installer = None
        self.connection_method = None
        self.connection_attempts: List[Dict] = []
        
    async def log(self, message: str, level: str = "info"):
        """Log para o installer ativo ou logger padrão"""
        if self.active_installer:
            await self.active_installer.log(message, level)
        else:
            # Mapear 'success' para 'info' pois logger padrão não tem success
            log_level = "info" if level == "success" else level
            # Validar que o nível existe no logger
            if hasattr(logger, log_level):
                getattr(logger, log_level)(f"[{self.client_id}] {message}")
            else:
                logger.info(f"[{self.client_id}] [{level.upper()}] {message}")
    
    def _format_psexec_error(self, error_msg: str) -> str:
        """Gera mensagem amigável para erros de PSExec"""
        if "|" in error_msg and error_msg.count("|") >= 2:
            return error_msg

        lower_msg = error_msg.lower()

        if "dns" in error_msg or "resolve" in lower_msg:
            return f"Erro de DNS - não foi possível resolver {self.host}"
        if "timeout" in lower_msg or "timed out" in lower_msg:
            return f"Host {self.host} não respondeu (timeout) - pode estar offline"
        if "445" in error_msg or "port_closed" in error_msg:
            return "Porta SMB 445 bloqueada ou inacessível (firewall?)"
        if "permission" in lower_msg or "permiss" in lower_msg:
            return "Sem permissões administrativas - verifique se o usuário é admin local"
        if "auth" in lower_msg or "credential" in lower_msg:
            return "Credenciais inválidas ou rejeitadas"

        return error_msg

    async def try_psexec(self) -> Tuple[bool, str, Optional[WindowsPSExecInstaller]]:
        """
        Tentativa 1: PSExec
        Mais comum, funciona sem WinRM habilitado
        """
        await self.log("=" * 60, "info")
        await self.log("🔧 TENTATIVA 1: PSExec", "info")
        await self.log("=" * 60, "info")
        
        try:
            installer = WindowsPSExecInstaller(
                host=self.host,
                username=self.username,
                password=self.password,
                domain=self.domain,
                psexec_path=self.psexec_path,
                client_id=self.client_id
            )
            
            # Build display username
            display_username = f"{self.domain}\\{self.username}" if self.domain else self.username
            
            await self.log(f"📋 Host: {self.host}", "info")
            await self.log(f"👤 Usuário: {display_username}", "info")
            await self.log(f"🔑 Método: PSExec (SMB porta 445)", "info")

            valid, validation_msg = await installer.validate_connection()
            if not valid:
                detailed_msg = self._format_psexec_error(validation_msg)
                await self.log(f"❌ Validação PSExec falhou: {detailed_msg}", "warning")
                self.connection_attempts.append({
                    "method": "psexec",
                    "success": False,
                    "message": detailed_msg
                })
                return False, detailed_msg, None

            await self.log("⚡ Iniciando conexão via PSExec...", "info")
            
            if await installer.connect():
                await self.log("✅ SUCESSO: Conexão PSExec estabelecida!", "success")
                self.connection_attempts.append({
                    "method": "psexec",
                    "success": True,
                    "message": "Conexão bem-sucedida via PSExec"
                })
                return True, "PSExec conectado com sucesso", installer
            else:
                await self.log("❌ FALHA: PSExec não conseguiu conectar", "warning")
                self.connection_attempts.append({
                    "method": "psexec",
                    "success": False,
                    "message": "PSExec falhou - tentando próximo método"
                })
                return False, "PSExec falhou", None
                
        except Exception as e:
            error_msg = str(e)
            await self.log(f"❌ ERRO PSExec: {error_msg}", "error")
            detailed_msg = self._format_psexec_error(error_msg)

            self.connection_attempts.append({
                "method": "psexec",
                "success": False,
                "message": detailed_msg
            })
            return False, detailed_msg, None
    
    async def try_winrm(self) -> Tuple[bool, str, Optional[WindowsWinRMInstaller]]:
        """
        Tentativa 2: WinRM
        Requer WinRM habilitado no servidor remoto
        """
        await self.log("=" * 60, "info")
        await self.log("🔧 TENTATIVA 2: WinRM", "info")
        await self.log("=" * 60, "info")
        
        try:
            installer = WindowsWinRMInstaller(
                host=self.host,
                username=self.username,
                password=self.password,
                domain=self.domain,
                use_ssl=self.winrm_use_ssl,
                port=self.winrm_port,
                client_id=self.client_id
            )
            
            # Build display username
            display_username = f"{self.domain}\\{self.username}" if self.domain else self.username
            
            await self.log(f"📋 Host: {self.host}", "info")
            await self.log(f"👤 Usuário: {display_username}", "info")
            await self.log(f"🔑 Método: WinRM porta {self.winrm_port}", "info")
            await self.log(f"🔒 SSL: {'Habilitado' if self.winrm_use_ssl else 'Desabilitado'}", "info")
            await self.log("⚡ Iniciando conexão via WinRM...", "info")
            
            if await installer.connect():
                await self.log("✅ SUCESSO: Conexão WinRM estabelecida!", "success")
                self.connection_attempts.append({
                    "method": "winrm",
                    "success": True,
                    "message": "Conexão bem-sucedida via WinRM"
                })
                return True, "WinRM conectado com sucesso", installer
            else:
                await self.log("❌ FALHA: WinRM não conseguiu conectar", "warning")
                self.connection_attempts.append({
                    "method": "winrm",
                    "success": False,
                    "message": "WinRM falhou - tentando próximo método"
                })
                return False, "WinRM falhou", None
                
        except Exception as e:
            error_msg = str(e)
            await self.log(f"❌ ERRO WinRM: {error_msg}", "error")
            
            # Analisar erro estruturado (formato: CODE|Message|Category)
            if "|" in error_msg:
                parts = error_msg.split("|")
                code = parts[0] if len(parts) > 0 else "UNKNOWN"
                message = parts[1] if len(parts) > 1 else error_msg
                
                if code == "AUTH_FAILED":
                    detailed_msg = "Autenticação WinRM falhou - verifique usuário/senha"
                elif code == "TIMEOUT":
                    detailed_msg = "Timeout WinRM - serviço pode estar desabilitado ou firewall bloqueando"
                elif code == "PORT_CLOSED":
                    detailed_msg = f"Porta WinRM {self.winrm_port} fechada ou inacessível"
                else:
                    detailed_msg = message
            else:
                detailed_msg = error_msg
            
            self.connection_attempts.append({
                "method": "winrm",
                "success": False,
                "message": detailed_msg
            })
            return False, detailed_msg, None
    
    async def try_ssh(self) -> Tuple[bool, str, Optional[WindowsSSHInstaller]]:
        """
        Tentativa 3: SSH/OpenSSH
        Último recurso - requer OpenSSH Server instalado no Windows
        """
        await self.log("=" * 60, "info")
        await self.log("🔧 TENTATIVA 3: SSH/OpenSSH", "info")
        await self.log("=" * 60, "info")
        
        try:
            installer = WindowsSSHInstaller(
                host=self.host,
                username=self.username,
                password=self.password,
                domain=self.domain,
                ssh_port=self.ssh_port,
                key_file=self.key_file,
                client_id=self.client_id
            )
            
            await self.log(f"📋 Host: {self.host}", "info")
            await self.log(f"👤 Usuário: {self.username}", "info")
            await self.log(f"🔑 Método: SSH porta {self.ssh_port}", "info")
            await self.log("⚡ Iniciando conexão via SSH...", "info")
            
            if await installer.connect():
                await self.log("✅ SUCESSO: Conexão SSH estabelecida!", "success")
                self.connection_attempts.append({
                    "method": "ssh",
                    "success": True,
                    "message": "Conexão bem-sucedida via SSH/OpenSSH"
                })
                return True, "SSH conectado com sucesso", installer
            else:
                await self.log("❌ FALHA: SSH não conseguiu conectar", "warning")
                self.connection_attempts.append({
                    "method": "ssh",
                    "success": False,
                    "message": "SSH falhou - OpenSSH pode não estar instalado"
                })
                return False, "SSH falhou", None
                
        except Exception as e:
            error_msg = str(e)
            await self.log(f"❌ ERRO SSH: {error_msg}", "error")
            
            # Analisar erro estruturado
            if "|" in error_msg:
                parts = error_msg.split("|")
                code = parts[0] if len(parts) > 0 else "UNKNOWN"
                message = parts[1] if len(parts) > 1 else error_msg
                
                if code == "AUTH_FAILED":
                    detailed_msg = "Autenticação SSH falhou"
                elif code == "TIMEOUT":
                    detailed_msg = "Timeout SSH - OpenSSH pode não estar instalado"
                elif code == "PORT_CLOSED":
                    detailed_msg = f"Porta SSH {self.ssh_port} fechada - OpenSSH não instalado?"
                else:
                    detailed_msg = message
            else:
                detailed_msg = error_msg
            
            self.connection_attempts.append({
                "method": "ssh",
                "success": False,
                "message": detailed_msg
            })
            return False, detailed_msg, None
    
    async def connect_with_fallback(self) -> Tuple[bool, str, Optional[object]]:
        """
        Tenta conectar usando múltiplos métodos com fallback automático
        
        Returns:
            Tuple[bool, str, Optional[Installer]]: 
                - success: True se algum método funcionou
                - message: Mensagem detalhada sobre as tentativas
                - installer: Instância do installer conectado (None se todos falharam)
        """
        await self.log("🚀 Iniciando conexão Windows com fallback automático", "info")
        await self.log(f"🎯 Target: {self.host}", "info")
        await self.log(f"👤 Usuário: {self.username}", "info")
        await self.log("", "info")
        
        # Tentativa 1: PSExec
        success, message, installer = await self.try_psexec()
        if success:
            self.active_installer = installer
            self.connection_method = "psexec"
            await self.log("", "info")
            await self.log("=" * 60, "success")
            await self.log("🎉 CONEXÃO ESTABELECIDA VIA PSEXEC!", "success")
            await self.log("=" * 60, "success")
            return True, "Conectado via PSExec", installer
        
        await self.log("⚠️ PSExec falhou, tentando WinRM...", "warning")
        await self.log("", "info")
        
        # Tentativa 2: WinRM
        success, message, installer = await self.try_winrm()
        if success:
            self.active_installer = installer
            self.connection_method = "winrm"
            await self.log("", "info")
            await self.log("=" * 60, "success")
            await self.log("🎉 CONEXÃO ESTABELECIDA VIA WINRM!", "success")
            await self.log("=" * 60, "success")
            return True, "Conectado via WinRM", installer
        
        await self.log("⚠️ WinRM falhou, tentando SSH como último recurso...", "warning")
        await self.log("", "info")
        
        # Tentativa 3: SSH
        success, message, installer = await self.try_ssh()
        if success:
            self.active_installer = installer
            self.connection_method = "ssh"
            await self.log("", "info")
            await self.log("=" * 60, "success")
            await self.log("🎉 CONEXÃO ESTABELECIDA VIA SSH!", "success")
            await self.log("=" * 60, "success")
            return True, "Conectado via SSH/OpenSSH", installer
        
        # Todos os métodos falharam
        await self.log("", "error")
        await self.log("=" * 60, "error")
        await self.log("❌ FALHA TOTAL: TODOS OS MÉTODOS FALHARAM", "error")
        await self.log("=" * 60, "error")
        
        # Construir mensagem de erro detalhada
        error_details = "\n\n📋 RESUMO DAS TENTATIVAS:\n\n"
        for i, attempt in enumerate(self.connection_attempts, 1):
            status = "✅ SUCESSO" if attempt["success"] else "❌ FALHA"
            error_details += f"{i}. {attempt['method'].upper()}: {status}\n"
            error_details += f"   └─ {attempt['message']}\n\n"
        
        error_details += "\n💡 RECOMENDAÇÕES:\n\n"
        error_details += "1. Verifique se as credenciais estão corretas\n"
        error_details += "2. Confirme que o host está acessível pela rede\n"
        error_details += "3. PSExec: Porta 445 (SMB) deve estar aberta\n"
        error_details += "4. WinRM: Execute 'Enable-PSRemoting -Force' no servidor\n"
        error_details += "5. SSH: Instale OpenSSH Server no Windows\n"
        error_details += "6. Verifique configurações de firewall no servidor\n"
        
        await self.log(error_details, "error")
        
        raise Exception(f"ALL_METHODS_FAILED|Todos os métodos de conexão falharam para {self.host}. Veja logs para detalhes.|CONEXAO_MULTIPLA")
    
    async def disconnect(self):
        """Desconectar do installer ativo"""
        if self.active_installer:
            await self.active_installer.disconnect()
            self.active_installer = None
            self.connection_method = None
    
    def get_connection_summary(self) -> Dict:
        """Retorna resumo das tentativas de conexão"""
        return {
            "host": self.host,
            "successful_method": self.connection_method,
            "attempts": self.connection_attempts,
            "total_attempts": len(self.connection_attempts)
        }
