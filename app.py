"""
Orchestrator and shared utilities.

Contains:
- call_model(model, system_prompt, user_prompt): Groq API wrapper with retries/timeouts.
- log_step(agent, summary): append step logs to logs.txt.
- orchestrate(idea): run agents in sequence.
- Gradio demo launch.
"""

import os
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import gradio as gr

# Load .env file for local use
load_dotenv()

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(BASE_DIR, "memories")
os.makedirs(MEM_DIR, exist_ok=True)
LOG_FILE = os.path.join(BASE_DIR, "logs.txt")

# --- API Key ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    print("⚠️  GROQ_API_KEY not set. Please set it in .env or environment variables.")

# --- Groq API Base URL (correct one) ---
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


# -------------------------------------------------------------------------
# 1️⃣ Model Caller
# -------------------------------------------------------------------------
def call_model(model, system_prompt, user_prompt, max_retries=3, timeout=30):
    """
    Groq API (OpenAI-compatible) call with retry + backoff.
    Returns model's text response or [ERROR] message.
    """
    assert GROQ_API_KEY, "GROQ_API_KEY not set in environment"

    url = f"{GROQ_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 800,
        "temperature": 0.7
    }

    backoff = 2
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content
        except Exception as e:
            if attempt == max_retries:
                return f"[ERROR] Model call failed after {attempt} attempts: {e}"
            print(f"Retrying Groq model call ({attempt}/{max_retries}) after error: {e}")
            time.sleep(backoff)
            backoff *= 2
    return "[ERROR] Unexpected failure in call_model()"


# -------------------------------------------------------------------------
# 2️⃣ Logging Utility
# -------------------------------------------------------------------------
def log_step(agent_name, summary):
    """Append timestamped log entries to logs.txt."""
    ts = datetime.utcnow().isoformat()
    line = f"{ts} | {agent_name} | {summary}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


# -------------------------------------------------------------------------
# 3️⃣ Import Agents
# -------------------------------------------------------------------------
# Import only after defining utilities to avoid circular import issues.
from agents import brief_agent, writer_agent, visual_agent, reviewer_agent, publisher_agent


# -------------------------------------------------------------------------
# 4️⃣ Orchestration Flow
# -------------------------------------------------------------------------
def orchestrate(idea_text):
    """
    Run full story-creation pipeline:
    Brief → Writer → Visual → Reviewer → Publisher.
    Returns a dict with all agent outputs.
    """
    results = {}

    # --- Brief Agent ---
    brief_out = brief_agent.run(idea_text)
    log_step("BriefAgent", str(brief_out)[:120])
    results["brief"] = brief_out

    # --- Writer Agent ---
    writer_out = writer_agent.run(brief_out)
    log_step("WriterAgent", str(writer_out)[:120])
    results["writer"] = writer_out

    # --- Visual Agent ---
    visual_out = visual_agent.run(writer_out)
    log_step("VisualAgent", str(visual_out)[:120])
    results["visual"] = visual_out

    # --- Reviewer Agent ---
    reviewer_input = {
        "brief": brief_out,
        "story": writer_out,
        "visuals": visual_out
    }
    reviewer_out = reviewer_agent.run(reviewer_input)
    log_step("ReviewerAgent", str(reviewer_out)[:120])
    results["reviewer"] = reviewer_out

    # --- Publisher Agent ---
    publisher_input = {
        "brief": brief_out,
        "story": writer_out,
        "visuals": visual_out,
        "reviewer": reviewer_out
    }
    publisher_out = publisher_agent.run(publisher_input)
    log_step("PublisherAgent", str(publisher_out)[:120])
    results["publisher"] = publisher_out

    return results


# -------------------------------------------------------------------------
# 5️⃣ Gradio Frontend
# -------------------------------------------------------------------------
def run_pipeline(idea):
    try:
        out = orchestrate(idea)
        # Format for UI
        def fmt(x):
            if isinstance(x, (dict, list)):
                return json.dumps(x, indent=2)
            return str(x)
        return fmt(out["brief"]), fmt(out["writer"]), fmt(out["visual"]), fmt(out["reviewer"]), fmt(out["publisher"])
    except AssertionError as ae:
        return f"AssertionError: {ae}", "", "", "", ""
    except Exception as e:
        return f"Exception: {e}", "", "", "", ""


# -------------------------------------------------------------------------
# 6️⃣ Launch App (Safe version-independent layout)
# -------------------------------------------------------------------------
title = "AI Story Studio 🧠🎨"
desc = "Collaborative agentic system that creates illustrated short stories using open-source models via Groq."

def build_ui():
    with gr.Blocks(title=title) as demo:
        gr.Markdown(f"# {title}\n\n{desc}")

        idea = gr.Textbox(
            lines=3,
            placeholder="Enter a short story idea (e.g., A robot finding friendship on Mars)",
            label="Story Idea"
        )

        brief_out = gr.Textbox(label="Brief Agent JSON", lines=8)
        writer_out = gr.Textbox(label="Writer Story Text", lines=10)
        visual_out = gr.Textbox(label="Visual Agent Prompts", lines=8)
        reviewer_out = gr.Textbox(label="Reviewer Feedback (JSON)", lines=8)
        published_out = gr.Textbox(label="Final Published Story (Markdown)", lines=12)

        generate_btn = gr.Button("✨ Generate Story", variant="primary")

        # --- bind safely using gr.on(event=...) ---
        generate_btn.click(
            fn=run_pipeline,
            inputs=[idea],
            outputs=[brief_out, writer_out, visual_out, reviewer_out, published_out]
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.queue()   # <-- ensures async safety
    demo.launch(show_api=False)
