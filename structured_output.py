import anthropic
import json
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system="""You are a data extraction assistant. 
You ALWAYS respond with valid JSON only. 
No preamble. No explanation. No markdown. Just raw JSON.""",
    messages=[
        {
            "role": "user",
            "content": """Extract the following info as JSON with these exact keys:
{
  "name": string,
  "role": string,
  "skills": list of strings,
  "years_experience": integer
}

Input: Sloan is a senior AI engineer with 5 years experience. 
He specializes in LLMs, vector databases, RAG pipelines, and Docker."""
        }
    ]
)

raw = message.content[0].text
print("=== RAW RESPONSE ===")
print(raw)

parsed = json.loads(raw)
print("\n=== PARSED OBJECT ===")
print(f"Name: {parsed['name']}")
print(f"Role: {parsed['role']}")
print(f"Skills: {', '.join(parsed['skills'])}")
print(f"Experience: {parsed['years_experience']} years")
