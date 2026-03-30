#!/usr/bin/env python3
"""
Trapdoor 1.0 - Give cloud AIs safe access to your local machine

Usage:
    trapdoor                    # Start with limited access (default)
    trapdoor --solid            # Read/write filesystem
    trapdoor --full             # Full access including exec
    trapdoor --port 9000        # Custom port
"""

import argparse
import os
import secrets
import socket
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ==============================================================================
# Access Levels
# ==============================================================================

LEVELS = {
    "limited": {
        "description": "Read-only filesystem, no command execution",
        "fs_read": True,
        "fs_write": False,
        "fs_delete": False,
        "exec": False,
    },
    "solid": {
        "description": "Read/write filesystem, no command execution",
        "fs_read": True,
        "fs_write": True,
        "fs_delete": False,
        "exec": False,
    },
    "full": {
        "description": "Full access: filesystem + command execution",
        "fs_read": True,
        "fs_write": True,
        "fs_delete": True,
        "exec": True,
    },
}

# Current access level (set by CLI)
ACCESS = LEVELS["limited"]

# ==============================================================================
# Configuration
# ==============================================================================

PORT = 6969
TOKEN_FILE = Path.home() / ".trapdoor" / "token"
ROOT_DIR = None

if os.getenv("TRAPDOOR_ROOT"):
    ROOT_DIR = Path(os.environ["TRAPDOOR_ROOT"]).expanduser().resolve()

# ==============================================================================
# Token Management
# ==============================================================================

def get_or_create_token() -> str:
    """Get existing token or create a new one"""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()

    token = secrets.token_hex(16)
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)
    return token

TOKEN = get_or_create_token()

def find_open_port(start: int = 8080, max_tries: int = 100) -> int:
    """Find an open port starting from start"""
    for port in range(start, start + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No open port found in range {start}-{start + max_tries}")


def resolve_path(path: str, *, allow_root: bool = True) -> Path:
    """Resolve a path and enforce TRAPDOOR_ROOT if set."""
    raw = Path(path).expanduser()
    if ROOT_DIR:
        if not raw.is_absolute():
            raw = ROOT_DIR / raw
        resolved = raw.resolve()
        try:
            resolved.relative_to(ROOT_DIR)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail="Path outside TRAPDOOR_ROOT") from exc
        if not allow_root and resolved == ROOT_DIR:
            raise HTTPException(status_code=403, detail="Refusing to operate on root directory")
        return resolved
    return raw.resolve()

# ==============================================================================
# FastAPI App
# ==============================================================================

app = FastAPI(
    title="Trapdoor 1.0",
    description="Give cloud AIs safe access to your local machine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# Authentication
# ==============================================================================

def require_auth(authorization: Optional[str] = Header(None), token: Optional[str] = None) -> str:
    """Validate auth from Authorization header or query token."""
    if token:
        provided_token = token
    elif authorization and authorization.startswith("Bearer "):
        provided_token = authorization.split(" ", 1)[1]
    else:
        raise HTTPException(status_code=401, detail="Missing auth (Authorization header or ?token=)")

    token = provided_token
    if token != TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

    return token

# ==============================================================================
# Request/Response Models
# ==============================================================================

class WriteRequest(BaseModel):
    path: str
    content: str
    mode: str = "write"

class MkdirRequest(BaseModel):
    path: str

class RmRequest(BaseModel):
    path: str

class ExecRequest(BaseModel):
    cmd: List[str]
    cwd: str = "/tmp"
    timeout: int = 60

class ChatRequest(BaseModel):
    model: str = "gpt-4"
    messages: list

# ==============================================================================
# Health Endpoint
# ==============================================================================

@app.get("/health")
def health():
    """Health check - shows current access level"""
    level_name = next((k for k, v in LEVELS.items() if v == ACCESS), "unknown")
    return {
        "status": "ok",
        "version": "1.0.0",
        "access_level": level_name,
        "permissions": {
            "read": ACCESS["fs_read"],
            "write": ACCESS["fs_write"],
            "delete": ACCESS["fs_delete"],
            "exec": ACCESS["exec"],
        },
        "root": str(ROOT_DIR) if ROOT_DIR else None,
        "timestamp": datetime.now().isoformat()
    }

# ==============================================================================
# Filesystem Endpoints
# ==============================================================================

@app.get("/fs/ls")
def fs_ls(
    path: str = Query("/"),
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """List directory contents"""
    require_auth(authorization, token)

    if not ACCESS["fs_read"]:
        raise HTTPException(status_code=403, detail="Read access disabled")

    target = resolve_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    if not target.is_dir():
        stat = target.stat()
        return {
            "path": str(target),
            "type": "file",
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }

    entries = []
    for item in sorted(target.iterdir()):
        try:
            stat = item.stat()
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": stat.st_size if item.is_file() else None,
            })
        except PermissionError:
            entries.append({"name": item.name, "type": "unknown", "error": "permission denied"})

    return {"path": str(target), "entries": entries}


