import os
import json
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
import time

load_dotenv()

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
CEREBRAS_MODEL = "llama3.1-8b"

# Initialize Cerebras client once
cerebras_client = Cerebras(api_key=CEREBRAS_API_KEY)

# Try importing job schema
default_schema = None
try:
    from rag.models.schemas import job_schema
    default_schema = job_schema
except ImportError:
    pass

def call_cerebras_llm(
    prompt: str,
    model: str = CEREBRAS_MODEL,
    structured: bool = False,
    stream: bool = False,
    json_schema: dict = None,
    temperature: float = 0.5,
    stream_delay: float = 0.025
) -> str:
    messages = [{"role": "user", "content": prompt}]
    kwargs = {"model": model, "messages": messages}

    if structured:
        schema = json_schema or default_schema
        if schema is None:
            raise ValueError("No JSON schema provided for structured output.")
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "job_schema",
                "strict": True,
                "schema": schema,
            },
        }

    try:
        response = cerebras_client.chat.completions.create(**kwargs, stream=stream)

        if stream:
            full_text = ""
            for chunk in response:
                content = getattr(chunk.choices[0].delta, "content", "") or ""
                print(content, end="", flush=True)
                full_text += content
                if stream_delay > 0:
                    time.sleep(stream_delay)
            return full_text
        else:
            return response.choices[0].message.content

    except Exception as e:
        return f"[Cerebras LLM error: {str(e)}]"

if __name__ == "__main__":
    from rag.models.schemas import job_schema
    test_prompt = "You are a helpful assistant. Suggest a job in the UK and make it a 5000 word job description"

    try:
        answer = call_cerebras_llm(
            prompt=test_prompt,
            model="llama-4-scout-17b-16e-instruct",
            structured=True,
            json_schema=job_schema,
            stream=False
        )
        print("\n\nFull response:\n", answer)
        try:
            print(json.dumps(json.loads(answer), indent=2))
        except Exception:
            print("Could not parse as JSON.")
    except Exception as e:
        print("Error calling Cerebras LLM:", e)
    #python -m rag.models.llm_cerebras
