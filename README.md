# Trapdoor 1.0

**Give cloud AIs access to your local machine.** A tiny FastAPI bridge with access tiers.

I'm not a dev—just frustrated that the things I paid for wouldn't talk to each other. This is the minimal thing I made. It works; be careful.

But truly, be careful. This is a door into your computer. The callers are coming either way; this at least lets you control the door.

## How this started

I'm not a dev, just a man with insomnia and a hobbyist. The fun problem to solve was how a simple fetch could be enough to get cloud models talking to your filesystem. Before I even knew what endpoints were, I just dropped a local model at the other end of a tunnel and set it up to enact commands when they came through.

—patrick

---

## What Works (and What Doesn't)

**The Reality Check:**

| Client | Can Connect? | Why |
|--------|-------------|-----|
| Local Python/Node/curl | **Yes** | No sandbox restrictions |
| Claude Code (WebFetch) | **Yes** | Cloudflare domains are trusted |
| Custom GPT Actions | **Yes** | Different mechanism (OpenAPI spec) |
| ChatGPT Code Interpreter | **No** | Sandbox blocks ALL outbound HTTP |
| Claude.ai chat | **No** | Sandbox blocks outbound HTTP |

**The Key Discovery:** AI chat sandboxes (ChatGPT Code Interpreter, Claude.ai) block outbound HTTP requests entirely. The "upload connector.py" approach was designed assuming the AI could make HTTP calls—it can't.

**What Actually Works:**
- **Claude Code** (CLI) can reach trusted domains like Cloudflare tunnels.
- **Local scripts** work perfectly (no sandbox).
- **Custom GPT Actions** use a different mechanism that does work.

---

## Install & Run

```bash
cd trapdoor-1.0
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn requests
python server.py
```

Access levels (pick the smallest that works):
```bash
python server.py                   # read-only (default)
python server.py --solid           # read + write (no exec)
python server.py --full -y         # everything (exec/delete) — only if you mean it

# Safer defaults
# Use a sandbox root and a fresh token each run
python server.py --root /tmp/trapdoor --rotate-token
```

---

## For Local Scripts (Works)

```python
import requests

BASE_URL = "https://your-tunnel-url.com"
TOKEN = "your-token"
headers = {"Authorization": f"Bearer {TOKEN}"}

# List files
resp = requests.get(f"{BASE_URL}/fs/ls", params={"path": "~"}, headers=headers)
print(resp.json())

# Read file
resp = requests.get(f"{BASE_URL}/fs/read", params={"path": "/path/to/file"}, headers=headers)
print(resp.json())
```

---

## For Claude Code (Works with Cloudflare)

If you're using Claude Code CLI with a Cloudflare tunnel:

```bash
# Your trapdoor is at: https://trapdoor.yourdomain.com
# Claude Code's WebFetch can reach this
```

Claude Code can use WebFetch to connect; keep using Bearer auth headers (or short-lived query tokens if you must).

---

## For Custom GPT Actions (Works)

Create an OpenAPI spec pointing to your Trapdoor:

```json
{
  "openapi": "3.0.0",
  "servers": [{"url": "https://your-trapdoor-url.com"}],
  "paths": {
    "/fs/ls": {"get": {"operationId": "listFiles"}},
    "/fs/read": {"get": {"operationId": "readFile"}},
    "/exec": {"post": {"operationId": "executeCommand"}}
  }
}
```

This works because Custom GPT Actions use a different mechanism than Code Interpreter.

---

## Expose (optional)

Skip this if you're just using it locally. If you must expose it, use a fresh token, `--solid` (no exec), and kill the tunnel when done.

```bash
# Option 1: ngrok (dynamic URL)
ngrok http 6969

# Option 2: Cloudflare tunnel (stable URL, trusted by Claude Code)
cloudflared tunnel --url http://localhost:6969
```

**Recommendation:** Use Cloudflare with a custom domain for stable, trusted access.

---

## Revoke

```bash
rm ~/.trapdoor/token            # or restart with --rotate-token
```

---

## What's Next?

This is Trapdoor 1.0—a simple server that exposes your filesystem and commands.

**Trapdoor 2.0** (private, in development) adds:
- Local LLM (Qwen 2.5 Coder 32B) as the brain
- Multi-token security with scoped permissions
- Workflow learning from every interaction
- Memory system that improves over time

**Trapdoor 3.0** (vision) will add:
- Multi-model orchestration (local + cloud specialists)
- Mesh network across multiple machines
- Autonomous agent coordination

---

## License

MIT
