"""
Trapdoor Connector - Upload this to ChatGPT/Claude/any sandboxed AI

This gives the AI access to your local machine via Trapdoor.

Setup:
    1. Run Trapdoor server on your machine: python server.py
    2. Expose it: ngrok http 8080
    3. Upload this file to your AI chat
    4. Set the URL and token when prompted

Usage:
    import connector as td

    # Connect
    td.connect("https://your-ngrok-url.ngrok.io", "your-token")

    # List files
    td.ls("/home/user")

    # Read file
    content = td.read("/home/user/notes.txt")

    # Write file
    td.write("/tmp/output.txt", "Hello from the cloud!")

    # Run command
    result = td.run("ls -la")
"""

import shlex
from typing import List, Dict, Any, Optional

import requests

# Connection state
_url: Optional[str] = None
_token: Optional[str] = None
_headers: Dict[str, str] = {}
_session = requests.Session()
DEFAULT_TIMEOUT = 10


def _request(method: str, path: str, **kwargs) -> requests.Response:
    _require_connection()
    url = f"{_url}{path}"
    if "timeout" not in kwargs:
        kwargs["timeout"] = DEFAULT_TIMEOUT
    try:
        resp = _session.request(method, url, headers=_headers, **kwargs)
        resp.raise_for_status()
        return resp
    except requests.RequestException as exc:
        raise RuntimeError(f"Trapdoor request failed: {exc}") from exc


def connect(url: str, token: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """
    Connect to Trapdoor server

    Args:
        url: Your Trapdoor URL (e.g., https://abc123.ngrok.io)
        token: Your auth token

    Returns:
        True if connection successful
    """
    global _url, _token, _headers

    _url = url.rstrip("/")
    _token = token
    _headers = {"Authorization": f"Bearer {token}"}

    # Test connection (health + auth)
    try:
        resp = _session.get(f"{_url}/health", timeout=timeout)
        resp.raise_for_status()
        info = resp.json()
        _request("get", "/fs/ls", params={"path": "."}, timeout=timeout)
        print(f"Connected to Trapdoor {info.get('version', '1.0')} at {_url}")
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False


def _require_connection():
    if not _url:
        raise RuntimeError("Not connected. Call connect(url, token) first.")


# ==============================================================================
# Filesystem
# ==============================================================================

def ls(path: str = "/") -> List[str]:
    """List directory contents"""
    data = _request("get", "/fs/ls", params={"path": path}).json()
    if "entries" in data:
        return [e["name"] for e in data["entries"]]
    return data


def read(path: str) -> str:
    """Read file contents"""
    data = _request("get", "/fs/read", params={"path": path}).json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data.get("content", "")


def write(path: str, content: str, append: bool = False) -> dict:
    """Write content to file"""
    return _request(
        "post",
        "/fs/write",
        json={"path": path, "content": content, "mode": "append" if append else "write"},
    ).json()


def mkdir(path: str) -> dict:
    """Create directory"""
    return _request("post", "/fs/mkdir", json={"path": path}).json()


def rm(path: str) -> dict:
    """Remove file or directory"""
    return _request("post", "/fs/rm", json={"path": path}).json()


# ==============================================================================
# Command Execution
# ==============================================================================

def exec(cmd: List[str], cwd: str = "/tmp", timeout: int = 60) -> Dict[str, Any]:
    """
    Execute command

    Args:
        cmd: Command as list ["ls", "-la"]
        cwd: Working directory
        timeout: Timeout in seconds

    Returns:
        Dict with stdout, stderr, returncode
    """
    return _request(
        "post",
        "/exec",
        json={"cmd": cmd, "cwd": cwd, "timeout": timeout},
        timeout=timeout,
    ).json()


def run(cmd_string: str, cwd: str = "/tmp") -> str:
    """
    Run shell command (convenience wrapper)

    Args:
        cmd_string: Command as string "ls -la"

    Returns:
        Command stdout
    """
    result = exec(shlex.split(cmd_string), cwd=cwd)
    if result.get("returncode") != 0 and result.get("stderr"):
        print(f"Warning: {result['stderr']}")
    return result.get("stdout", "")


# ==============================================================================
# Chat (if Trapdoor has LLM configured)
# ==============================================================================

def chat(prompt: str, model: str = "default") -> str:
    """Send prompt to local LLM via Trapdoor"""
    data = _request(
        "post",
        "/v1/chat/completions",
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=30,
    ).json()
    return data["choices"][0]["message"]["content"]


# ==============================================================================
# Utilities
# ==============================================================================

def health() -> dict:
    """Check server health"""
    return _request("get", "/health", timeout=5).json()


def whoami() -> str:
    """Get current user on remote machine"""
    return run("whoami").strip()


def pwd() -> str:
    """Get current directory info"""
    return run("pwd").strip()


def cat(path: str) -> str:
    """Alias for read()"""
    return read(path)


# ==============================================================================
# Quick test
# ==============================================================================

if __name__ == "__main__":
    print("Trapdoor Connector")
    print("=" * 40)
    print()
    print("Usage in AI chat:")
    print('  import connector as td')
    print('  td.connect("https://your-url.ngrok.io", "your-token")')
    print('  td.ls("/home")')
    print('  td.read("/etc/hostname")')
    print('  td.run("uname -a")')
