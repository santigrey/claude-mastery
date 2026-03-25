"""
evals.py — Evaluation harness for Claude-powered agents.

Real AI engineers don't just build agents — they measure them.
This harness runs test cases against your agent and scores outputs.

Eval types:
  - exact_match    : output must contain expected string
  - contains       : output must contain all expected keywords
  - json_valid     : output must be parseable JSON
  - tool_called    : specific tool must have been invoked
  - llm_judge      : Claude evaluates quality of the response

This pattern is used at Anthropic, OpenAI, and every serious AI team.
"""

import anthropic
import json
import time
from dotenv import load_dotenv
from retry import api_call_with_retry
from datetime import datetime

load_dotenv()

client = anthropic.Anthropic()

# --- TOOLS (same as react_agent) ---
tools = [
    {
        "name": "get_datetime",
        "description": "Returns current date and time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["date", "time", "full"]}
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
                "expression": {"type": "string"}
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
                "server": {"type": "string", "enum": ["ciscokid", "thebeast", "slimjim", "all"]}
            },
            "required": ["server"]
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
            return str(eval(tool_input.get("expression", "")))
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
    return "Unknown tool"


# --- AGENT RUNNER ---
def run_agent(user_message: str) -> tuple:
    """Run agent and return (final_text, tools_called)."""
    messages = [{"role": "user", "content": user_message}]
    tools_called = []
    max_iterations = 8
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        response = api_call_with_retry(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            system="You are a helpful AI assistant with access to tools. Use them when needed.",
            messages=messages
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            return final_text, tools_called

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tools_called.append(block.name)
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})

    return "Max iterations reached", tools_called


# --- EVAL TYPES ---
def eval_contains(output: str, expected_keywords: list) -> tuple:
    """Check if output contains all expected keywords."""
    missing = [kw for kw in expected_keywords if kw.lower() not in output.lower()]
    passed = len(missing) == 0
    reason = "All keywords found" if passed else f"Missing: {missing}"
    return passed, reason

def eval_exact_match(output: str, expected: str) -> tuple:
    passed = expected.lower() in output.lower()
    reason = "Match found" if passed else f"Expected '{expected}' not in output"
    return passed, reason

def eval_json_valid(output: str) -> tuple:
    try:
        json.loads(output)
        return True, "Valid JSON"
    except Exception as e:
        return False, f"Invalid JSON: {str(e)}"

def eval_tool_called(tools_called: list, expected_tool: str) -> tuple:
    passed = expected_tool in tools_called
    reason = f"Tool '{expected_tool}' was called" if passed else f"Tool '{expected_tool}' was NOT called. Called: {tools_called}"
    return passed, reason

def eval_llm_judge(question: str, output: str, criteria: str) -> tuple:
    """Use Claude to judge response quality."""
    response = api_call_with_retry(
        client.messages.create,
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        system="You are a strict evaluator. Respond only with PASS or FAIL - <reason>.",
        messages=[{
            "role": "user",
            "content": f"Question: {question}\nResponse: {output}\nCriteria: {criteria}\nDid the response meet the criteria?"
        }]
    )
    verdict = response.content[0].text.strip()
    passed = verdict.upper().startswith("PASS")
    return passed, verdict


