import anthropic
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = anthropic.Anthropic()

# Define the tool schema — this is what Claude sees
tools = [
    {
        "name": "get_system_info",
        "description": "Returns current system information including date, time, and a status report. Use this when the user asks about current time, date, or system status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "info_type": {
                    "type": "string",
                    "enum": ["datetime", "status", "all"],
                    "description": "Type of system info to retrieve"
                }
            },
            "required": ["info_type"]
        }
    }
]

# The actual tool execution — this runs on YOUR machine
def execute_tool(tool_name, tool_input):
    if tool_name == "get_system_info":
        info_type = tool_input.get("info_type", "all")
        
        now = datetime.now()
        
        if info_type == "datetime":
            return f"Current datetime: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        elif info_type == "status":
            return "System status: All systems operational. Claude Mastery project active."
        else:
            return f"Datetime: {now.strftime('%Y-%m-%d %H:%M:%S')} | Status: All systems operational"
    
    return "Tool not found"

def chat_with_tools(user_message):
    print(f"\nUser: {user_message}")
    print("="*50)
    
    # First API call — Claude decides whether to use a tool
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=tools,
        system="You are a helpful AI assistant with access to system tools. Use them when relevant.",
        messages=[
            {"role": "user", "content": user_message}
        ]
    )
    
    print(f"Stop reason: {response.stop_reason}")
    
    # If Claude wants to use a tool
    if response.stop_reason == "tool_use":
        tool_block = next(b for b in response.content if b.type == "tool_use")
        
        print(f"\n[Claude is calling tool: {tool_block.name}]")
        print(f"[Tool input: {tool_block.input}]")
        
        # Execute the tool
        tool_result = execute_tool(tool_block.name, tool_block.input)
        print(f"[Tool result: {tool_result}]")
        
        # Second API call — send tool result back to Claude
        final_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            system="You are a helpful AI assistant with access to system tools. Use them when relevant.",
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": tool_result
                        }
                    ]
                }
            ]
        )
        
        print(f"\nClaude: {final_response.content[0].text}")
    
    else:
        # Claude answered directly without tool
        print(f"\nClaude: {response.content[0].text}")

# Test it
chat_with_tools("What time is it right now?")
chat_with_tools("What is the capital of France?")
