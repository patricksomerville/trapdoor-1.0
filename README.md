# Trapdoor 1.0

**Give cloud AIs safe access to your local machine.**

Upload a connector script to ChatGPT, Claude, or any sandboxed AI - and let it read your files, write code, and run commands on your machine.

## Quick Start

```bash
# Install
pip install fastapi uvicorn requests

# Run (safe read-only mode by default)
python server.py

# Expose publicly
ngrok http 8080
```

Upload `connector.py` to your AI chat, then:

```python
import connector as td
td.connect("https://abc123.ngrok.io", "your-token")
td.ls("/home")
td.read("/home/user/notes.txt")
```

## Access Levels

```bash
python server.py              # 🔒 LIMITED - read only (default)
python server.py --solid      # 🔐 SOLID   - read + write
python server.py --full       # 🔓 FULL    - everything + exec
```

| Level | Read | Write | Delete | Exec |
|-------|------|-------|--------|------|
| `--limited` | ✓ | ✗ | ✗ | ✗ |
| `--solid` | ✓ | ✓ | ✗ | ✗ |
| `--full` | ✓ | ✓ | ✓ | ✓ |

**Full access** requires confirmation (or `-y` to skip):
- Grants shell, sudo, system utilities
- On macOS: can use screen capture, mic, camera if you've granted those permissions

## API

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/fs/ls?path=...` | GET | Yes | List directory |
| `/fs/read?path=...` | GET | Yes | Read file |
| `/fs/write` | POST | Yes | Write file |
| `/fs/mkdir` | POST | Yes | Create directory |
| `/fs/rm` | POST | Yes | Remove file/dir |
| `/exec` | POST | Yes | Execute command |

## Security

Your token is your only protection:

```bash
# Token location
~/.trapdoor/token

# Revoke access instantly
rm ~/.trapdoor/token

# New token generated on next start
python server.py
```

## Files

```
v1/
├── server.py      # The server (~500 lines)
├── connector.py   # Upload to AI chats
└── README.md      # You're here
```

## Roadmap

- **1.0** ✅ Core server with access levels
- **1.1** Instructions file + session logging
- **1.2** Blocklist patterns
- **1.5** Local chat gateway mode

## License

MIT
