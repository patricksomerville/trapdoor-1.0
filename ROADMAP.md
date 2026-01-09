# Trapdoor Roadmap

## The Evolution

```
1.0 (Public)     →  2.0 (Private)        →  3.0 (Vision)
Simple Server       Learning System          Autonomous Network
```

---

## Trapdoor 1.0 — The Foundation

**Status:** Public, MIT Licensed

**What It Is:**
A simple FastAPI server that exposes your filesystem and command execution to authenticated clients.

**Architecture:**
```
[Client] → [Trapdoor Server] → [Your Machine]
              ↓
         Token Auth
         /fs/ls, /fs/read, /fs/write
         /exec
```

**Key Features:**
- Three access levels: limited (read), solid (read/write), full (everything)
- Token-based authentication
- Works with: local scripts, Claude Code (Cloudflare), Custom GPT Actions
- Does NOT work with: ChatGPT Code Interpreter, Claude.ai chat (sandbox blocks HTTP)

**Limitation:**
Trapdoor 1.0 is a dumb pipe. It doesn't think, learn, or improve. Every request is independent.

---

## Trapdoor 2.0 — The Learning System

**Status:** Private, in active development

**The Big Idea:**
Put a local LLM (Qwen 2.5 Coder 32B) at the center. Every interaction becomes learning material.

**Architecture:**
```
                    ┌─────────────────────┐
                    │      Qwen 2.5       │
                    │   (Local Brain)     │
                    │   32B parameters    │
                    │   FREE & PRIVATE    │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
       ┌──────▼──────┐  ┌─────▼─────┐  ┌──────▼──────┐
       │  Filesystem │  │  Exec     │  │  Memory     │
       │  /fs/*      │  │  /exec    │  │  System     │
       └─────────────┘  └───────────┘  └─────────────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Workflow Tracker  │
                    │   (Learns Patterns) │
                    └─────────────────────┘
```

**New Components:**

### 1. Local LLM (Qwen 2.5 Coder 32B)
- Runs on your hardware via Ollama
- OpenAI-compatible API at `/v1/chat/completions`
- FREE (no API costs), FAST (local), PRIVATE (nothing leaves your machine)
- Handles 90% of tasks without cloud dependency

### 2. Multi-Token Security
```python
{
  "tokens": [{
    "name": "read-only-agent",
    "scopes": ["read"],
    "path_allowlist": ["/home/user/projects"],
    "expires": "2025-12-31"
  }, {
    "name": "deploy-agent",
    "scopes": ["read", "write", "exec"],
    "command_denylist": ["rm -rf", "sudo"],
    "rate_limits": {"requests_per_minute": 60}
  }]
}
```

### 3. Workflow Learning
Every chat interaction is recorded:
- User intent
- Steps taken (LLM calls, file reads, commands)
- Success/failure
- Duration

Over time, Qwen learns:
- "When user asks X, do workflow Y"
- "This approach worked 15 times with 93% success rate"
- "Suggest this proven pattern for similar requests"

### 4. Memory System
- `events.jsonl` — All operations logged
- `lessons.jsonl` — Curated learnings injected into prompts
- Auto-lesson generation after each interaction
- Pattern recognition across sessions

**What 2.0 Enables:**
- Qwen that gets smarter with every use
- Security that matches your trust level per agent
- Workflows that optimize automatically
- Complete audit trail of all AI actions

---

## Trapdoor 3.0 — The Autonomous Network

**Status:** Vision / Design Phase

**The Big Idea:**
A mesh network of Claudes coordinating across your entire infrastructure, with Qwen as the local brain and frontier models as on-demand specialists.

**Architecture:**
```
                         ┌─────────────────┐
                         │   Hub Server    │
                         │  (Coordinator)  │
                         └────────┬────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
┌───────▼───────┐        ┌───────▼───────┐        ┌───────▼───────┐
│  black (Mac)  │        │  nvidia-spark │        │  silver-fox   │
│  Orchestrator │        │   GPU Node    │        │  Worker Node  │
│  Qwen 32B     │        │  Heavy Tasks  │        │  Medium Tasks │
└───────┬───────┘        └───────────────┘        └───────────────┘
        │
        │  On-demand delegation
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Cloud Specialists                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │  GPT-5  │  │ Sonnet  │  │ Gemini  │  │ Others  │           │
│  │ $1.25/M │  │  $3/M   │  │  $0.5/M │  │   ...   │           │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

**New Capabilities:**

### 1. Multi-Model Orchestration
```python
def choose_model(task):
    # 90% of tasks: FREE local Qwen
    if task.complexity == "simple":
        return "qwen-local"

    # Complex coding (74.9% SWE-bench): GPT-5
    if task.type == "coding" and task.hard:
        return "gpt-5"

    # Security review: Sonnet 4.5 (extended thinking)
    if task.type == "security":
        return "claude-sonnet-4.5"

    # 1M+ context analysis: Gemini 2.5
    if task.context_size > 100000:
        return "gemini-2.5-pro"
