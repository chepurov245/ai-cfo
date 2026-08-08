conversation_history = []


def add_message(role: str, content: str):
    conversation_history.append(
        {
            "role": role,
            "content": content
        }
    )

    print("\n========== MEMORY ==========")
    print(conversation_history)
    print("============================\n")


def get_history():
    print("\n========== GET HISTORY ==========")
    print(conversation_history)
    print("=================================\n")

    return conversation_history


def clear_history():
    conversation_history.clear()

    print("\n========== MEMORY CLEARED ==========\n")