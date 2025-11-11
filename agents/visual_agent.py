"""
Visual Agent:
- Role: create image-generation prompts for key scenes.
- Saves latest output to memories/visual_mem.json
"""
import os
import json

MEM_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memories", "visual_mem.json")
os.makedirs(os.path.dirname(MEM_PATH), exist_ok=True)

SYSTEM_PROMPT = (
    "You are the Visual Agent. From the brief, produce 3 image-generation prompts for key scenes. "
    "For each, include: id, scene_description, camera, lighting, mood, style (artistic references), "
    "and safety_notes. Output JSON list."
)

def _save_mem(data):
    with open(MEM_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run(brief):
    from app import call_model, log_step
    try:
        user_prompt = "Brief:\n" + (json.dumps(brief, ensure_ascii=False) if isinstance(brief, dict) else str(brief))
        raw = call_model("llama-3.1-8b-instant", SYSTEM_PROMPT, user_prompt)
        try:
            visuals = json.loads(raw)
        except Exception:
            visuals = {"raw_visuals": raw}
        _save_mem(visuals)
        summary = str(visuals)[:120]
        log_step("VisualAgent", summary)
        return visuals
    except Exception as e:
        err = {"error": str(e)}
        _save_mem(err)
        log_step("VisualAgent", f"ERROR: {e}")
        return err
