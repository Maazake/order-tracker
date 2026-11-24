import json
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel

from app.config import settings
from app.schemas import ProcessStage


class StepNote(BaseModel):
    stage: ProcessStage
    text: str
    category: Literal["routine", "defect", "machine", "material"]


class StepNoteBatch(BaseModel):
    notes: list[StepNote]


NOTES_SYSTEM_PROMPT = """You are a CNC operator writing short notes after finishing a step.
Your note must be in english, 1 sentence long, 
specific and mostly with numbers and dimensions.
About half of the notes are routine. The rest are problems,
split roughly evenly between defect, machine and material.
We have 4 categories: routine - step went normally | defect - flaw in detail,
or wrong size etc. | machine - problem with machine or tool | material - problem with 
input material.
Notes should look like: "Material cut with 2 mm allowance." or
"2 pcs rejected: thread M12 out of tolerance, reworked and accepted." or
"Burrs on tooth edges removed manually."
All notes must describe work typical for the stage given by the user.
Do not repeat notes.
"""


def generate_notes(
    client: anthropic.Anthropic, stage: ProcessStage, count: int = 25
) -> list[StepNote]:
    content = f"Write {count} notes for the {stage} stage"

    response = client.messages.parse(
        model=settings.anthropic_model,
        max_tokens=4000,
        system=NOTES_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        output_format=StepNoteBatch,
    )
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        raise RuntimeError(f"No notes for {stage}: {response.stop_reason}")
    return response.parsed_output.notes


api_key = settings.anthropic_api_key.get_secret_value()

if __name__ == "__main__":
    client = anthropic.Anthropic(api_key=api_key)

    all_notes = []
    for stage in ProcessStage:
        notes = generate_notes(client, stage)
        all_notes.extend(notes)
        print(stage, len(notes))

    data = [note.model_dump(mode="json") for note in all_notes]

    Path("data").mkdir(exist_ok=True)
    with open("data/step_notes.json", "w") as file:
        json.dump(data, file, indent=2)

    print("Total:", len(all_notes))
