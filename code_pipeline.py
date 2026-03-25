"""
code_pipeline.py — Self-testing code generation pipeline.

Workflow:
  1. Claude generates Python code for a given task
  2. Code is written to disk and executed in a subprocess
  3. Output is captured and returned to Claude
  4. Claude evaluates the output and iterates if needed
  5. Pipeline completes when code passes or max iterations reached

This is the pattern used in production AI coding assistants.
"""

import anthropic
import subprocess
import tempfile
import os
import json
from dotenv import load_dotenv
from retry import api_call_with_retry

load_dotenv()

client = anthropic.Anthropic()

# --- PROMPTS ---
CODE_GENERATOR_PROMPT = """You are an expert Python engineer.

When given a coding task:
1. Write clean, working Python code
2. Include only the code — no explanation, no markdown fences
3. The code must be self-contained and executable
4. Print the final result clearly
5. Handle errors gracefully

Return ONLY the raw Python code. Nothing else."""

CODE_EVALUATOR_PROMPT = """You are a senior code reviewer and QA engineer.

You will be given:
- A coding task
- The code that was written
- The execution output

Your job:
1. Determine if the code correctly solved the task
2. If YES: respond with exactly: PASS
3. If NO: respond with exactly: FAIL - <brief reason and fix needed>

Be strict. Only pass if the output clearly solves the task."""


# --- CODE EXECUTOR ---
def execute_code(code: str, timeout: int = 15) -> dict:
    """Write code to a temp file and execute it safely."""
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.py',
        delete=False,
        dir='/tmp'
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ['python3', tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout}s",
            "returncode": -1
        }
    finally:
        os.unlink(tmp_path)


# --- CODE GENERATOR ---
def generate_code(task: str, previous_code: str = None, error: str = None) -> str:
    """Ask Claude to generate or fix code for a task."""
    if previous_code and error:
        user_message = f"""Task: {task}

Previous code that failed:
{previous_code}

Error or issue:
{error}

Fix the code and return only the corrected Python code."""
    else:
        user_message = f"Task: {task}"

    response = api_call_with_retry(
        client.messages.create,
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=CODE_GENERATOR_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    code = response.content[0].text.strip()

    # Strip markdown if Claude adds it anyway
    if code.startswith("```"):
        lines = code.split('\n')
        code = '\n'.join(lines[1:-1])

    return code


# --- CODE EVALUATOR ---
def evaluate_output(task: str, code: str, execution_result: dict) -> tuple:
    """Ask Claude to evaluate whether the code solved the task."""
    if not execution_result["success"]:
        return False, f"Execution failed: {execution_result['stderr']}"

    eval_message = f"""Task: {task}

Code written:
{code}

Execution output:
{execution_result['stdout']}

Errors (if any):
{execution_result['stderr']}"""

    response = api_call_with_retry(
        client.messages.create,
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        system=CODE_EVALUATOR_PROMPT,
        messages=[{"role": "user", "content": eval_message}]
    )

    verdict = response.content[0].text.strip()
    passed = verdict.upper().startswith("PASS")
    return passed, verdict


# --- MAIN PIPELINE ---
def run_code_pipeline(task: str, max_iterations: int = 3):
    print(f"\n{'='*60}")
    print(f"TASK: {task}")
    print(f"{'='*60}")

    code = None
    error = None

    for iteration in range(1, max_iterations + 1):
        print(f"\n--- Iteration {iteration} ---")

        # Step 1: Generate code
        print("[1] Generating code...")
        code = generate_code(task, code, error)
        print(f"[CODE]\n{code}\n")

        # Step 2: Execute code
        print("[2] Executing code...")
        result = execute_code(code)
        print(f"[OUTPUT] {result['stdout']}")
        if result['stderr']:
            print(f"[STDERR] {result['stderr']}")

        # Step 3: Evaluate output
        print("[3] Evaluating output...")
        passed, verdict = evaluate_output(task, code, result)
        print(f"[VERDICT] {verdict}")

        if passed:
            print(f"\n✅ PIPELINE COMPLETE — passed on iteration {iteration}")
            break
        else:
            error = verdict
            print(f"\n⚠️  ITERATION FAILED — retrying with fix...")

    else:
        print(f"\n❌ PIPELINE FAILED — max iterations ({max_iterations}) reached")

    return code, result


# --- TEST TASKS ---
print("\n" + "="*60)
print("CODE GENERATION PIPELINE — Day 18")
print("="*60)

# Task 1 — Simple
run_code_pipeline(
    "Write a Python function that takes a list of numbers and returns "
    "the mean, median, and standard deviation. Test it with [10, 20, 30, 40, 50]."
)

# Task 2 — File I/O
run_code_pipeline(
    "Write Python code that creates a file called 'test_output.txt', "
    "writes the first 10 Fibonacci numbers to it one per line, "
    "then reads it back and prints the contents."
)

# Task 3 — Error recovery test
run_code_pipeline(
    "Write Python code that fetches the current UTC time using only "
    "the standard library (no requests, no external packages) and "
    "prints it in ISO 8601 format."
)
