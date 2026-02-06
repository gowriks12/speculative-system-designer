from pathlib import Path
from openai import OpenAI
from server.resources.critiques import create_scaling_critique
import jsonschema
from dotenv import load_dotenv
load_dotenv(override=True)

client = OpenAI()

PROMPT_PATH = Path("server/prompts/scaling_future.txt")


def load_prompt():
    return PROMPT_PATH.read_text()


def simulate_scaling_future(architecture_text: str) -> dict:

    evaluation_prompt = load_prompt()

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": evaluation_prompt
            },
            {
                "role": "user",
                "content": architecture_text
            }
        ],
        # text=jsonschema
    )

    result = response.output[0].content[0].text
    # print(result)
    import json
    parsed = json.loads(result)
    # print(parsed)

    critique = create_scaling_critique(parsed["risks"])

    return {
        "status": "critique_generated",
        "critique": critique.model_dump(),
        "analysis": parsed["summary"]
    }


