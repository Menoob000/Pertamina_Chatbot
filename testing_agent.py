import sys
from langchain_core.messages import HumanMessage, AIMessage

try:
    from agent import app
except ImportError:
    print("Error: Could not import 'app' from 'main.py'. Ensure your main agent script is in the same directory.")
    sys.exit(1)


def run_agent_test():
    print("=" * 60)
    print("🤖 Agent Testing Environment")
    print("Type your prompt and press Enter.")
    print("Type 'q' or 'quit' at any prompt to exit.")
    print("=" * 60 + "\n")

    # Thread configuration to maintain chat memory across iterations
    config = {"configurable": {"thread_id": "test_session_1"}}

    while True:
        try:
            user_input = input("\nUser > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting test session.")
            break

        # Check for quit command
        if user_input.lower() in ["q", "quit"]:
            print("Exiting test session. Goodbye!")
            break

        if not user_input:
            continue

        print("\nThinking...")
        
        # Invoke the agent graph with the user message
        input_state = {"messages": [HumanMessage(content=user_input)]}
        
        # Stream events through the state graph
        for event in app.stream(input_state, config=config, stream_mode="values"):
            latest_message = event["messages"][-1]

        # Display tool execution logs or final response
        if isinstance(latest_message, AIMessage) and latest_message.content:
            print(f"\nAssistant > {latest_message.content}")


if __name__ == "__main__":
    run_agent_test()