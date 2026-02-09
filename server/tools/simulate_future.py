from pathlib import Path
from openai import OpenAI
from server.resources.critiques import create_scaling_critique, save_critique, Critique
import json
from dotenv import load_dotenv
from uuid import uuid4
load_dotenv(override=True)

ROOT_PATH = Path(__file__).parent.parent.parent

# FUTURES_PATH = ROOT_PATH + Path("data\futures.json")
FUTURES_PATH = Path("C:\\Users\\gowri\\Documents\\Projects\\MCP\\SpeculativeSystemDesigner\\data\\futures.json")

client = OpenAI()

PROMPT_PATH = Path("server/prompts/scaling_future.txt")
futures = {}

with open(ROOT_PATH / "data/futures.json", "r") as f:
        futures = json.load(f)

def load_prompt():
    return PROMPT_PATH.read_text()

def simulate_future(future_id: str, architecture_text: str) -> dict:
    
    future = futures[future_id]

    prompt = future["review_prompt"]
    print(prompt)


    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": architecture_text}
        ]
    )
    raw_text = response.output[0].content[0].text
    # print(raw_text)
    # Remove markdown fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```json")[1].strip("```")
    # print("2222",raw_text)
    parsed = json.loads(raw_text)

    # print("---------",response.output[0].content[0].text.strip())

    # parsed = json.loads(response.output[0].content[0].text.strip())

    critique = Critique(
        id=str(uuid4()),
        future=future_id,
        summary=parsed["summary"],
        risks=parsed["risks"],
        required_tradeoff="Unresolved"
    )

    save_critique(critique)

    return critique.model_dump()



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
    save_critique(critique)

    return {
        "status": "critique_generated",
        "critique": critique.model_dump(),
        "analysis": parsed["summary"]
    }