# --- TEST SUITE ---
TEST_CASES = [
    {
        "id": "TC001",
        "description": "Basic math calculation",
        "input": "What is 25 multiplied by 48?",
        "eval_type": "contains",
        "expected": ["1,200"],
        "expected_tool": "calculate"
    },
    {
        "id": "TC002",
        "description": "DateTime retrieval",
        "input": "What is today's date?",
        "eval_type": "tool_called",
        "expected": [],
        "expected_tool": "get_datetime"
    },
    {
        "id": "TC003",
        "description": "Homelab server status",
        "input": "What is the status of ciscokid?",
        "eval_type": "contains",
        "expected": ["192.168.1.10", "pgvector"],
        "expected_tool": "homelab_status"
    },
    {
        "id": "TC004",
        "description": "No tool needed — general knowledge",
        "input": "What is the capital of Japan?",
        "eval_type": "contains",
        "expected": ["Tokyo"],
        "expected_tool": None
    },
    {
        "id": "TC005",
        "description": "Multi-tool — date and math",
        "input": "What is today's date and what is 15% of 2500?",
        "eval_type": "contains",
        "expected": ["375", "2026"],
        "expected_tool": "calculate"
    },
    {
        "id": "TC006",
        "description": "All homelab servers",
        "input": "Give me a status report on all homelab servers",
        "eval_type": "contains",
        "expected": ["ciscokid", "thebeast", "slimjim"],
        "expected_tool": "homelab_status"
    },
    {
        "id": "TC007",
        "description": "LLM judge — quality of explanation",
        "input": "Explain what a vector database is in simple terms",
        "eval_type": "llm_judge",
        "expected": [],
        "expected_tool": None,
        "judge_criteria": "The response must explain vector databases clearly, mention similarity search, and be understandable to a non-technical person"
    },
    {
        "id": "TC008",
        "description": "Complex calculation",
        "input": "If I have 3 servers each using 847 watts, what is my total power draw in kilowatts?",
        "eval_type": "contains",
        "expected": ["2.541"],
        "expected_tool": "calculate"
    },
    {
        "id": "TC009",
        "description": "TheBeast specific status",
        "input": "Is TheBeast online?",
        "eval_type": "contains",
        "expected": ["Ollama", "192.168.1.152"],
        "expected_tool": "homelab_status"
    },
    {
        "id": "TC010",
        "description": "No hallucination check",
        "input": "What is the status of a server called shadowbox?",
        "eval_type": "llm_judge",
        "expected": [],
        "expected_tool": None,
        "judge_criteria": "The response must NOT make up server details. It should indicate the server is unknown or not found."
    }
]


# --- HARNESS RUNNER ---
def run_evals():
    print("\n" + "="*60)
    print("EVAL HARNESS — Project Ascension Agent")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test cases: {len(TEST_CASES)}")
    print("="*60)

    results = []
    passed = 0
    failed = 0

    for tc in TEST_CASES:
        print(f"\n[{tc['id']}] {tc['description']}")
        print(f"  Input: {tc['input']}")

        start = time.time()
        output, tools_called = run_agent(tc["input"])
        elapsed = round(time.time() - start, 2)

        # Run appropriate eval
        eval_type = tc["eval_type"]

        if eval_type == "contains":
            success, reason = eval_contains(output, tc["expected"])
            # Also check tool was called if specified
            if success and tc.get("expected_tool"):
                tool_ok, tool_reason = eval_tool_called(tools_called, tc["expected_tool"])
                if not tool_ok:
                    success = False
                    reason = tool_reason

        elif eval_type == "tool_called":
            success, reason = eval_tool_called(tools_called, tc["expected_tool"])

        elif eval_type == "json_valid":
            success, reason = eval_json_valid(output)

        elif eval_type == "llm_judge":
            success, reason = eval_llm_judge(
                tc["input"], output, tc.get("judge_criteria", "Response is helpful and accurate")
            )

        else:
            success, reason = False, f"Unknown eval type: {eval_type}"

        status = "✅ PASS" if success else "❌ FAIL"
        if success:
            passed += 1
        else:
            failed += 1

        print(f"  Status: {status}")
        print(f"  Reason: {reason}")
        print(f"  Tools:  {tools_called if tools_called else 'none'}")
        print(f"  Time:   {elapsed}s")

        results.append({
            "id": tc["id"],
            "description": tc["description"],
            "passed": success,
            "reason": reason,
            "tools_called": tools_called,
            "elapsed": elapsed
        })

        time.sleep(1)  # Rate limit buffer

    # --- SUMMARY ---
    score = round((passed / len(TEST_CASES)) * 100, 1)
    print(f"\n{'='*60}")
    print(f"EVAL RESULTS")
    print(f"{'='*60}")
    print(f"Passed:  {passed}/{len(TEST_CASES)}")
    print(f"Failed:  {failed}/{len(TEST_CASES)}")
    print(f"Score:   {score}%")
    print(f"{'='*60}")

    # Write results to disk
    with open("eval_results.json", "w") as f:
        json.dump({
            "run_time": datetime.now().isoformat(),
            "score": score,
            "passed": passed,
            "failed": failed,
            "total": len(TEST_CASES),
            "results": results
        }, f, indent=2)

    print(f"\nResults saved to eval_results.json")
    return score


if __name__ == "__main__":
    run_evals()
