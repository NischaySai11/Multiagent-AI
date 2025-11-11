"""
Brief Agent:
- Role: condense a short idea into a structured story brief JSON.
- Output saved to memories/brief_mem.json
"""
import os
import json

MEM_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memories", "brief_mem.json")
os.makedirs(os.path.dirname(MEM_PATH), exist_ok=True)

SYSTEM_PROMPT = (
    "You are the Brief Agent. Given a short idea, produce a concise JSON brief "
    "with fields: title, logline, themes (list), characters (list of {name, role, traits}), "
    "setting, tone, target_audience, key_scenes (list), image_requirements (list). "
    "Only output valid JSON."
)

def _save_mem(data):
    with open(MEM_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run(idea_text):
    """
    Produce a brief from an idea. Calls app.call_model at runtime to avoid circular import.
    """
    from app import call_model, log_step
    try:
        user_prompt = f"Idea: {idea_text}\nReturn a single JSON object as described."
        raw = call_model("llama-3.1-8b-instant", SYSTEM_PROMPT, user_prompt)
        try:
            brief = json.loads(raw)
        except Exception:
            # If model didn't return strict JSON, wrap raw string
            brief = {"raw_brief": raw}
        _save_mem(brief)
        summary = brief.get("title", brief.get("raw_brief", str(idea_text)) )[:120]
        log_step("BriefAgent", summary)
        return brief
    except Exception as e:
        err = {"error": str(e)}
        _save_mem(err)
        log_step("BriefAgent", f"ERROR: {e}")
        return err
