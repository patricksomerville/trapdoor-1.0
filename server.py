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

PORT = 8080
TOKEN_FILE = Path.home() / ".trapdoor" / "token"

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

def require_auth(authorization: Optional[str] = Header(None)) -> str:
    """Validate Bearer token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.split(" ", 1)[1]
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
        "timestamp": datetime.now().isoformat()
    }

# ==============================================================================
# Filesystem Endpoints
# ==============================================================================

@app.get("/fs/ls")
def fs_ls(
    path: str = Query("/"),
    authorization: Optional[str] = Header(None)
):
    """List directory contents"""
    require_auth(authorization)

    if not ACCESS["fs_read"]:
        raise HTTPException(status_code=403, detail="Read access disabled")

    target = Path(path).expanduser().resolve()

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
    authorization: Optional[str] = Header(None)
):
    """Read file contents"""
    require_auth(authorization)

    if not ACCESS["fs_read"]:
        raise HTTPException(status_code=403, detail="Read access disabled")

    target = Path(path).expanduser().resolve()

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
    authorization: Optional[str] = Header(None)
):
    """Write content to file"""
    require_auth(authorization)

    if not ACCESS["fs_write"]:
        raise HTTPException(status_code=403, detail="Write access disabled. Start with --solid or --full")

    target = Path(req.path).expanduser().resolve()
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
    authorization: Optional[str] = Header(None)
):
    """Create directory"""
    require_auth(authorization)

    if not ACCESS["fs_write"]:
        raise HTTPException(status_code=403, detail="Write access disabled. Start with --solid or --full")

    target = Path(req.path).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    return {"path": str(target), "created": True}


@app.post("/fs/rm")
def fs_rm(
    req: RmRequest,
    authorization: Optional[str] = Header(None)
):
    """Remove file or directory"""
    require_auth(authorization)

    if not ACCESS["fs_delete"]:
        raise HTTPException(status_code=403, detail="Delete access disabled. Start with --full")

    target = Path(req.path).expanduser().resolve()

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
    authorization: Optional[str] = Header(None)
):
    """Execute shell command"""
    require_auth(authorization)

    if not ACCESS["exec"]:
        raise HTTPException(status_code=403, detail="Exec disabled. Start with --full to enable")

    try:
        result = subprocess.run(
            req.cmd,
            cwd=req.cwd,
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
    authorization: Optional[str] = Header(None)
):
    """OpenAI-compatible chat endpoint (optional LLM proxy)"""
    require_auth(authorization)

    ollama_host = os.getenv("OLLAMA_HOST")

    if ollama_host:
        import requests
        resp = requests.post(
            f"{ollama_host}/v1/chat/completions",
            json={"model": req.model, "messages": req.messages}
        )
        return resp.json()

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

    parser.add_argument("--port", "-p", type=int, default=8080, help="Port (default: 8080)")
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

    PORT = args.port

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

🌐 Server:  http://localhost:{PORT}
🔑 Token:   {TOKEN}
📁 Config:  {TOKEN_FILE}

To expose publicly:
    ngrok http {PORT}

Then upload connector.py to ChatGPT/Claude with your URL + token
{"─" * 67}
""")

    uvicorn.run(app, host=args.host, port=PORT)


if __name__ == "__main__":
    main()
