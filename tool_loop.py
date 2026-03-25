import anthropic
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = anthropic.Anthropic()

tools = [
    {
        "name": "get_datetime",
        "description": "Returns the current date and time. Use when the user asks about time or date.",
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
        "description": "Performs mathematical calculations. Use when the user asks for any math operation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate e.g. '2 + 2' or '150 * 0.20'"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_homelab_status",
        "description": "Returns status of homelab servers. Use when user asks about servers, homelab, or infrastructure.",
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
    }
]

def execute_tool(tool_name, tool_input):
    print(f"  -> Executing: {tool_name}({tool_input})")

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
        expression = tool_input.get("expression", "")
        try:
            result = eval(expression)
            return f"Result: {result}"
        except Exception as e:
            return f"Calculation error: {str(e)}"

    elif tool_name == "get_homelab_status":
        server = tool_input.get("server", "all")
        status = {
            "ciscokid": "192.168.1.10 | Ubuntu 22.04 | RAID-5 | pgvector active | Netdata running",
            "thebeast": "192.168.1.152 | Ubuntu | GPU inference node | Standby",
            "slimjim": "192.168.1.40 | Dell R340 | Online | Light resources | Available"
        }
        if server == "all":
            return json.dumps(status, indent=2)
        return status.get(server, "Server not found")

    return f"Unknown tool: {tool_name}"

def run_agent(user_message):
    print(f"\n{'='*60}")
    print(f"USER: {user_message}")
    print(f"{'='*60}")

    messages = [{"role": "user", "content": user_message}]
    iteration = 0
    max_iterations = 10

    while iteration < max_iterations:
        iteration += 1
        print(f"\n[Iteration {iteration}]")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            system="You are an AI assistant with access to tools. Use multiple tools if needed to fully answer the question.",
            messages=messages
        )

        print(f"Stop reason: {response.stop_reason}")

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            print(f"\nFINAL ANSWER: {final_text}")
            break

        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    print(f"\n[Claude calling: {block.name}]")
                    result = execute_tool(block.name, block.input)
                    print(f"  -> Result: {result}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

    if iteration >= max_iterations:
        print("\n[MAX ITERATIONS REACHED — stopping]")

run_agent("What time is it and what is 15% of 847?")
run_agent("Give me a status report on all my homelab servers and tell me today's date.")
