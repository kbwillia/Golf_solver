import os
from dotenv import load_dotenv
import ollama

def call_llama(
    prompt: str,
    model: str = "llama3.1",
    structured: bool = False,
    stream: bool = False,
    json_schema: dict = None,
    temperature: float = 0.5,
    stream_delay: float = 0.025
) -> str:
    """
    Call the Ollama LLM and return the response message.
    If stream=False, returns the message string.
    If stream=True, returns the full text response.
    """
    messages = [{"role": "user", "content": prompt}]

    # Prepare options
    options = {
        "temperature": temperature,
        "num_ctx": 2048
    }

    # Add structured output if requested
    if structured and json_schema:
        # Note: Ollama may not support structured output like Cerebras
        # For now, we'll add a note in the prompt
        prompt = f"{prompt}\n\nPlease respond in valid JSON format according to this schema: {json_schema}"
        messages = [{"role": "user", "content": prompt}]

    try:
        if stream:
            # Handle streaming response
            full_text = ""
            response = ollama.chat(
                model=model,
                messages=messages,
                options=options,
                stream=True
            )

            for chunk in response:
                content = chunk.get('message', {}).get('content', '')
                print(content, end="", flush=True)
                full_text += content
                if stream_delay > 0:
                    import time
                    time.sleep(stream_delay)
            return full_text
        else:
            # Handle non-streaming response
            response = ollama.chat(
                model=model,
                messages=messages,
                options=options
            )

            message = response['message']['content']
            return message

    except Exception as e:
        return f"[Ollama LLM error: {str(e)}]"

def main():
    # Load environment variables
    load_dotenv()

    # Simple Q&A test with Llama 3.1
    print("\n=== Simple Llama 3.1 Q&A Test ===")

    # Create a chat completion
    question = "What is the capital of usa?"
    response = call_llama(
        prompt=question,
        model='llama3.1',
        structured=False,
        stream=False,
        temperature=0.3
    )

    # Print the response
    print(f"\nQuestion: {question}")
    print("Response:", response)
    print("\nModel Info:")
    print(f"- Model: llama3.1")
    print(f"- Context Length: 2048")
    print(f"- Temperature: 0.3")

if __name__ == "__main__":
    main()