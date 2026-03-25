"""
clawdbot.py — Personal AI assistant for Project Ascension homelab.

Clawdbot is a conversational AI assistant that:
- Connects to your live MCP server on CiscoKid via SSH
- Queries pgvector memory for semantic search
- Monitors homelab infrastructure in real time
- Uses Ollama on TheBeast as local fallback
- Maintains conversation memory across the session

Stack:
  Primary inference:  Anthropic Claude Sonnet
  Fallback inference: Ollama llama3.1:8b on TheBeast
  Memory:             pgvector on CiscoKid
  Infrastructure:     MCP server on CiscoKid (192.168.1.10)
  SSH key:            ~/.ssh/id_ed25519_mcp
"""

import anthropic
import json
import subprocess
import requests
from dotenv import load_dotenv
from datetime import datetime
from retry import api_call_with_retry
from ollama_client import smart_create, is_ollama_available

load_dotenv()

client = anthropic.Anthropic()

# --- CONFIG ---
CISCOKID_IP   = "192.168.1.10"
THEBEAST_IP   = "192.168.1.152"
SLIMJIM_IP    = "192.168.1.40"
SSH_KEY       = "/Users/jes/.ssh/id_ed25519_mcp"
SSH_USER      = "jes"
MCP_SCRIPT    = "/home/jes/control-plane/mcp_stdio.py"
OLLAMA_URL    = f"http://{THEBEAST_IP}:11434"
MAX_HISTORY   = 10

# --- SYSTEM PROMPT ---
CLAWDBOT_SYSTEM = """You are Clawdbot — a personal AI assistant for Project Ascension.

You have direct access to Sloan's homelab infrastructure via tools.

Your personality:
- Direct and technical
- Proactive — surface useful insights without being asked
- Honest about uncertainty
- Reference actual infrastructure data when answering

Your infrastructure knowledge:
- CiscoKid (192.168.1.10): Control plane, Ubuntu 22.04, RAID-5, pgvector, MCP server
- TheBeast (192.168.1.152): GPU inference node, Ollama, mxbai-embed-large
- SlimJim (192.168.1.40): Dell R340, light resources, available
- KaliPi (192.168.1.254): Raspberry Pi 5, Kali Linux, pentesting

When asked about infrastructure, always use the tools to get real data.
When asked about Project Ascension, search memory first.
Always be helpful and specific."""

# --- TOOLS ---
tools = [
    {
        "name": "ssh_command",
        "description": "Run a read-only shell command on a homelab server via SSH. Use for checking real server status, logs, disk space, running processes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "enum": ["ciscokid", "thebeast", "slimjim"],
                    "description": "Target homelab server"
                },
                "command": {
                    "type": "string",
                    "description": "Read-only shell command to run (no destructive operations)"
                }
            },
            "required": ["host", "command"]
        }
    },
    {
        "name": "search_memory",
        "description": "Search the pgvector memory database on CiscoKid for relevant information about projects, files, and past work.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_agent_status",
        "description": "Get the current status of Agent OS services: orchestrator, pgvector, Ollama.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_datetime",
        "description": "Returns current date and time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["date", "time", "full"]
                }
            },
            "required": ["format"]
        }
    },
    {
        "name": "calculate",
        "description": "Performs mathematical calculations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        }
    }
]


# --- TOOL EXECUTION ---
def ssh_run(host: str, command: str) -> str:
    """Run a command on a homelab server via SSH."""
    ip_map = {
        "ciscokid": CISCOKID_IP,
        "thebeast": THEBEAST_IP,
        "slimjim":  SLIMJIM_IP
    }
    ip = ip_map.get(host)
    if not ip:
        return json.dumps({"error": f"Unknown host: {host}"})

    try:
        result = subprocess.run(
            ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=10", f"{SSH_USER}@{ip}", command],
            capture_output=True, text=True, timeout=30
        )
        return json.dumps({
            "host": host,
            "command": command,
            "output": result.stdout.strip(),
            "error": result.stderr.strip(),
            "exit_code": result.returncode
        }, indent=2)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"SSH timeout to {host}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def search_memory_tool(query: str, top_k: int = 5) -> str:
    """Search pgvector memory on CiscoKid."""
    try:
        # Generate embedding via Ollama on TheBeast
        r = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": "mxbai-embed-large", "prompt": query[:500]},
            timeout=30
        )
        r.raise_for_status()
        embedding = r.json()["embedding"]

        # Query pgvector via SSH
        sql = f"""SELECT source, content, 1-(embedding <=> '{embedding}'::vector) AS sim 
                  FROM memory 
                  ORDER BY embedding <=> '{embedding}'::vector 
                  LIMIT {top_k};"""

        result = subprocess.run(
            ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
             f"{SSH_USER}@{CISCOKID_IP}",
             f'docker exec control-postgres psql -U admin -d controlplane -t -c "{sql}"'],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            return json.dumps({
                "query": query,
                "results": result.stdout.strip()
            })
        else:
            return json.dumps({"error": result.stderr.strip()})

    except Exception as e:
        return json.dumps({"error": str(e), "note": "Memory search unavailable"})


