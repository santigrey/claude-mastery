import anthropic
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = anthropic.Anthropic()

# --- TOOLS ---
tools = [
    {
        "name": "get_datetime",
        "description": "Returns current date and time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["date", "time", "full"],
                    "description": "Format of datetime to return"
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
    },
    {
        "name": "homelab_status",
        "description": "Returns status of homelab servers. Use when asked about servers or infrastructure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "enum": ["ciscokid", "thebeast", "slimjim", "all"],
                    "description": "Which server to check"
                }
            },
            "required": ["server"]
        }
    },
    {
        "name": "search_memory",
        "description": "Searches the vector memory database for relevant information. Use when asked to recall, find, or look up past information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "store_memory",
        "description": "Stores important information into the vector memory database for future retrieval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Information to store"
                },
                "source": {
                    "type": "string",
                    "description": "Label for this memory entry"
                }
            },
            "required": ["content", "source"]
        }
    }
]

# --- TOOL EXECUTION ---
def execute_tool(tool_name, tool_input):
    print(f"\n  [TOOL CALL] {tool_name}")
    print(f"  [INPUT]     {json.dumps(tool_input)}")

    if tool_name == "get_datetime":
        now = datetime.now()
        fmt = tool_input.get("format", "full")
        if fmt == "date":
            result = now.strftime("%Y-%m-%d")
        elif fmt == "time":
            result = now.strftime("%H:%M:%S")
        else:
            result = now.strftime("%Y-%m-%d %H:%M:%S")

    elif tool_name == "calculate":
        try:
            result = str(eval(tool_input.get("expression", "")))
        except Exception as e:
            result = f"Error: {str(e)}"

    elif tool_name == "homelab_status":
        server = tool_input.get("server", "all")
        status = {
            "ciscokid": "192.168.1.10 | Ubuntu 22.04 | RAID-5 | pgvector active | MCP server running",
            "thebeast": "192.168.1.152 | Ubuntu | GPU inference | Ollama running",
            "slimjim":  "192.168.1.40 | Dell R340 | Online | Light resources | Available"
        }
        if server == "all":
            result = json.dumps(status, indent=2)
        else:
            result = status.get(server, "Server not found")

    elif tool_name == "search_memory":
        # Simulated memory search — in production this calls your pgvector MCP
        query = tool_input.get("query", "")
        result = json.dumps({
            "query": query,
            "results": [
                {"rank": 1, "content": "Project Ascension: AI operator platform on homelab", "similarity": 0.92},
                {"rank": 2, "content": "CiscoKid control plane with pgvector and Agent OS", "similarity": 0.88},
                {"rank": 3, "content": "TheBeast GPU node running Ollama inference", "similarity": 0.81}
            ]
        }, indent=2)

    elif tool_name == "store_memory":
        content = tool_input.get("content", "")
        source = tool_input.get("source", "react_agent")
        result = json.dumps({
            "status": "stored",
            "source": source,
            "content_preview": content[:100]
        })

    else:
        result = f"Unknown tool: {tool_name}"

    print(f"  [RESULT]    {result[:200]}")
    return result


# --- ReAct AGENT LOOP ---
SYSTEM_PROMPT = """You are an AI agent with access to tools. 

Your reasoning process:
1. THINK about what the user needs
2. DECIDE which tool(s) to use
3. ACT by calling the tool
4. OBSERVE the result
5. REPEAT if needed
6. ANSWER when you have enough information

Be explicit in your reasoning. Use multiple tools if needed.
Always complete the full task before stopping."""

def run_react_agent(goal):
    print(f"\n{'='*60}")
    print(f"GOAL: {goal}")
    print(f"{'='*60}")

    messages = [{"role": "user", "content": goal}]
    iteration = 0
    max_iterations = 10

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            tools=tools,
            system=SYSTEM_PROMPT,
            messages=messages
        )

        print(f"Stop reason: {response.stop_reason}")

        # Show Claude's reasoning if it includes text
        for block in response.content:
            if hasattr(block, "text") and block.text:
                print(f"\n[REASONING]\n{block.text}")

        messages.append({"role": "assistant", "content": response.content})

        # Done
        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            print(f"\n{'='*60}")
            print(f"FINAL ANSWER:\n{final_text}")
            print(f"{'='*60}")
            print(f"Completed in {iteration} iteration(s)")
            break

        # Tool use
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
            messages.append({"role": "user", "content": tool_results})

    if iteration >= max_iterations:
        print("\n[MAX ITERATIONS REACHED]")


# --- TEST GOALS ---
run_react_agent(
    "Give me a full status report: check all homelab servers, "
    "get the current date and time, and search memory for anything "
    "related to Project Ascension. Summarize everything into a "
    "structured briefing."
)