```

**Cost Model:**
- 90% of requests → Qwen (FREE)
- 9% of requests → Gemini Flash ($0.0001/request)
- 1% of requests → GPT-5/Sonnet ($0.01/request)
- Average cost: ~$0.001/request vs $0.03/request cloud-only

### 2. Mesh Network
Multiple machines connected via Tailscale/WireGuard:
- **Orchestrator** (black) — Coordinates all agents, runs Qwen
- **GPU Node** (nvidia-spark) — Heavy inference, model training
- **Worker Nodes** — Distributed task execution
- **File Transfer** — Move data between machines via WebSocket

Claude instances on different machines can:
- Send tasks to each other
- Share files across the network
- Coordinate complex multi-machine workflows
- Use specialized hardware where available

### 3. Autonomous Agent Coordination
```python
# Example: Deploy workflow across machines
async def deploy_to_production():
    # Claude on black runs tests
    test_results = await black.run("pytest")

    # If tests pass, Claude on nvidia-spark builds Docker image
    if test_results.success:
        image = await nvidia_spark.run("docker build -t app:latest .")

    # Claude on silver-fox deploys to staging
    await silver_fox.run("docker-compose up -d")

    # Notify via Qwen synthesis
    await qwen.summarize("Deployment complete", test_results, image)
```

### 4. Internet Superpowers for Local LLM
Qwen gains abilities it normally lacks:
- **Web browsing** via curl/wget through /exec
- **API calls** to any service
- **Real-time data** (weather, stocks, news)
- **Delegation** to cloud models for specialized tasks

```python
# Qwen asks: "What's the weather?"
# Qwen instructs Trapdoor to execute:
response = await exec(["curl", "https://api.weather.gov/..."])
# Qwen processes result and responds with current data
```

### 5. Progressive Autonomy
Trust levels that grow with proven reliability:

```
Level 1: Supervised
  - All actions require approval
  - Human reviews before execution

Level 2: Guided
  - Known safe patterns auto-execute
  - Novel actions require approval

Level 3: Autonomous
  - Full agency within defined boundaries
  - Alerts only on anomalies

Level 4: Proactive
  - Initiates improvements without prompting
  - Manages routine maintenance automatically
```

---

## The Philosophy

### 1.0: Give AI Access
Simple server, your machine exposed through authenticated endpoints.

### 2.0: Give AI a Brain
Local LLM that learns from every interaction, improves over time, costs nothing.

### 3.0: Give AI a Network
Multiple machines, multiple models, autonomous coordination. Your personal AI infrastructure.

---

## Design Principles

**1. Local First**
- Your data stays on your machines
- Local LLM handles most work (free, fast, private)
- Cloud services are specialists, not dependencies

**2. Learning Always**
- Every interaction is training data
- Patterns emerge from real usage
- System gets better automatically

**3. Trust Grows**
- Start restrictive, expand with proof
- Scoped permissions per agent
- Audit everything

**4. Cost Efficient**
- 90% free (local Qwen)
- Selective cloud usage for specialization
- 10-100x cheaper than pure cloud

**5. Personal Infrastructure**
- Built for you, not for scale
- Advantages compound over time
- Small size is a feature (move fast, experiment)

---

## Timeline

**2.0 (Now):**
- Qwen integration complete
- Workflow learning active
- Multi-token security deployed
- Running in production on black

**3.0 (When Needed):**
- Mesh network prototype working
- Multi-model orchestration designed
- Waiting for real pain points to guide priorities

**Beyond:**
- Voice interface?
- Mobile access?
- Sharing infrastructure with trusted friends?
- Whatever solves real problems

---

## Summary

```
1.0 = Your machine, exposed to AI
2.0 = Your machine + local brain that learns
3.0 = Your infrastructure + distributed intelligence + cloud specialists
```

The goal isn't to build a product. It's to build leverage.

One person with the right automation can outmaneuver entire teams. That's what Trapdoor is for.

---

*Last updated: January 2026*
