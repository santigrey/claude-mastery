import anthropic
from retry import api_call_with_retry
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
        "description": "Returns status of homelab servers.",
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
        "description": "Searches vector memory for relevant information.",
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
        "name": "write_report",
        "description": "Writes a final report to disk. Use this as the last step when all information is gathered.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Output filename e.g. report.md"
                },
                "content": {
                    "type": "string",
                    "description": "Full report content in markdown"
                }
            },
            "required": ["filename", "content"]
        }
    }
]

# --- TOOL EXECUTION ---
def execute_tool(tool_name, tool_input):
    print(f"\n  [TOOL] {tool_name} | input: {json.dumps(tool_input)[:100]}")

    if tool_name == "get_datetime":
        now = datetime.now()
        fmt = tool_input.get("format", "full")
        if fmt == "date":
            return now.strftime("%Y-%m-%d")
        elif fmt == "time":
            return now.strftime("%H:%M:%S")
        else:
            return now.strftime("%Y-%m-%d %H:%M:%S")

    elif tool_name == "calculate":
        try:
            result = eval(tool_input.get("expression", ""))
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {str(e)}"

    elif tool_name == "homelab_status":
        server = tool_input.get("server", "all")
        status = {
            "ciscokid": "192.168.1.10 | Ubuntu 22.04 | RAID-5 | pgvector active | MCP server running",
            "thebeast": "192.168.1.152 | Ubuntu | GPU inference | Ollama running",
            "slimjim":  "192.168.1.40 | Dell R340 | Online | Light resources | Available"
        }
        if server == "all":
            return json.dumps(status, indent=2)
        return status.get(server, "Server not found")

    elif tool_name == "search_memory":
        query = tool_input.get("query", "")
        return json.dumps({
            "query": query,
            "results": [
                {"rank": 1, "content": "Project Ascension: AI operator platform on homelab", "similarity": 0.92},
                {"rank": 2, "content": "CiscoKid control plane with pgvector and Agent OS indexed 203 files", "similarity": 0.88},
                {"rank": 3, "content": "TheBeast GPU node running Ollama with mxbai-embed-large model", "similarity": 0.81}
            ]
        }, indent=2)

    elif tool_name == "write_report":
        filename = tool_input.get("filename", "report.md")
        content = tool_input.get("content", "")
        with open(filename, "w") as f:
            f.write(content)
        return f"Report written to {filename} ({len(content)} characters)"

    return f"Unknown tool: {tool_name}"


# --- STATE MACHINE ---
class TaskState:
    PLANNING    = "PLANNING"
    EXECUTING   = "EXECUTING"
    COMPLETE    = "COMPLETE"
    FAILED      = "FAILED"


# --- PLANNING PROMPT ---
PLANNER_PROMPT = """You are a task planning agent. 

When given a goal, you MUST:
1. Break it into 3-5 concrete sequential subtasks
2. Return ONLY a JSON object in this exact format:

{
  "goal": "the original goal",
  "subtasks": [
    {"id": 1, "description": "what to do", "tool": "tool_name or null"},
    {"id": 2, "description": "what to do", "tool": "tool_name or null"},
    {"id": 3, "description": "what to do", "tool": "tool_name or null"}
  ]
}

Available tools: get_datetime, calculate, homelab_status, search_memory, write_report
Return ONLY the JSON. No preamble. No explanation."""


# --- EXECUTOR PROMPT ---
EXECUTOR_PROMPT = """You are a task execution agent. 

You will be given a specific subtask to complete.
Use the available tools to complete it.
Be direct and efficient.
Return a clear result when done."""


def plan_tasks(goal):
    print(f"\n[PLANNER] Breaking down goal into subtasks...")
    response = api_call_with_retry(client.messages.create,
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=PLANNER_PROMPT,
        messages=[{"role": "user", "content": f"Goal: {goal}"}]
    )
    raw = response.content[0].text.strip()
    # Strip markdown if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def execute_subtask(subtask, results_so_far):
    print(f"\n[EXECUTOR] Subtask {subtask['id']}: {subtask['description']}")

    context = f"Previous results:\n{json.dumps(results_so_far, indent=2)}\n\n" if results_so_far else ""
    user_message = f"{context}Complete this subtask: {subtask['description']}"

    messages = [{"role": "user", "content": user_message}]
    max_iterations = 5
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        response = api_call_with_retry(client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            system=EXECUTOR_PROMPT,
            messages=messages
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            return final_text

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

    return "Max iterations reached for subtask."


# --- MAIN TASK AGENT ---
def run_task_agent(goal):
    print(f"\n{'='*60}")
    print(f"GOAL: {goal}")
    print(f"{'='*60}")

    state = TaskState.PLANNING

    # Phase 1 — Plan
    plan = plan_tasks(goal)
    print(f"\n[PLAN] {len(plan['subtasks'])} subtasks identified:")
    for t in plan["subtasks"]:
        print(f"  {t['id']}. {t['description']}")

    state = TaskState.EXECUTING
    results = {}

    # Phase 2 — Execute each subtask sequentially
    for subtask in plan["subtasks"]:
        result = execute_subtask(subtask, results)
        results[f"subtask_{subtask['id']}"] = {
            "description": subtask["description"],
            "result": result
        }
        print(f"\n  [DONE] Subtask {subtask['id']} complete")

    state = TaskState.COMPLETE

    print(f"\n{'='*60}")
    print(f"ALL SUBTASKS COMPLETE")
    print(f"{'='*60}")
    for key, val in results.items():
        print(f"\n{key}: {val['description']}")
        print(f"  → {val['result'][:200]}")

    return results


# --- RUN ---
run_task_agent(
    "Audit my homelab: check all server statuses, search memory for "
    "Project Ascension details, get the current timestamp, calculate "
    "how many days are left in 2026, then write a full markdown report "
    "to 'homelab_audit.md' with all findings."
)
