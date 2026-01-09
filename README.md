# Trapdoor

**Give cloud AIs access to your local machine.**

I'm not a dev, just trying to solve a problem I found frustrating when I first started to understand how annoying it was that the things I paid for couldn't help me with other things I paid for. I'm sure there's a better and smarter version of this somewhere, but this is what I made. It makes me happy if it helps you! Be careful, of course, but you're a grownup (I think?).

—patrick

---

## Install

```bash
pip install fastapi uvicorn requests
```

## Run

```bash
python server.py              # read-only (default)
python server.py --solid      # read + write
python server.py --full       # everything
```

## Use

Upload `connector.py` to ChatGPT/Claude, then:

```python
import connector as td
td.connect("https://your-ngrok-url.ngrok.io", "your-token")
td.ls("/home")
td.read("/path/to/file.txt")
```

## Expose

```bash
ngrok http 8080
```

## Revoke

```bash
rm ~/.trapdoor/token
```

## License

MIT
