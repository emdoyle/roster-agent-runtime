import os

import openai
from roster_agent_runtime.logs import app_logger
from tenacity import retry, stop_after_attempt, wait_random_exponential

logger = app_logger()


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(4))
async def ask_openai(prompt: str, system_message: str, **openai_kwargs):
    user_message = {"content": prompt, "role": "user"}
    system_message = {"content": system_message, "role": "system"}
    kwargs = {
        "api_key": os.environ["ROSTER_OPENAI_API_KEY"],
        "model": "gpt-4",
        "messages": [system_message, user_message],
        "n": 1,
        "stop": None,
        "temperature": 0.2,
        **openai_kwargs,
    }
    try:
        logger.debug("(openai-llm) input: %s", prompt)
        response = await openai.ChatCompletion.acreate(**kwargs)
        output = response.choices[0]["message"]["content"]
        logger.debug("(openai-llm) output: %s", output)
    except Exception:
        logger.exception("(openai-llm) Failed to call OpenAI")
        raise

    return output
