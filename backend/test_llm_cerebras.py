import os
import requests
from llm_cerebras import call_cerebras_llm

def check_rate_limit_status():
    """Check rate limit status without using tokens - just make a minimal request to get headers"""
    print("Checking rate limit status...")

    try:
        api_key = os.getenv("CEREBRAS_API_KEY")
        if not api_key:
            print("❌ CEREBRAS_API_KEY not found")
            return False

        url = "https://api.cerebras.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Make a minimal request that should use very few tokens
        payload = {
            "model": "llama3.1-8b",
            "messages": [
                {"role": "user", "content": "Hi"}
            ],
            "temperature": 0.7,
            "stream": False,
            "max_tokens": 1  # Minimize token usage
        }

        response = requests.post(url, json=payload, headers=headers)

        # Extract and display rate limit information regardless of success/failure
        print("\n📊 Current API Rate Limit Status:")
        print("=" * 50)

        # Most important info first - when you can use API again
        daily_reset = response.headers.get('x-ratelimit-reset-requests-day')
        if daily_reset:
            total_seconds = int(float(daily_reset))
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            print(f"🕒 DAILY QUOTA RESETS IN: {hours}h {minutes}m {seconds}s")

        minute_reset = response.headers.get('x-ratelimit-reset-tokens-minute')
        if minute_reset:
            reset_seconds = int(float(minute_reset))
            print(f"🕒 MINUTE QUOTA RESETS IN: {reset_seconds} seconds")

        print("-" * 50)

        # Current remaining quotas
        tokens_remaining = response.headers.get('x-ratelimit-remaining-tokens-minute')
        if tokens_remaining:
            print(f"Tokens remaining (this minute): {tokens_remaining}")

        daily_remaining = response.headers.get('x-ratelimit-remaining-requests-day')
        if daily_remaining:
            print(f"Requests remaining (today): {daily_remaining}")

        # Total limits for reference
        daily_limit = response.headers.get('x-ratelimit-limit-requests-day')
        if daily_limit:
            print(f"Daily request limit: {daily_limit}")

        minute_limit = response.headers.get('x-ratelimit-limit-tokens-minute')
        if minute_limit:
            print(f"Per-minute token limit: {minute_limit}")

        print("=" * 50)

        # Debug: Show all rate limit related headers for analysis
        print("\n🔍 All rate limit headers found:")
        print("-" * 25)
        for header_name, header_value in response.headers.items():
            if 'ratelimit' in header_name.lower():
                print(f"{header_name}: {header_value}")
        print("-" * 25)

        if response.status_code == 200:
            print("✅ API is available - no rate limits hit")

            # Extract token usage information from response body
            try:
                response_data = response.json()
                print(f"\n🔍 Full API Response Structure:")
                print(f"Response keys: {list(response_data.keys())}")

                if 'usage' in response_data:
                    usage = response_data['usage']
                    print(f"\n🔢 Detailed Token Usage:")
                    print("=" * 40)

                    # Standard OpenAI-compatible fields
                    prompt_tokens = usage.get('prompt_tokens', 0)
                    completion_tokens = usage.get('completion_tokens', 0)
                    total_tokens = usage.get('total_tokens', 0)

                    print(f"📥 Input tokens (prompt): {prompt_tokens}")
                    print(f"📤 Output tokens (completion): {completion_tokens}")
                    print(f"📊 Total tokens used: {total_tokens}")

                    # Check for any additional usage fields specific to Cerebras
                    print(f"\n🔍 All usage fields available:")
                    for key, value in usage.items():
                        print(f"  {key}: {value}")

                    print("=" * 40)
                else:
                    print("\n⚠️ No 'usage' field found in response")
                    print("Available response fields:", list(response_data.keys()))

            except Exception as e:
                print(f"⚠️ Could not parse token usage: {e}")
                print(f"Raw response: {response.text[:200]}...")

            return True
        elif response.status_code == 429:
            error_data = response.json()
            error_msg = error_data.get('message', 'Rate limit exceeded')
            print(f"⚠️ API Rate Limited: {error_msg}")

            if 'token' in error_msg.lower():
                print("💡 You've hit your daily TOKEN quota. Wait for daily reset time above.")
            elif 'request' in error_msg.lower():
                print("💡 You've hit your daily REQUEST quota. Wait for daily reset time above.")
            else:
                print("💡 Rate limit hit. Check reset times above.")

            return False
        else:
            print(f"❌ API call failed with status {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error checking rate limits: {e}")
        return False

