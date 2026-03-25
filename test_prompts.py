import anthropic
from dotenv import load_dotenv
from prompts.engineer import ENGINEER, ANALYST, MENTOR

load_dotenv()

client = anthropic.Anthropic()

def ask(persona_name, system_prompt, question):
    print(f"\n{'='*50}")
    print(f"PERSONA: {persona_name}")
    print(f"QUESTION: {question}")
    print(f"{'='*50}")
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system=system_prompt,
        messages=[
            {"role": "user", "content": question}
        ]
    )
    
    print(message.content[0].text)

question = "What is the single most important skill I should build right now as an AI engineer?"

ask("ENGINEER", ENGINEER, question)
ask("ANALYST", ANALYST, question)
ask("MENTOR", MENTOR, question)
