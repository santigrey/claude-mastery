import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

MAX_TURNS = 6  # Max conversation turns before summarizing

def summarize_history(history):
    print("\n[SYSTEM: History too long — summarizing...]\n")
    
    history_text = ""
    for msg in history:
        history_text += f"{msg['role'].upper()}: {msg['content']}\n"
    
    summary = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system="You are a conversation summarizer. Summarize the key points of this conversation in 3-5 sentences. Be concise.",
        messages=[
            {
                "role": "user",
                "content": f"Summarize this conversation:\n\n{history_text}"
            }
        ]
    )
    
    summary_text = summary.content[0].text
    
    # Reset history with summary as context
    return [
        {
            "role": "user",
            "content": f"[Previous conversation summary: {summary_text}]"
        },
        {
            "role": "assistant",
            "content": "Understood. I have context from our previous conversation and will continue from there."
        }
    ]

def chat(history, user_input):
    history.append({"role": "user", "content": user_input})
    
    # Check if we need to summarize
    if len(history) > MAX_TURNS * 2:
        history = summarize_history(history)
        history.append({"role": "user", "content": user_input})
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system="You are a senior AI engineer. Be direct and technical.",
        messages=history
    )
    
    assistant_reply = response.content[0].text
    history.append({"role": "assistant", "content": assistant_reply})
    
    print(f"\n[Turns: {len(history)//2} | Input tokens: {response.usage.input_tokens}]")
    print(f"Claude: {assistant_reply}\n")
    
    return history

# Main loop
print("=== CONVERSATION MANAGER ===")
print("Type 'quit' to exit\n")

history = []

while True:
    user_input = input("You: ").strip()
    
    if user_input.lower() == "quit":
        print("Session ended.")
        break
    
    if not user_input:
        continue
    
    history = chat(history, user_input)
