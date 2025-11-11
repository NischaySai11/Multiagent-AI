"""
Reviewer Agent:
- Role: evaluate brief, story, and visuals and output strict JSON validated by jsonschema.
- Saves latest output to memories/reviewer_mem.json
"""
import os
import json
from jsonschema import validate, ValidationError

MEM_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memories", "reviewer_mem.json")
os.makedirs(os.path.dirname(MEM_PATH), exist_ok=True)

# Schema the reviewer must produce
REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string"},
        "score": {"type": "number", "minimum": 0, "maximum": 100},
        "issues": {
            "type": "array",
            "items": {"type": "string"}
        },
        "recommendations": {"type": "string"},
        "summary": {"type": "string"}
    },
    "required": ["verdict", "score", "issues", "recommendations", "summary"],
    "additionalProperties": False
}

SYSTEM_PROMPT = (
    "You are the Reviewer Agent. Evaluate the brief, story, and visuals. Produce a strict JSON matching the schema: "
    "verdict (Approved/Needs Work/Rejected), score (0-100), issues (list), recommendations (string), summary (string). "
    "Output only JSON that validates against the schema."
)

def _save_mem(data):
    with open(MEM_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run(context):
    """
    context: dict with keys brief, story, visuals
    """
    from app import call_model, log_step
    try:
        user_prompt = "Context:\n" + json.dumps(context, ensure_ascii=False)
        raw = call_model("llama-3.1-8b-instant", SYSTEM_PROMPT, user_prompt)
        try:
            parsed = json.loads(raw)
        except Exception:
            # If parser fails, ask the model to output JSON strictly (fallback)
            parsed = {"error": "Reviewer did not return valid JSON", "raw": raw}
            _save_mem(parsed)
            log_step("ReviewerAgent", "Invalid JSON from model")
            return parsed
        # Validate
        try:
            validate(instance=parsed, schema=REVIEW_SCHEMA)
        except ValidationError as ve:
            # Return structured error
            err = {"error": "validation_failed", "message": str(ve), "candidate": parsed}
            _save_mem(err)
            log_step("ReviewerAgent", f"Validation failed: {ve.message}")
            return err
        _save_mem(parsed)
        log_step("ReviewerAgent", parsed.get("summary", "")[:120])
        return parsed
    except Exception as e:
        err = {"error": str(e)}
        _save_mem(err)
        log_step("ReviewerAgent", f"ERROR: {e}")
        return err
