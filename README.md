# Trapdoor 1.0

**Give cloud AIs access to your local machine.**

I'm not a dev, just trying to solve a problem I found frustrating when I first started to understand how annoying it was that the things I paid for couldn't help me with other things I paid for. I'm sure there's a better and smarter version of this somewhere, but this is what I made. It makes me happy if it helps you! Be careful, of course, but you're a grownup (I think?).

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
- **Claude Code** (the CLI tool) can reach trusted domains like Cloudflare tunnels
- **Local scripts** work perfectly (no sandbox)
- **Custom GPT Actions** use a different mechanism that does work

---

## Install & Run

```bash
cd trapdoor-1.0
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn requests
python server.py
```

Access levels:
```bash
python server.py              # read-only (default)
python server.py --solid      # read + write
python server.py --full       # everything including exec
```

---

## For Local Scripts (Works)

```python
import requests

BASE_URL = "https://your-tunnel-url.com"
TOKEN = "your-token"
headers = {"Authorization": f"Bearer {TOKEN}"}

# List files
resp = requests.get(f"{BASE_URL}/ls", params={"path": "~"}, headers=headers)
print(resp.json())

# Read file
resp = requests.get(f"{BASE_URL}/read", params={"path": "/path/to/file"}, headers=headers)
print(resp.json())
```

---

## For Claude Code (Works with Cloudflare)

If you're using Claude Code CLI with a Cloudflare tunnel:

```bash
# Your trapdoor is at: https://trapdoor.yourdomain.com
# Claude Code's WebFetch can reach this
```

Claude Code can use WebFetch to connect, and with query param auth (`?token=xxx`), it has full access.

---

## For Custom GPT Actions (Works)

Create an OpenAPI spec pointing to your Trapdoor:

```json
{
  "openapi": "3.0.0",
  "servers": [{"url": "https://your-trapdoor-url.com"}],
  "paths": {
    "/ls": {"get": {"operationId": "listFiles", ...}},
    "/read": {"get": {"operationId": "readFile", ...}},
    "/exec": {"post": {"operationId": "executeCommand", ...}}
  }
}
```

This works because Custom GPT Actions use a different mechanism than Code Interpreter.

---

## Expose

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
rm ~/.trapdoor/token
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
