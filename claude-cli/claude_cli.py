import anthropic
import json
from dotenv import load_dotenv
from datetime import datetime
from prompts.engineer import ENGINEER, ANALYST, MENTOR

load_dotenv()

client = anthropic.Anthropic()

MAX_TURNS = 8

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
    }
]

def execute_tool(tool_name, tool_input):
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
    return "Unknown tool"

def summarize_history(history):
    print("\n[Summarizing conversation history...]\n")
    history_text = ""
    for msg in history:
        if isinstance(msg["content"], str):
            history_text += f"{msg['role'].upper()}: {msg['content']}\n"
    summary = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system="Summarize this conversation in 3-5 sentences. Be concise.",
        messages=[{"role": "user", "content": f"Summarize:\n\n{history_text}"}]
    )
    return [
        {"role": "user", "content": f"[Previous summary: {summary.content[0].text}]"},
        {"role": "assistant", "content": "Understood. Continuing from context."}
    ]

def run_agent(user_input, history, system_prompt):
    history.append({"role": "user", "content": user_input})
    if len(history) > MAX_TURNS * 2:
        history = summarize_history(history)
        history.append({"role": "user", "content": user_input})
    max_iterations = 5
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            system=system_prompt,
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
                    print(f"  [Tool: {block.name}]")
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            history.append({"role": "user", "content": tool_results})
    return "Max iterations reached.", history

PERSONAS = {
    "1": ("ENGINEER", ENGINEER),
    "2": ("ANALYST", ANALYST),
    "3": ("MENTOR", MENTOR)
}

def main():
    print("\n" + "="*60)
    print("       CLAUDE CLI - Week 1 Integration Build")
    print("="*60)
    print("\nSelect persona:")
    print("  1 - Engineer")
    print("  2 - Analyst")
    print("  3 - Mentor")
    choice = input("\nChoice (1-3): ").strip()
    persona_name, system_prompt = PERSONAS.get(choice, ("ENGINEER", ENGINEER))
    print(f"\n[Persona: {persona_name}]")
    print("Type quit to exit | switch to change persona | clear to reset\n")
    history = []
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("\nSession ended.")
            break
        if user_input.lower() == "clear":
            history = []
            print("[History cleared]\n")
            continue
        if user_input.lower() == "switch":
            print("\nSelect persona:")
            print("  1 - Engineer")
            print("  2 - Analyst")
            print("  3 - Mentor")
            choice = input("Choice (1-3): ").strip()
            persona_name, system_prompt = PERSONAS.get(choice, ("ENGINEER", ENGINEER))
            history = []
            print(f"[Switched to {persona_name}]\n")
            continue
        response, history = run_agent(user_input, history, system_prompt)
        print(f"\nClaude ({persona_name}): {response}\n")

if __name__ == "__main__":
    main()
