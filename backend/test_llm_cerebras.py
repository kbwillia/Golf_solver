import os
from llm_cerebras import call_cerebras_llm

def test_basic_llm():
    """Test basic LLM functionality without structured output"""
    print("Testing basic LLM functionality...")

    test_prompt = "You are a helpful assistant. Please respond with a short greeting and tell me what you can help with."

    try:
        response = call_cerebras_llm(
            prompt=test_prompt,
            model="llama3.1-8b",
            structured=False,
            stream=False,
            temperature=0.7
        )

        print("✅ LLM Response received successfully!")
        print(f"Response: {response}")
        return True

    except Exception as e:
        print(f"❌ Error testing LLM: {e}")
        return False

def test_streaming_llm():
    """Test streaming LLM functionality"""
    print("\nTesting streaming LLM functionality...")

    test_prompt = "You are a helpful assistant. Please give me a brief explanation of what a chatbot is."

    try:
        response = call_cerebras_llm(
            prompt=test_prompt,
            model="llama3.1-8b",
            structured=False,
            stream=True,
            temperature=0.7,
            stream_delay=0.01
        )

        print("\n✅ Streaming LLM Response received successfully!")
        print(f"Full response: {response}")
        return True

    except Exception as e:
        print(f"❌ Error testing streaming LLM: {e}")
        return False

def test_golf_chatbot_prompt():
    """Test a golf-related prompt that would be useful for your game"""
    print("\nTesting golf chatbot prompt...")

    test_prompt = """You are a helpful golf assistant. A player is playing a card game called Golf and they have these cards in their hand: [2H, 7D, KC, 9S].
    They can see one card from the discard pile: 5C.
    Should they pick up the 5C from the discard pile or draw a new card from the deck?
    Give a brief, friendly explanation of your reasoning."""

    try:
        response = call_cerebras_llm(
            prompt=test_prompt,
            model="llama3.1-8b",
            structured=False,
            stream=False,
            temperature=0.7
        )

        print("✅ Golf chatbot prompt response received successfully!")
        print(f"Response: {response}")
        return True

    except Exception as e:
        print(f"❌ Error testing golf chatbot prompt: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Cerebras LLM Integration")
    print("=" * 50)

    # Check if API key is set
    if not os.getenv("CEREBRAS_API_KEY"):
        print("⚠️  Warning: CEREBRAS_API_KEY environment variable not set!")
        print("Please create a .env file with your API key:")
        print("CEREBRAS_API_KEY=your_api_key_here")
        print("\nFor now, the tests will likely fail...")

    # Run tests
    basic_success = test_basic_llm()
    streaming_success = test_streaming_llm()
    golf_success = test_golf_chatbot_prompt()

    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Basic LLM: {'✅ PASS' if basic_success else '❌ FAIL'}")
    print(f"Streaming LLM: {'✅ PASS' if streaming_success else '❌ FAIL'}")
    print(f"Golf Chatbot: {'✅ PASS' if golf_success else '❌ FAIL'}")

    if basic_success and streaming_success and golf_success:
        print("\n🎉 All tests passed! Your LLM integration is ready for the golf game chatbot.")
    else:
        print("\n⚠️  Some tests failed. Please check your API key and try again.")


#python test_llm_cerebras.py