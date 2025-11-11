"""
Publisher Agent:
- Role: assemble final Markdown with title, byline, story, and image placeholders with visual prompts.
- Saves latest output to memories/publisher_mem.json
"""
import os
import json

MEM_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memories", "publisher_mem.json")
os.makedirs(os.path.dirname(MEM_PATH), exist_ok=True)

SYSTEM_PROMPT = (
    "You are the Publisher Agent. Assemble a final polished Markdown story using the brief, story text, visuals, and reviewer notes. "
    "Include image placeholders with labels and the visual prompts as captions. Output only Markdown."
)

def _save_mem(data):
    with open(MEM_PATH, "w", encoding="utf-8") as f:
        json.dump({"published": data}, f, ensure_ascii=False, indent=2)

def run(context):
    from app import call_model, log_step
    try:
        user_prompt = "Context:\n" + json.dumps(context, ensure_ascii=False)
        md = call_model("llama-3.1-8b-instant", SYSTEM_PROMPT, user_prompt)
        _save_mem(md)
        log_step("PublisherAgent", (md[:120].replace("\n", " ")))
        return md
    except Exception as e:
        err = f"[ERROR] {e}"
        _save_mem(err)
        log_step("PublisherAgent", f"ERROR: {e}")
        return err
