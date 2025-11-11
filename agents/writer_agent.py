"""
Writer Agent:
- Role: write a short story based on the brief.
- Saves latest output to memories/writer_mem.json
"""
import os
import json

MEM_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memories", "writer_mem.json")
os.makedirs(os.path.dirname(MEM_PATH), exist_ok=True)

SYSTEM_PROMPT = (
    "You are the Writer Agent. Turn the structured brief into a compelling short story (~800-1200 words). "
    "Use vivid description and clear character voice. Output only the story text."
)

def _save_mem(data):
    with open(MEM_PATH, "w", encoding="utf-8") as f:
        json.dump({"story": data}, f, ensure_ascii=False, indent=2)

def run(brief):
    from app import call_model, log_step
    try:
        user_prompt = "Brief:\n" + (json.dumps(brief, ensure_ascii=False) if isinstance(brief, dict) else str(brief))
        story = call_model("llama-3.1-8b-instant", SYSTEM_PROMPT, user_prompt)
        _save_mem(story)
        log_step("WriterAgent", (story[:120].replace("\n", " ")))
        return story
    except Exception as e:
        err = f"[ERROR] {e}"
        _save_mem(err)
        log_step("WriterAgent", f"ERROR: {e}")
        return err