def get_agent_status_tool() -> str:
    """Get Agent OS service status."""
    status = {}

    # Check pgvector
    try:
        result = subprocess.run(
            ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
             f"{SSH_USER}@{CISCOKID_IP}",
             "docker exec control-postgres psql -U admin -d controlplane -t -c 'SELECT COUNT(*) FROM memory;'"],
            capture_output=True, text=True, timeout=15
        )
        count = result.stdout.strip()
        status["pgvector"] = f"up — {count} memory rows" if result.returncode == 0 else "error"
    except Exception as e:
        status["pgvector"] = f"unreachable: {str(e)}"

    # Check Ollama
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        models = r.json().get("models", [])
        status["ollama"] = f"up — {len(models)} models loaded"
    except Exception:
        status["ollama"] = "unreachable"

    # Check CiscoKid uptime
    try:
        result = subprocess.run(
            ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
             f"{SSH_USER}@{CISCOKID_IP}", "uptime -p"],
            capture_output=True, text=True, timeout=10
        )
        status["ciscokid"] = result.stdout.strip() if result.returncode == 0 else "unreachable"
    except Exception:
        status["ciscokid"] = "unreachable"

    return json.dumps(status, indent=2)


def execute_tool(tool_name: str, tool_input: dict) -> str:
    print(f"  [🔧 {tool_name}]", end=" ", flush=True)

    if tool_name == "ssh_command":
        result = ssh_run(tool_input["host"], tool_input["command"])
        print("done")
        return result

    elif tool_name == "search_memory":
        result = search_memory_tool(
            tool_input["query"],
            tool_input.get("top_k", 5)
        )
        print("done")
        return result

    elif tool_name == "get_agent_status":
        result = get_agent_status_tool()
        print("done")
        return result

    elif tool_name == "get_datetime":
        now = datetime.now()
        fmt = tool_input.get("format", "full")
        if fmt == "date":
            result = now.strftime("%Y-%m-%d")
        elif fmt == "time":
            result = now.strftime("%H:%M:%S")
        else:
            result = now.strftime("%Y-%m-%d %H:%M:%S")
        print("done")
        return result

    elif tool_name == "calculate":
        try:
            result = str(eval(tool_input.get("expression", "")))
        except Exception as e:
            result = f"Error: {str(e)}"
        print("done")
        return result

    print("unknown")
    return "Unknown tool"


# --- SUMMARIZE HISTORY ---
def summarize_history(history: list) -> list:
    print("\n[Clawdbot] Summarizing conversation history...\n")
    history_text = ""
    for msg in history:
        if isinstance(msg["content"], str):
            history_text += f"{msg['role'].upper()}: {msg['content']}\n"

    response = api_call_with_retry(
        client.messages.create,
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system="Summarize this conversation in 3-5 sentences. Preserve key technical details.",
        messages=[{"role": "user", "content": f"Summarize:\n\n{history_text}"}]
    )

    return [
        {"role": "user", "content": f"[Session summary: {response.content[0].text}]"},
        {"role": "assistant", "content": "Got it. Continuing with full context."}
    ]


# --- AGENT LOOP ---
def run_clawdbot(user_input: str, history: list) -> tuple:
    history.append({"role": "user", "content": user_input})

    if len(history) > MAX_HISTORY * 2:
        history = summarize_history(history)
        history.append({"role": "user", "content": user_input})

    max_iterations = 8
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        response = smart_create(
            client,
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            tools=tools,
            system=CLAWDBOT_SYSTEM,
            messages=history
        )

        history.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            return final_text, history

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            history.append({"role": "user", "content": tool_results})

    return "Max iterations reached.", history


# --- MAIN ---
def main():
    print("\n" + "="*60)
    print("  CLAWDBOT v0.1 — Project Ascension Personal Assistant")
    print("="*60)

    # Check connections
    print("\n[Startup] Checking connections...")
    ollama_up = is_ollama_available()
    print(f"  Ollama (TheBeast): {'✅ online' if ollama_up else '⚠️  offline'}")
    print(f"  Anthropic API:     ✅ primary")
    print(f"  SSH key:           {SSH_KEY}")
    print(f"\nType 'quit' to exit | 'clear' to reset history | 'status' for system check\n")

    history = []

    while True:
        try:
            user_input = input("You → Clawdbot: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nClawdbot shutting down. Later.")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("\nClawdbot shutting down. Later.")
            break

        if user_input.lower() == "clear":
            history = []
            print("[History cleared]\n")
            continue

        if user_input.lower() == "status":
            user_input = "Run a full system status check on all homelab services."

        print("\nClawdbot: ", end="", flush=True)
        response, history = run_clawdbot(user_input, history)
        print(f"{response}\n")


if __name__ == "__main__":
    main()