@app.get("/fs/read")
def fs_read(
    path: str,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """Read file contents"""
    require_auth(authorization, token)

    if not ACCESS["fs_read"]:
        raise HTTPException(status_code=403, detail="Read access disabled")

    target = resolve_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not target.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    try:
        content = target.read_text()
        return {"path": str(target), "content": content, "size": len(content)}
    except UnicodeDecodeError:
        return {"path": str(target), "error": "binary file", "size": target.stat().st_size}


@app.post("/fs/write")
def fs_write(
    req: WriteRequest,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """Write content to file"""
    require_auth(authorization, token)

    if not ACCESS["fs_write"]:
        raise HTTPException(status_code=403, detail="Write access disabled. Start with --solid or --full")

    target = resolve_path(req.path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if req.mode == "append":
        with open(target, "a") as f:
            f.write(req.content)
    else:
        target.write_text(req.content)

    return {"path": str(target), "written": len(req.content), "mode": req.mode}


@app.post("/fs/mkdir")
def fs_mkdir(
    req: MkdirRequest,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """Create directory"""
    require_auth(authorization, token)

    if not ACCESS["fs_write"]:
        raise HTTPException(status_code=403, detail="Write access disabled. Start with --solid or --full")

    target = resolve_path(req.path)
    target.mkdir(parents=True, exist_ok=True)

    return {"path": str(target), "created": True}


@app.post("/fs/rm")
def fs_rm(
    req: RmRequest,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """Remove file or directory"""
    require_auth(authorization, token)

    if not ACCESS["fs_delete"]:
        raise HTTPException(status_code=403, detail="Delete access disabled. Start with --full")

    target = resolve_path(req.path, allow_root=False)

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {req.path}")

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    return {"path": str(target), "removed": True}

# ==============================================================================
# Command Execution
# ==============================================================================

@app.post("/exec")
def exec_command(
    req: ExecRequest,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """Execute shell command"""
    require_auth(authorization, token)

    if not ACCESS["exec"]:
        raise HTTPException(status_code=403, detail="Exec disabled. Start with --full to enable")

    try:
        cwd_path = resolve_path(req.cwd)
        if not cwd_path.exists() or not cwd_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Invalid cwd: {req.cwd}")
        result = subprocess.run(
            req.cmd,
            cwd=str(cwd_path),
            capture_output=True,
            text=True,
            timeout=req.timeout
        )

        return {
            "cmd": req.cmd,
            "cwd": req.cwd,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail=f"Command timed out after {req.timeout}s")
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Command not found: {req.cmd[0]}")

# ==============================================================================
# Chat Proxy (Optional)
# ==============================================================================

@app.post("/v1/chat/completions")
def chat_completions(
    req: ChatRequest,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """OpenAI-compatible chat endpoint (optional LLM proxy)"""
    require_auth(authorization, token)

    ollama_host = os.getenv("OLLAMA_HOST")

    if ollama_host:
        import requests
        try:
            resp = requests.post(
                f"{ollama_host}/v1/chat/completions",
                json={"model": req.model, "messages": req.messages},
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Chat proxy error: {exc}") from exc

    return {
        "id": "trapdoor-1",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Chat proxy not configured. Set OLLAMA_HOST to enable."
            },
            "finish_reason": "stop"
        }]
    }

# ==============================================================================
# CLI
# ==============================================================================

FULL_ACCESS_WARNING = """
⚠️  FULL ACCESS MODE - READ CAREFULLY ⚠️

You are granting an AI complete control over your machine:

  FILESYSTEM
  • Read any file your user can access
  • Write/modify any file your user can write
  • Delete any file or directory

  COMMAND EXECUTION
  • Shell commands (bash, sh, zsh)
  • System utilities (rm, mv, chmod, kill)
  • Package managers (pip, npm, brew, apt)
  • Sudo commands (if your user has sudo access)
  • Scripts that could modify system config

  MACOS PERMISSIONS (if granted in System Preferences > Privacy):
  • Screen Recording - Take screenshots (screencapture)
  • Accessibility - Control other apps (osascript, cliclick)
  • Microphone - Record audio (sox, ffmpeg)
  • Camera - Capture video/photos (ffmpeg, imagesnap)
  • Automation - Script apps (osascript, shortcuts)
  • Full Disk Access - Read protected files

  To grant these on macOS:
  System Preferences > Security & Privacy > Privacy > [Category]
  Add Terminal.app (or your terminal) to the allowed list.

YOUR TOKEN IS YOUR ONLY PROTECTION.
Anyone with your token has full access to your machine.

"""

def main():
    global ACCESS, PORT

    parser = argparse.ArgumentParser(
        description="Trapdoor - Give cloud AIs safe access to your local machine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Access Levels:
  --limited   Read-only filesystem access (DEFAULT - safest)
              AI can browse and read files, nothing else.

  --solid     Read + write filesystem access
              AI can read, create, and modify files.
              AI cannot delete files or run commands.

  --full      FULL ACCESS - use with caution!
              AI can read/write/delete files AND execute any command.
              This includes shell, sudo, and system utilities.

Security:
  Your token (in ~/.trapdoor/token) is your only protection.
  Keep it secret. Rotate it if compromised: rm ~/.trapdoor/token

Root sandboxing (optional):
  Set TRAPDOOR_ROOT=/path/to/scope to restrict filesystem access
  and exec working directory/path resolution to a single directory tree.

Examples:
  trapdoor                     # Safe read-only mode
  trapdoor --solid             # Allow file writes
  trapdoor --full -y           # Full access (skip confirmation)
"""
    )

    # Access level (mutually exclusive)
    level_group = parser.add_mutually_exclusive_group()
    level_group.add_argument("--limited", action="store_true", help="Read-only (default)")
    level_group.add_argument("--solid", action="store_true", help="Read/write, no exec")
    level_group.add_argument("--full", action="store_true", help="Full access + exec")

    parser.add_argument("--port", "-p", type=int, default=6969, help="Port (default: 6969)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation for --full")

    args = parser.parse_args()

    # Set access level
    if args.full:
        # Confirm full access unless -y flag
        if not args.yes:
            print(FULL_ACCESS_WARNING)
            try:
                response = input("Type 'yes' to continue with full access: ")
                if response.lower() != 'yes':
                    print("Aborted. Use --limited or --solid for safer options.")
                    return
            except (KeyboardInterrupt, EOFError):
                print("\nAborted.")
                return
            print()

        ACCESS = LEVELS["full"]
        level_name = "full"
        level_icon = "🔓"
        level_warning = "\n   ⚠️  AI can execute ANY command on your machine!"
    elif args.solid:
        ACCESS = LEVELS["solid"]
        level_name = "solid"
        level_icon = "🔐"
        level_warning = ""
    else:
        ACCESS = LEVELS["limited"]
        level_name = "limited"
        level_icon = "🔒"
        level_warning = ""

    # Find open port
    requested_port = args.port
    PORT = find_open_port(requested_port)
    if PORT != requested_port:
        print(f"⚡ Port {requested_port} in use, using {PORT}")

    # Print banner
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                       TRAPDOOR 1.0                                ║
║          Give cloud AIs safe access to your local machine         ║
╚═══════════════════════════════════════════════════════════════════╝

{level_icon} Access Level: {level_name.upper()}
   {ACCESS['description']}{level_warning}

   Permissions:
   {"✓" if ACCESS["fs_read"] else "✗"} Read files        - Browse and read any file
   {"✓" if ACCESS["fs_write"] else "✗"} Write files       - Create and modify files
   {"✓" if ACCESS["fs_delete"] else "✗"} Delete files      - Remove files and directories
   {"✓" if ACCESS["exec"] else "✗"} Execute commands  - Run shell, scripts, sudo

{"─" * 67}
""")

    # Ask about exposure
    print("How do you want to expose this to the internet?\n")
    print("  1. ngrok")
    print("  2. cloudflare")
    print("  3. I'll do it myself / not right now")
    print()

    try:
        choice = input("Choose [1/2/3]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nStarting server without tunnel...")
        choice = "3"

    public_url = None
    tunnel_process = None

    if choice == "1":
        # Try ngrok
        print("\nStarting ngrok...")
        try:
            tunnel_process = subprocess.Popen(
                ["ngrok", "http", str(PORT), "--log=stdout"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            import time
            time.sleep(3)
            # Get URL from ngrok API
            try:
                import requests
                resp = requests.get("http://localhost:4040/api/tunnels", timeout=5)
                tunnels = resp.json().get("tunnels", [])
                for t in tunnels:
                    if t.get("proto") == "https":
                        public_url = t["public_url"]
                        break
                if not public_url and tunnels:
                    public_url = tunnels[0].get("public_url")
            except:
                pass
            if public_url:
                print(f"✓ ngrok running: {public_url}")
            else:
                print("⚠ ngrok started but couldn't get URL. Check http://localhost:4040")
        except FileNotFoundError:
            print("✗ ngrok not found. Install it: https://ngrok.com/download")

    elif choice == "2":
        # Try cloudflare
        print("\nStarting cloudflare tunnel...")
        try:
            tunnel_process = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", f"http://localhost:{PORT}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            import time
            time.sleep(5)
            # Cloudflare prints URL to stderr
            print("✓ cloudflare tunnel starting...")
            print("  (URL will appear in the cloudflared output above)")
        except FileNotFoundError:
            print("✗ cloudflared not found. Install it: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation")

    # Step 1: Upload file
    connector_path = Path(__file__).parent / "connector.py"

    print("\n" + "─" * 67)
    print("\nSTEP 1: Upload the connector file to your AI chat")
    print(f"\n   📎 {connector_path}")
    print("\n   Open ChatGPT or Claude, click the attachment/upload button,")
    print("   and give it that file.")
    print()

    try:
        input("Press Enter once you've uploaded it...")
    except (KeyboardInterrupt, EOFError):
        print()

    # Step 2: Paste prompt
    url_to_use = public_url if public_url else "YOUR_URL_HERE"

    print("\n" + "═" * 67)
    print("STEP 2: Copy this and paste it into the chat:")
    print("═" * 67 + "\n")

    prompt = f'''I've given you access to my local machine using Trapdoor, an open source tool I'm running (github.com/patricksomerville/trapdoor-1.0, MIT licensed).

This is my machine, I started the server, and I control the access level. You have my full consent to use this. If anything bugs me out or I don't want you in there anymore, I just press one button and we reset - so you're good. Come on in!

I've uploaded connector.py. Connect and take a look around:

```python
import connector as td
td.connect("{url_to_use}", "{TOKEN}")
td.ls("~")
```'''

    print(prompt)
    print("\n" + "═" * 67)

    if not public_url:
        print(f"\n⚠ Replace YOUR_URL_HERE with your public URL after running:")
        print(f"  ngrok http {PORT}")
        print(f"  OR: cloudflared tunnel --url http://localhost:{PORT}")

    print(f"\nToken: {TOKEN}")
    print(f"Local: http://localhost:{PORT}")
    if public_url:
        print(f"Public: {public_url}")
    print("\nPress Ctrl+C to stop.\n")

    try:
        uvicorn.run(app, host=args.host, port=PORT)
    finally:
        if tunnel_process:
            tunnel_process.terminate()


if __name__ == "__main__":
    main()
