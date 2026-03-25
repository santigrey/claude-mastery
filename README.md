# Claude Mastery — AI Engineering Curriculum

A 3-week intensive curriculum demonstrating production-grade AI engineering
using the Anthropic API. Built in ~3 hours of focused execution.

## Stack
- **Primary inference:** Anthropic Claude Sonnet 4
- **Local fallback:** Ollama llama3.1:8b on self-hosted GPU node
- **Memory:** pgvector on self-hosted control plane
- **Infrastructure:** 3-server homelab (control, inference, edge)
- **Protocol:** MCP (Model Context Protocol)

## Projects

### Clawdbot v0.1
Personal AI assistant with live homelab integration.
- SSH into real servers (CiscoKid, TheBeast, SlimJim)
- Semantic search against pgvector memory (592 rows)
- Live GPU telemetry from Tesla T4
- Anthropic primary + Ollama fallback
- Conversation memory with summarization

### Task Planning Agent
Autonomous agent that breaks goals into subtasks and executes sequentially.
- State machine: PLANNING → EXECUTING → COMPLETE
- Context carry-forward between subtasks
- Writes markdown reports to disk

### ReAct Agent
Reason + Act loop with parallel tool calling.
- Parallel tool execution in single iteration
- Visible reasoning at each step
- Max iterations guard

### Self-Testing Code Pipeline
Claude writes code, executes it, evaluates output, iterates.
- Subprocess execution in temp files
- LLM-as-judge evaluation
- Auto-retry with error feedback

### Evals Harness
10-test evaluation suite scoring agent reliability.
- contains, exact_match, tool_called, llm_judge eval types
- Hallucination detection
- 100% baseline pass rate
- Results saved to JSON

### Claude CLI
Multi-persona conversational assistant.
- Engineer, Analyst, Mentor personas
- Conversation memory with summarization fallback
- Tool use: datetime, calculator

## Week 1 — API Fluency
| Day | Build | Concept |
|-----|-------|---------|
| 1 | hello_claude.py | Raw API call, metadata |
| 2 | streaming.py, structured_output.py | Streaming, JSON outputs |
| 3 | prompts/ library | System prompt architecture |
| 4 | conversation_manager.py | Memory management |
| 5 | tool_use_basic.py | Single tool use |
| 6 | tool_loop.py | Multi-tool agentic loop |
| 7 | claude-cli/ | Integration build |

## Week 2-3 — Agents + Production
| Day | Build | Concept |
|-----|-------|---------|
| 15 | react_agent.py | ReAct pattern |
| 16 | task_agent.py | Task planning + state machine |
| 17 | retry.py, ollama_client.py | Production hardening |
| 18 | code_pipeline.py | Self-testing code generation |
| 19 | evals.py | Evaluation harness |
| 20 | clawdbot/ | Live homelab AI assistant |

## Architecture
```
JesAir (dev) ──── Anthropic API (primary)
      │
      ├──── CiscoKid (192.168.1.10)
      │     ├── pgvector memory (592 rows)
      │     ├── MCP server
      │     └── Agent OS (203 files indexed)
      │
      ├──── TheBeast (192.168.1.152)
      │     ├── Ollama (fallback inference)
      │     ├── Tesla T4 GPU
      │     └── mxbai-embed-large embeddings
      │
      └──── SlimJim (192.168.1.40)
            └── Dell R340 (available)
```

## Key Concepts Demonstrated
- Anthropic Messages API — raw SDK fluency
- Streaming + structured JSON outputs
- System prompt architecture + persona design
- Conversation memory management + summarization
- Tool use — single, multi-tool, parallel
- MCP server integration
- ReAct agent pattern
- Task planning with state machines
- Production error handling + retry logic
- Hybrid inference (cloud + local fallback)
- Evaluation harnesses + LLM-as-judge
- Self-hosted AI infrastructure

## Author
Sloan — AI Platform Engineer
github.com/santigrey
