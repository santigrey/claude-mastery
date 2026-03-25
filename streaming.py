import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

print("=== STREAMING RESPONSE ===")

with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system="You are a senior AI engineer. Be direct and technical.",
    messages=[
        {
            "role": "user",
            "content": "List 5 key skills an AI engineer needs in 2025. Be concise."
        }
    ]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

print("\n\n=== DONE ===")
