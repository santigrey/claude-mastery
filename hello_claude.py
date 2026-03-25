import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system="You are a senior AI engineer. Be direct and technical.",
    messages=[
        {
            "role": "user",
            "content": "In 3 sentences, tell me what the Anthropic Messages API is and why it matters for AI engineering."
        }
    ]
)

print("=== RESPONSE ===")
print(message.content[0].text)

print("\n=== METADATA ===")
print(f"Model: {message.model}")
print(f"Input tokens: {message.usage.input_tokens}")
print(f"Output tokens: {message.usage.output_tokens}")
print(f"Stop reason: {message.stop_reason}")
