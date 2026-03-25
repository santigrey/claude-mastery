# Claude Mastery — Spin Up SOP
## Standard Operating Procedure for Environment Setup

---

## PREREQUISITES

### Required on JesAir (Primary Dev Machine)
- Python 3.x installed (`python3 --version`)
- Git installed (`git --version`)
- SSH key at `~/.ssh/id_ed25519_mcp` (for homelab access)
- Anthropic API key (console.anthropic.com)

### Required Infrastructure (Homelab)
- CiscoKid (192.168.1.10) — SSH accessible, Docker running
- TheBeast (192.168.1.152) — Ollama running on port 11434
- SlimJim (192.168.1.40) — online and accessible

---

## STEP 1 — CLONE THE REPO

If starting fresh on any machine:

```bash
cd ~
git clone https://github.com/santigrey/claude-mastery.git
cd claude-mastery
```

If repo already exists, pull latest:

```bash
cd ~/claude-mastery
git pull
```

---

## STEP 2 — CREATE VIRTUAL ENVIRONMENT

```bash
cd ~/claude-mastery
python3 -m venv .venv
source .venv/bin/activate
```

Verify activation — prompt should show `(.venv)`.

---

## STEP 3 — INSTALL DEPENDENCIES

```bash
pip install anthropic python-dotenv requests ollama
```

Verify:

```bash
python3 -c "import anthropic; print('anthropic', anthropic.__version__)"
python3 -c "import requests; print('requests', requests.__version__)"
```

---

## STEP 4 — CREATE .env FILE

```bash
nano .env
```

Add exactly this (no quotes, no spaces around =):

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Save: `Ctrl+X` → `Y` → `Enter`

Verify key loads:

```bash
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('ANTHROPIC_API_KEY')[:20])"
```

---

## STEP 5 — VERIFY ANTHROPIC API

```bash
python3 hello_claude.py
```

Expected output:
```
=== RESPONSE ===
[Claude responds with AI engineering answer]

=== METADATA ===
Model: claude-sonnet-4-20250514
Input tokens: ...
Output tokens: ...
Stop reason: end_turn
```

---

## STEP 6 — VERIFY HOMELAB CONNECTIONS

### Check CiscoKid:
```bash
ssh -i ~/.ssh/id_ed25519_mcp -o StrictHostKeyChecking=no jes@192.168.1.10 "uptime"
```

### Check TheBeast Ollama:
```bash
curl -s http://192.168.1.152:11434/api/tags | python3 -m json.tool | grep name
```

Expected: `llama3.1:8b` and `mxbai-embed-large` listed.

### Check SlimJim:
```bash
ssh -i ~/.ssh/id_ed25519_mcp -o StrictHostKeyChecking=no jes@192.168.1.40 "uptime"
```

---

## STEP 7 — VERIFY OLLAMA FALLBACK

```bash
python3 ollama_client.py
```

Expected output:
```
Testing Ollama connection to TheBeast...
Ollama is UP at http://192.168.1.152:11434
Response: [one sentence answer]
Stop reason: end_turn
```

---

## STEP 8 — RUN EVALS (HEALTH CHECK)

```bash
python3 evals.py
```

Expected: `Score: 100.0%` — if below 90% something is broken.

---

## LAUNCH EACH TOOL

### Claude CLI (multi-persona assistant)
```bash
cd ~/claude-mastery
source .venv/bin/activate
cd claude-cli
python3 claude_cli.py
```

### Clawdbot (live homelab assistant) ← PRIMARY DEMO TOOL
```bash
cd ~/claude-mastery
source .venv/bin/activate
cd clawdbot
python3 clawdbot.py
```
Type `status` on first launch to verify all connections.

### ReAct Agent
```bash
cd ~/claude-mastery
source .venv/bin/activate
python3 react_agent.py
```

### Task Planning Agent
```bash
cd ~/claude-mastery
source .venv/bin/activate
python3 task_agent.py
```

### Code Pipeline
```bash
cd ~/claude-mastery
source .venv/bin/activate
python3 code_pipeline.py
```

### Evals Harness
```bash
cd ~/claude-mastery
source .venv/bin/activate
python3 evals.py
```

---

## TROUBLESHOOTING

### API Key Not Loading
```bash
cat .env
```
Must show: `ANTHROPIC_API_KEY=sk-ant-...`
No quotes. No spaces. Must be in `~/claude-mastery/.env`

### Anthropic 529 Overloaded
Check status: https://status.anthropic.com
Retry logic is built in — wait it out or Ollama fallback activates automatically.

### SSH Permission Denied to JesAir
From any device, add your public key to JesAir:
```bash
# On JesAir
nano ~/.ssh/authorized_keys
# Paste your device's public key
chmod 600 ~/.ssh/authorized_keys
```

### SSH Permission Denied to Homelab
Verify MCP key exists:
```bash
ls -la ~/.ssh/id_ed25519_mcp
```
If missing, regenerate and add to CiscoKid/TheBeast/SlimJim authorized_keys.

### Ollama Not Reachable
Check TheBeast is powered on and Ollama service is running:
```bash
ssh -i ~/.ssh/id_ed25519_mcp jes@192.168.1.152 "systemctl status ollama"
```

### venv Not Activating
```bash
cd ~/claude-mastery
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install anthropic python-dotenv requests ollama
```

### Clawdbot Memory Search Failing
pgvector query requires Ollama for embeddings. If TheBeast is down,
memory search will return an error but other tools still work.

---

## DEVICE-SPECIFIC NOTES

| Device | OS | Activate venv | SSH to JesAir |
|--------|----|---------------|---------------|
| JesAir | macOS | `source .venv/bin/activate` | N/A (local) |
| Mac Mini | macOS | `source .venv/bin/activate` | `ssh jes@192.168.1.155` |
| Cortez | Windows | `.venv\Scripts\Activate.ps1` | `ssh jes@192.168.1.155` |

---

## QUICK REFERENCE — HOMELAB IPs

| Server | IP | Role | User |
|--------|----|------|------|
| JesAir | 192.168.1.155 | Primary dev | jes |
| Mac Mini | 192.168.1.13 | Command center | jes |
| CiscoKid | 192.168.1.10 | Control plane | jes |
| TheBeast | 192.168.1.152 | GPU inference | jes |
| SlimJim | 192.168.1.40 | Edge/available | jes |
| KaliPi | 192.168.1.254 | Pentesting | sloan |

---

## DAILY WORKFLOW

```
1. cd ~/claude-mastery
2. source .venv/bin/activate
3. git pull
4. python3 hello_claude.py  ← verify API
5. Launch what you need
```

---

*Last updated: 2026-03-25*
*Repo: github.com/santigrey/claude-mastery*