def test_basic_llm_with_rate_limits():
    """Test basic LLM functionality and capture rate limit information"""
    print("Testing basic LLM functionality and rate limits...")

    # test_prompt = "You are a helpful assistant. Please respond with a short greeting and tell me what you can help with."

    test_prompt = (
        "explain the following gif and give me context of what the user is meaning to say and what its typically used for. Convert it into a short message that can be used in a chatbot as well. Also give an example response of what the person receiving the message would say in response to the gif."
        "https://media3.giphy.com/media/O2kFK6fdz217a/giphy.gif"
    )

    try:
        # Make direct API call to capture headers
        api_key = os.getenv("CEREBRAS_API_KEY")
        if not api_key:
            print("❌ CEREBRAS_API_KEY not found")
            return False

        url = "https://api.cerebras.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama3.1-8b",
            "messages": [
                {"role": "user", "content": test_prompt}
            ],
            "temperature": 0.7,
            "stream": False
        }

        response = requests.post(url, json=payload, headers=headers)

        # Extract and display rate limit information regardless of success/failure
        print("\n📊 Rate Limit Information:")
        print("-" * 40)

        # Tokens remaining for current minute
        tokens_remaining = response.headers.get('x-ratelimit-remaining-tokens-minute')
        if tokens_remaining:
            print(f"Tokens remaining (current minute): {tokens_remaining}")

        # Time until daily request limit resets
        daily_reset = response.headers.get('x-ratelimit-reset-requests-day')
        if daily_reset:
            total_seconds = int(float(daily_reset))
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            print(f"⏰ Daily request limit resets in: {hours}h {minutes}m {seconds}s")

        # Time until per-minute token limit resets
        minute_reset = response.headers.get('x-ratelimit-reset-tokens-minute')
        if minute_reset:
            reset_seconds = int(float(minute_reset))
            print(f"⏰ Per-minute token limit resets in: {reset_seconds} seconds")

        # Additional rate limit info for reference
        daily_limit = response.headers.get('x-ratelimit-limit-requests-day')
        if daily_limit:
            print(f"Daily request limit: {daily_limit}")

        minute_limit = response.headers.get('x-ratelimit-limit-tokens-minute')
        if minute_limit:
            print(f"Per-minute token limit: {minute_limit}")

        daily_remaining = response.headers.get('x-ratelimit-remaining-requests-day')
        if daily_remaining:
            print(f"Daily requests remaining: {daily_remaining}")

        print("-" * 40)

        if response.status_code == 200:
            print("✅ LLM Response received successfully!")

            # Extract response content
            response_data = response.json()
            if response_data.get('choices'):
                content = response_data['choices'][0]['message']['content']
                print(f"Response: {content}")

            # Extract token usage information
            if 'usage' in response_data:
                usage = response_data['usage']
                print("\n🔢 Detailed Token Usage from Full Test:")
                print("=" * 50)

                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
                total_tokens = usage.get('total_tokens', 0)

                print(f"📥 Input tokens (prompt): {prompt_tokens}")
                print(f"📤 Output tokens (completion): {completion_tokens}")
                print(f"📊 Total tokens used: {total_tokens}")

                # Show all available usage fields
                print(f"\n🔍 All usage fields from this call:")
                for key, value in usage.items():
                    print(f"  {key}: {value}")

                print("=" * 50)
            else:
                print("\n⚠️ No token usage information available in response")
                print("Response structure:", list(response_data.keys()) if response_data else "No data")

            return True
        elif response.status_code == 429:
            print(f"⚠️ Rate limit exceeded (429): {response.text}")
            print("ℹ️ Check the reset times above to see when you can use the API again.")
            return False
        else:
            print(f"❌ API call failed with status {response.status_code}: {response.text}")
            return False

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

    # Run rate limit check first
    print("🔍 Checking current rate limit status...")
    rate_limit_success = check_rate_limit_status()

    # Only run full test if rate limits allow
    if rate_limit_success:
        print("\n" + "=" * 50)
        print("🚀 Rate limits OK - running full LLM test...")
        basic_success = test_basic_llm_with_rate_limits()
    else:
        print("\n⚠️ Rate limits exceeded - skipping full test")
        basic_success = False

    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Rate Limit Check: {'✅ PASS' if rate_limit_success else '❌ RATE LIMITED'}")
    if rate_limit_success:
        print(f"Basic LLM Test: {'✅ PASS' if basic_success else '❌ FAIL'}")
    else:
        print("Basic LLM Test: ⏭️ SKIPPED (rate limited)")

    if not rate_limit_success:
        print("\n💡 TIP: Use this script to check when your API quota resets!")


#python test_llm_cerebras.py