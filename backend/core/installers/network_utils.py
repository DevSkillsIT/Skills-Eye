"""
Utilities for network connectivity testing and validation
Centralized module for network-related operations across all installers
"""
import socket
from typing import Tuple


def test_port(host: str, port: int, timeout: int = 10) -> bool:
    """
    Test if a port is open on a host

    Args:
        host: Hostname or IP address
        port: Port number to test
        timeout: Connection timeout in seconds (default: 10)

    Returns:
        True: Port is open and accepting connections
        False: Port is closed/filtered but host responded quickly (connection refused)

    Raises:
        socket.gaierror: DNS resolution failed
        socket.timeout: Connection timeout (host unreachable, offline, or network very slow)
        ConnectionRefusedError: Connection actively refused by host
        Exception: Other network errors (unreachable, no route, etc)
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))

        # Analyze result codes:
        # 0 = success, port open
        # 10061 (Windows) or 111 (Linux) = connection refused (host UP, port closed)
        # 10060 (Windows) or 110 (Linux) = timeout (host DOWN or unreachable)

        if result == 0:
            return True
        elif result in (10061, 111):  # Connection refused - host is UP but port closed
            return False
        elif result in (10060, 110, 10065, 113):  # Timeout or unreachable - host is DOWN
            raise socket.timeout(
                f"Connection to {host}:{port} timed out (error code {result}). "
                "Host may be offline or unreachable."
            )
        else:
            # Other error codes - treat as network issue
            raise Exception(f"Network error connecting to {host}:{port} (error code {result})")

    except socket.gaierror as e:
        # DNS resolution failed - cannot resolve hostname
        raise socket.gaierror(f"DNS resolution failed for {host}: {e}")
    except socket.timeout:
        # Connection timed out - propagate the exception
        raise
    except OSError as e:
        # Handle OS-level errors (unreachable, no route, etc)
        error_msg = str(e).lower()
        if "timed out" in error_msg or "timeout" in error_msg:
            raise socket.timeout(f"Connection to {host}:{port} timed out: {e}")
        else:
            raise Exception(f"Network error testing {host}:{port}: {e}")
    except Exception as e:
        # Other unexpected errors
        raise Exception(f"Unexpected error testing {host}:{port}: {e}")
    finally:
        if sock:
            try:
                sock.close()
            except:
                pass


def validate_port_with_message(host: str, port: int, timeout: int = 10) -> Tuple[bool, str, str]:
    """
    Validate port connectivity and return structured error messages

    Args:
        host: Hostname or IP address
        port: Port number to test
        timeout: Connection timeout in seconds (default: 10)

    Returns:
        Tuple of (success: bool, message: str, category: str)
        - success: True if port is open
        - message: User-friendly message in Portuguese
        - category: Error category (dns, timeout, refused, network, success)
    """
    try:
        result = test_port(host, port, timeout)
        if result:
            return True, f"Porta {port} está acessível em {host}", "success"
        else:
            return False, f"Porta {port} está fechada em {host} (conexão recusada)", "refused"

    except socket.gaierror as e:
        return False, f"Erro de DNS: não foi possível resolver o host {host}", "dns"

    except socket.timeout as e:
        return False, f"Timeout: host {host} não responde na porta {port} (pode estar offline)", "timeout"

    except ConnectionRefusedError:
        return False, f"Conexão recusada pelo host {host} na porta {port}", "refused"

    except Exception as e:
        return False, f"Erro de rede ao testar {host}:{port}: {str(e)}", "network"


def format_structured_error(code: str, message: str, category: str, snippet: str = "") -> str:
    """
    Format error in structured format for parsing

    Args:
        code: Error code (e.g., DNS_ERROR, PORT_CLOSED)
        message: User-friendly error message
        category: Error category (dns, network, timeout, etc)
        snippet: Optional code snippet or details

    Returns:
        Formatted error string: "CODE|MESSAGE|CATEGORY|SNIPPET"
    """
    if snippet:
        return f"{code}|{message}|{category}|{snippet}"
    else:
        return f"{code}|{message}|{category}"


def resolve_hostname(host: str, timeout: int = 5) -> Tuple[bool, str]:
    """
    Resolve hostname to IP address

    Args:
        host: Hostname to resolve
        timeout: Resolution timeout in seconds

    Returns:
        Tuple of (success: bool, result: str)
        - If success: result is IP address
        - If failure: result is error message
    """
    try:
        socket.setdefaulttimeout(timeout)
        ip = socket.gethostbyname(host)
        return True, ip
    except socket.gaierror as e:
        return False, f"Não foi possível resolver {host}: {str(e)}"
    except Exception as e:
        return False, f"Erro ao resolver {host}: {str(e)}"
    finally:
        socket.setdefaulttimeout(None)


def is_valid_ip(ip: str) -> bool:
    """
    Check if string is a valid IP address

    Args:
        ip: IP address string to validate

    Returns:
        True if valid IPv4 or IPv6 address
    """
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET6, ip)
            return True
        except socket.error:
            return False


def is_valid_port(port: int) -> bool:
    """
    Check if port number is valid

    Args:
        port: Port number to validate

    Returns:
        True if port is in valid range (1-65535)
    """
    return 1 <= port <= 65535


__all__ = [
    'test_port',
    'validate_port_with_message',
    'format_structured_error',
    'resolve_hostname',
    'is_valid_ip',
    'is_valid_port',
]
