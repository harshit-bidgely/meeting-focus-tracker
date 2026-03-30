#!/usr/bin/env python3
"""
Simple Claude CLI interface using the Anthropic SDK
"""

import sys
from anthropic import Anthropic

def main():
    client = Anthropic()
    
    print("=" * 60)
    print("Claude CLI - Interactive Chat Interface")
    print("=" * 60)
    print("\nType 'exit' or 'quit' to end the conversation.")
    print("Type 'clear' to clear conversation history.\n")
    
    conversation_history = []
    
    try:
        while True:
            # Get user input
            user_input = input("You: ").strip()
            
            # Handle special commands
            if user_input.lower() in ['exit', 'quit']:
                print("\nGoodbye!")
                break
            
            if user_input.lower() == 'clear':
                conversation_history = []
                print("[Conversation history cleared]\n")
                continue
            
            if not user_input:
                continue
            
            # Add user message to history
            conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Get response from Claude
            print("\nClaude: ", end="", flush=True)
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=conversation_history
            )
            
            assistant_message = response.content[0].text
            print(assistant_message)
            print()
            
            # Add assistant response to history
            conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
    except KeyboardInterrupt:
        print("\n\nConversation interrupted.")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
