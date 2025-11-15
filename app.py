"""
Orchestrator and shared utilities (Modernized Gradio UI - compatible).

This file avoids using gr.Card and Row.style so it works with older Gradio releases.
Drop into your workspace and run with: python storycraft_modern.py
"""

import os
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import gradio as gr

# Load .env
load_dotenv()

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(BASE_DIR, "memories")
os.makedirs(MEM_DIR, exist_ok=True)
LOG_FILE = os.path.join(BASE_DIR, "logs.txt")

# --- API Key ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


# ---------------- Model Caller ----------------
def call_model(model, system_prompt, user_prompt, max_retries=4, timeout=30):
    """
    Robust model caller with improved 429 handling and exponential backoff.
    Returns model text or an error string starting with [ERROR].
    """
    if not GROQ_API_KEY:
        return "[ERROR] GROQ_API_KEY not set. Cannot call model."

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
            err = str(e)
            # If rate limited, wait longer and use linear increase per attempt
            if "429" in err or "Too Many Requests" in err:
                wait = 5 * attempt  # 5s, 10s, 15s, ...
                time.sleep(wait)
            else:
                # exponential backoff for other errors
                time.sleep(backoff)
                backoff *= 2

            if attempt == max_retries:
                return f"[ERROR] Model call failed after {attempt} attempts: {e}"

    return "[ERROR] Unexpected failure in call_model()"


# ---------------- Logging ----------------
def log_step(agent_name, summary):
    """Append timestamped log entries to logs.txt."""
    ts = datetime.utcnow().isoformat()
    line = f"{ts} | {agent_name} | {summary}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


# ---------------- Agents (mock if missing) ----------------
try:
    from agents import brief_agent, writer_agent, visual_agent, reviewer_agent, publisher_agent
except ImportError:
    print("WARNING: Could not import agents module. Agent functionality is mocked.")
    class MockAgent:
        def run(self, *args):
            if args and isinstance(args[0], str) and "brief" in args[0].lower():
                return '{"title": "Mock Story", "logline": "This is a mocked logline.", "themes": ["Mocking"]}'
            # simple simulated responses for other agents
            if args and isinstance(args[0], dict) and args[0].get('story'):
                return json.dumps({"status": "ok", "message": "Mock follow-up"})
            return json.dumps({"status": "mocked_output", "message": "Agent not implemented/imported"})
    brief_agent = MockAgent()
    writer_agent = MockAgent()
    visual_agent = MockAgent()
    reviewer_agent = MockAgent()
    publisher_agent = MockAgent()


# ---------------- Orchestration & Cache ----------------
# global cache now stores per-agent results for instant reload
_orch_cache = {}


def orchestrate(idea_text):
    """Backward-compatible full-run fallback (keeps existing behavior)."""
    global _orch_cache
    key = idea_text.strip()
    if key in _orch_cache:
        return _orch_cache[key]

    results = {}
    brief_out = brief_agent.run(idea_text)
    log_step("BriefAgent", str(brief_out)[:120])
    results["brief"] = brief_out

    writer_out = writer_agent.run(brief_out)
    log_step("WriterAgent", str(writer_out)[:120])
    results["writer"] = writer_out

    visual_out = visual_agent.run(writer_out)
    log_step("VisualAgent", str(visual_out)[:120])
    results["visual"] = visual_out

    reviewer_input = {"brief": brief_out, "story": writer_out, "visuals": visual_out}
    reviewer_out = reviewer_agent.run(reviewer_input)
    log_step("ReviewerAgent", str(reviewer_out)[:120])
    results["reviewer"] = reviewer_out

    publisher_input = {"brief": brief_out, "story": writer_out, "visuals": visual_out, "reviewer": reviewer_out}
    publisher_out = publisher_agent.run(publisher_input)
    log_step("PublisherAgent", str(publisher_out)[:120])
    results["publisher"] = publisher_out

    _orch_cache[key] = results
    return results


# ---------------- UI small components ----------------
def create_progress_tracker():
    """Return initial progress HTML using the update_progress helper."""
    # generate the progress HTML string and return a Gradio HTML component
    html = update_progress("brief", "pending")
    return gr.HTML(html)


def create_metrics_display():
    return gr.HTML("""
    <div class="metrics-row">
        <div class="metric"><div id="m-words">0</div><div class="m-label">Words</div></div>
        <div class="metric"><div id="m-chars">0</div><div class="m-label">Chars</div></div>
        <div class="metric"><div id="m-time">0 min</div><div class="m-label">Read</div></div>
        <div class="metric"><div id="m-score">-</div><div class="m-label">Quality</div></div>
    </div>
    """)


# ---------------- Helper: render combined progress + console ----------------
def render_progress_with_console(step, status, console_lines):
    """Return HTML containing both the visual tracker and a small console log under it."""
    tracker = update_progress(step, status)
    console_html = '<div class="agent-console">'
    for ln in console_lines[-12:]:
        console_html += f'<div class="console-line">{ln}</div>'
    console_html += '</div>'
    return tracker + console_html


# ---------------- Pipeline execution (sequential with live updates) ----------------
def run_pipeline_with_progress(idea):
    """Runs agents sequentially, yielding live UI updates after each step.

    Outputs (same order as UI bindings):
    progress_html, brief_out, writer_out, visual_out, reviewer_out, publisher_out, metrics_data
    """

    def fmt(x):
        if x is None: return "{}"
        if isinstance(x, dict): return json.dumps(x, indent=2)
        if isinstance(x, str):
            if not x or x.startswith("[ERROR]"):
                return json.dumps({"status": "error" if x.startswith("[ERROR]") else "empty", "message": x}, indent=2)
            try:
                return json.dumps(json.loads(x), indent=2)
            except json.JSONDecodeError:
                return x
        return json.dumps(x, indent=2)

    console = []
    key = idea.strip()

    # --- If fully cached, short-circuit with instant return ---
    if key and key in _orch_cache:
        results = _orch_cache[key]
        console.append(f"Loaded from cache for idea: '{key}'")
        brief_f = fmt(results.get('brief'))
        writer_f = fmt(results.get('writer'))
        visual_f = fmt(results.get('visual'))
        reviewer_f = fmt(results.get('reviewer'))
        publisher_f = fmt(results.get('publisher'))

        # metrics
        story_text = results.get('writer', '') if isinstance(results.get('writer'), str) else ''
        word_count = len(story_text.split()) if story_text else 0
        char_count = len(story_text)
        read_time = f"{(word_count // 200) or 1} min"
        quality_score = 'N/A'
        if isinstance(results.get('reviewer'), dict):
            quality_score = results['reviewer'].get('score', 'N/A')

        progress_html = render_progress_with_console('publisher', 'complete', console)
        yield (progress_html, brief_f, writer_f, visual_f, reviewer_f, publisher_f, f"{word_count},{char_count},{read_time},{quality_score}")
        return

    # Initialize UI: Brief running
    console.append("Starting pipeline...")
    console.append("Brief Agent: queued")
    yield (render_progress_with_console('brief', 'running', console), "{}", "", "{}", "{}", "", "")

    # --- Brief ---
    try:
        brief_out = brief_agent.run(idea)
        log_step("BriefAgent", str(brief_out)[:120])
        console.append("Brief Agent: complete")
        brief_f = fmt(brief_out)
    except Exception as e:
        brief_out = f"[ERROR] BriefAgent failed: {e}"
        brief_f = fmt(brief_out)
        console.append(brief_out)
        # stop pipeline and show error
        yield (render_progress_with_console('brief', 'error', console), brief_f, "", "{}", "{}", "", "0,0,0 min,N/A")
        return

    # Update: writer queued
    console.append("Writer Agent: queued")
    yield (render_progress_with_console('writer', 'running', console), brief_f, "", "{}", "{}", "", "")

    # --- Writer ---
    try:
        writer_out = writer_agent.run(brief_out)
        log_step("WriterAgent", str(writer_out)[:120])
        console.append("Writer Agent: complete")
        writer_f = fmt(writer_out)
    except Exception as e:
        writer_out = f"[ERROR] WriterAgent failed: {e}"
        writer_f = fmt(writer_out)
        console.append(writer_out)
        yield (render_progress_with_console('writer', 'error', console), brief_f, writer_f, "{}", "{}", "", "0,0,0 min,N/A")
        return

    # Update: visual queued
    console.append("Visual Agent: queued")
    yield (render_progress_with_console('visual', 'running', console), brief_f, writer_f, "{}", "{}", "", "")

    # --- Visual ---
    try:
        visual_out = visual_agent.run(writer_out)
        log_step("VisualAgent", str(visual_out)[:120])
        console.append("Visual Agent: complete")
        visual_f = fmt(visual_out)
    except Exception as e:
        visual_out = f"[ERROR] VisualAgent failed: {e}"
        visual_f = fmt(visual_out)
        console.append(visual_out)
        yield (render_progress_with_console('visual', 'error', console), brief_f, writer_f, visual_f, "{}", "", "0,0,0 min,N/A")
        return

    # Update: reviewer queued
    console.append("Reviewer Agent: queued")
    yield (render_progress_with_console('reviewer', 'running', console), brief_f, writer_f, visual_f, "{}", "", "")

    # --- Reviewer ---
    try:
        reviewer_input = {"brief": brief_out, "story": writer_out, "visuals": visual_out}
        reviewer_out = reviewer_agent.run(reviewer_input)
        log_step("ReviewerAgent", str(reviewer_out)[:120])
        console.append("Reviewer Agent: complete")
        reviewer_f = fmt(reviewer_out)
    except Exception as e:
        reviewer_out = f"[ERROR] ReviewerAgent failed: {e}"
        reviewer_f = fmt(reviewer_out)
        console.append(reviewer_out)
        yield (render_progress_with_console('reviewer', 'error', console), brief_f, writer_f, visual_f, reviewer_f, "", "0,0,0 min,N/A")
        return

    # Update: publisher queued
    console.append("Publisher Agent: queued")
    yield (render_progress_with_console('publisher', 'running', console), brief_f, writer_f, visual_f, reviewer_f, "", "")

    # --- Publisher ---
    try:
        publisher_input = {"brief": brief_out, "story": writer_out, "visuals": visual_out, "reviewer": reviewer_out}
        publisher_out = publisher_agent.run(publisher_input)
        # If publisher_agent internally calls call_model and hits 429, call_model will backoff accordingly
        log_step("PublisherAgent", str(publisher_out)[:120])
        console.append("Publisher Agent: complete")
        publisher_f = fmt(publisher_out)
    except Exception as e:
        publisher_out = f"[ERROR] PublisherAgent failed: {e}"
        publisher_f = fmt(publisher_out)
        console.append(publisher_out)
        yield (render_progress_with_console('publisher', 'error', console), brief_f, writer_f, visual_f, reviewer_f, publisher_f, "0,0,0 min,N/A")
        return

    # --- Save full results to cache (per-key) ---
    try:
        results = {"brief": brief_out, "writer": writer_out, "visual": visual_out, "reviewer": reviewer_out, "publisher": publisher_out}
        if key:
            _orch_cache[key] = results
            console.append(f"Cached results for idea: '{key}'")
    except Exception:
        pass

    # Compute final metrics
    story_text = writer_out if isinstance(writer_out, str) else ''
    word_count = len(story_text.split()) if story_text else 0
    char_count = len(story_text)
    read_time = f"{(word_count // 200) or 1} min"
    quality_score = 'N/A'
    try:
        if isinstance(reviewer_out, dict):
            quality_score = reviewer_out.get('score', 'N/A')
        elif isinstance(reviewer_out, str):
            try:
                rj = json.loads(reviewer_out)
                quality_score = rj.get('score', 'N/A')
            except Exception:
                quality_score = 'N/A'
    except Exception:
        quality_score = 'N/A'

    # Final render
    progress_html = render_progress_with_console('publisher', 'complete', console)
    yield (progress_html, fmt(brief_out), fmt(writer_out), fmt(visual_out), fmt(reviewer_out), fmt(publisher_out), f"{word_count},{char_count},{read_time},{quality_score}")


# ---------------- progress HTML builder (keeps original appearance) ----------------
def update_progress(step, status):
    steps = ["brief", "writer", "visual", "reviewer", "publisher"]
    html = '<div class="progress-track">'
    for s in steps:
        icon = {"brief": "📋", "writer": "✍️", "visual": "🎨", "reviewer": "✅", "publisher": "📰"}.get(s, "❓")
        status_icon = "•"
        status_text = "Pending"
        cls = "pending"
        if s == step:
            if status == "running":
                status_icon = "↻"
                status_text = "Running"
                cls = "running"
            elif status == "complete":
                status_icon = "✓"
                status_text = "Complete"
                cls = "complete"
            elif status == "error":
                status_icon = "✖"
                status_text = "Error"
                cls = "error"
        elif steps.index(s) < steps.index(step) and status != "error":
            status_icon = "✓"
            status_text = "Complete"
            cls = "complete"
        if status == "error" and steps.index(s) > steps.index(step):
            status_icon = "✖"
            status_text = "Error"
            cls = "error"

        # small bubble for substatus
        sub = "Idle"
        if s == step and status == 'running':
            sub = 'Running...'
        elif cls == 'complete':
            sub = 'Complete'
        elif cls == 'error':
            sub = 'Error'

        html += f'<div class="p-step {cls}" id="ps-{s}">'
        html += f'<div class="p-ic">{icon}</div>'
        html += f'<div class="p-title">{s.title()}</div>'
        html += f'<div class="p-sub">{sub}</div>'
        html += '</div>'

    html += '</div>'
    return html


# ---------------- Modern CSS (compatible) ----------------
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

:root{
  --bg: #f7f7f6;
  --card: #ffffff;
  --muted: #6b7280;
  --accent: #5b6cff;
  --radius: 12px;
}
body, .gradio-container {
  background: var(--bg) !important;
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
}

/* TOPBAR - full-width, stable */
.topbar{
  width:100% !important;
  display:flex;
  align-items:center;
  justify-content:flex-start;
  padding:14px 22px;
  background: var(--card);
  border-radius: var(--radius);
  box-shadow: 0 4px 14px rgba(0,0,0,0.05);
  margin-bottom: 14px;
  box-sizing:border-box;
  gap:14px;
}
.topbar-left { display:flex; align-items:center; gap:10px }
.brand { font-weight:700; font-size:1.15rem; color:#0f1724; letter-spacing: -0.2px; display:flex; align-items:center; gap:10px; }

/* NEW: colorful compact logo and gradient title for StoryCraft */
.brand .logo{
  width:42px;
  height:42px;
  border-radius:8px;
  display:flex;
  align-items:center;
  justify-content:center;
  background: linear-gradient(45deg, #ff7aa2 0%, #7c6bff 50%, #3ad1c8 100%);
  color: white;
  font-weight:800;
  box-shadow: 0 6px 18px rgba(124,107,255,0.12);
  font-size:14px;
}
.brand .title{
  background: linear-gradient(90deg, #ef4444 0%, #f97316 40%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight:800;
  font-size:1.05rem;
}
.sub { color:var(--muted); font-size:0.9rem }

/* card */
.card{ background: var(--card); border-radius: var(--radius); padding: 14px; box-shadow: 0 6px 18px rgba(17,24,39,0.06); border: 1px solid rgba(16,24,40,0.04); box-sizing:border-box; }

/* Agent buttons */
.agent-list{ display:flex; gap:8px; flex-wrap:wrap; margin-top:8px }
.agent-btn{
  background: transparent;
  border: 1px solid rgba(16,24,40,0.06);
  padding:8px 12px;
  border-radius: 999px;
  font-weight:600;
  cursor:pointer;
  transition: all 0.18s;
}
.agent-btn:hover{ transform: translateY(-3px); box-shadow: 0 8px 18px rgba(91,108,255,0.08); border-color: rgba(91,108,255,0.14) }

/* PROGRESS TRACK - force horizontal layout and stable sizing */
.progress-track{
  width:100% !important;
  display:flex !important;
  flex-direction:row !important;
  gap:12px !important;
  align-items:stretch !important;
  justify-content:space-between !important;
  min-height:90px;
  box-sizing:border-box;
}

.p-step{ flex:1 1 0; min-width:120px; max-width:22%; border-radius:10px; padding:12px 10px; text-align:center; background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(250,250,250,0.95)); border:1px solid rgba(16,24,40,0.03); box-sizing:border-box }
.p-step.running{ border-color: rgba(91,108,255,0.12) }
.p-step.complete{ background: rgba(34,197,94,0.06); border-color: rgba(34,197,94,0.12) }
.p-step.error{ background: rgba(244,63,94,0.06); border-color: rgba(244,63,94,0.12) }
.p-ic{ font-size:18px }
.p-title{ font-weight:700; font-size:0.95rem; color:#111 }
.p-sub{ font-size:0.78rem; color:var(--muted); margin-top:6px }

/* Progress compact small boxes (used for initial static tracker) */
.progress-compact{ display:flex; gap:8px; align-items:center; justify-content:space-between; }
.step-box{ background:var(--card); border-radius:8px; padding:8px 10px; display:flex; flex-direction:column; align-items:center; min-width:80px; box-shadow: 0 4px 12px rgba(2,6,23,0.04); border:1px solid rgba(16,24,40,0.03) }
.step-title{ font-weight:700; font-size:0.9rem; margin-top:6px }
.step-sub{ font-size:0.75rem; color:var(--muted) }

/* ensure the progress-area has its own white background so text is readable */
.output-column .card .progress-compact, .output-column .card .progress-track { background: transparent }

/* Metrics */
.metrics-row{ display:flex; gap:12px; margin-top:12px }
.metric{ background:var(--card); padding:10px 12px; border-radius:10px; text-align:center; flex:1; border:1px solid rgba(16,24,40,0.04) }
.metric > div:first-child{ font-weight:700; font-size:1.25rem; color:var(--accent) }
.m-label{ color:var(--muted); font-size:0.85rem }

textarea.gr-box, .gr-json-display, .gr-markdown, .gr-textbox{ border-radius:10px !important; border:1px solid rgba(16,24,40,0.04) !important; padding:12px !important; background: var(--card) !important }

button{ background: var(--accent) !important; color: white !important; padding: 10px 16px !important; border-radius: 10px !important; border:none !important; font-weight:700 }
button.secondary{ background:transparent !important; color:var(--accent) !important; border:1px solid rgba(91,108,255,0.12) !important }

/* agent console */
.agent-console{ margin-top:12px; background: #ffffff; color: #e6eef8; padding:10px; border-radius:8px; max-height:180px; overflow:auto; font-family: monospace; font-size:12px }
.console-line{ padding:2px 0 }

/* Fix for gr-markdown/prose text visibility - keep color but let background be default */
.gr-markdown,
.gr-markdown *,
.prose,
.prose * {
    color: #111 !important;
}

/* Only fix dark blocks inside the Published tab */
#tab-Published pre,
#tab-Published code,
#tab-Published .gr-code,
#tab-Published .gr-code *,
#tab-Published .gr-json-display,
#tab-Published .gr-json-display * {
    background: #ffffff !important;
    color: #111111 !important;
    border-radius: 10px !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
}

/* Prevent early stacking by ensuring containers reserve space */
.progress-track, .progress-compact { min-height: 70px }

@media (max-width:900px){ .metrics-row{ flex-direction:column } .progress-track{ flex-direction:column; gap:8px } }
"""


# ---------------- agent info helpers ----------------
def brief_info():
    return "**Brief Agent** — extracts core logline & themes. (Coordinating with Writer)."

def writer_info():
    return "**Writer Agent** — drafts scenes and dialog. (Uses Brief output)."

def visual_info():
    return "**Visual Agent** — creates visual prompt specs for concept art & storyboards."

def reviewer_info():
    return "**Reviewer Agent** — scores and suggests improvements. (Coordinates with Writer & Visual)."

def publisher_info():
    return "**Publisher Agent** — prepares final publishable output and metadata."


# ---------------- Build UI (compat-friendly) ----------------
def build_enhanced_ui():
    with gr.Blocks(title="StoryCraft — Modern", css=custom_css) as demo:

        # Topbar
        with gr.Row(elem_classes="topbar"):
            gr.Markdown(
                "<div style='display:flex;gap:8px;align-items:center;'>"
                "<div class='brand'>"
                  "<div class='logo'>SC</div>"
                  "<div class='title'>StoryCraft</div>"
                "</div>"
                "<div class='sub'>multi-agent story studio</div>"
                "</div>"
            )

        with gr.Row():
            # Left column (use Column as card container)
            with gr.Column(scale=2, min_width=320, elem_classes="input-column"):
                # Use Column as card wrapper
                with gr.Column(elem_classes="card"):
                    gr.Markdown("**Your Story Idea**")
                    idea = gr.Textbox(lines=4, placeholder="Enter a short idea...", label=None)

                    with gr.Row():
                        generate_btn = gr.Button("Generate Full Pipeline")
                        quick_btn = gr.Button("Quick Draft", elem_classes="secondary")

                    gr.Markdown("<div style='margin-top:10px; font-weight:700;'>Agents</div>")

                    with gr.Row(elem_classes="agent-list"):
                        brief_btn = gr.Button("📋 Brief", elem_id="btn-brief", elem_classes="agent-btn")
                        writer_btn = gr.Button("✍️ Writer", elem_classes="agent-btn")
                        visual_btn = gr.Button("🎨 Visual", elem_classes="agent-btn")
                        reviewer_btn = gr.Button("✅ Review", elem_classes="agent-btn")
                        publisher_btn = gr.Button("📰 Publish", elem_classes="agent-btn")

                    agent_info = gr.Markdown("_Click an agent to see what it does._", elem_classes="card", elem_id="agent-info")

            # Right column
            with gr.Column(scale=3, min_width=520, elem_classes="output-column"):
                with gr.Column(elem_classes="card"):
                    gr.Markdown("**Progress**")
                    progress_html = create_progress_tracker()
                    gr.Markdown("**Metrics**")
                    metrics_html = create_metrics_display()

                with gr.Column(elem_classes="card", ):
                    with gr.Tabs():
                        with gr.TabItem("Published"):
                            published_out = gr.Markdown("", label="Published Story")
                            gen_note_pub = gr.Markdown("_Generated by Publisher Agent (coordinated with Reviewer & Writer)_")

                        with gr.TabItem("Brief (JSON)"):
                            brief_out = gr.JSON(label="Brief JSON")
                            gen_note_brief = gr.Markdown("_Generated by Brief Agent_")

                        with gr.TabItem("Draft"):
                            writer_out = gr.Textbox(lines=12, show_label=False)
                            gen_note_writer = gr.Markdown("_Generated by Writer Agent (uses Brief)_")

                        with gr.TabItem("Visuals"):
                            visual_out = gr.JSON(label="Visual Prompts")
                            gen_note_visual = gr.Markdown("_Generated by Visual Agent_")

                        with gr.TabItem("Review"):
                            reviewer_out = gr.JSON(label="Review Output")
                            gen_note_review = gr.Markdown("_Generated by Reviewer Agent_")

        # Hidden metrics holder
        metrics_data = gr.Textbox(visible=False)

        # Agent buttons -> agent info
        brief_btn.click(fn=brief_info, inputs=[], outputs=[agent_info])
        writer_btn.click(fn=writer_info, inputs=[], outputs=[agent_info])
        visual_btn.click(fn=visual_info, inputs=[], outputs=[agent_info])
        reviewer_btn.click(fn=reviewer_info, inputs=[], outputs=[agent_info])
        publisher_btn.click(fn=publisher_info, inputs=[], outputs=[agent_info])

        # Quick pipeline: returns brief & writer quickly (sequential but no heavy waits)
        def quick_pipeline(idea_text):
            key = idea_text.strip()
            if key and key in _orch_cache:
                res = _orch_cache[key]
                brief_f = json.dumps(res.get('brief'), indent=2) if not isinstance(res.get('brief'), str) else res.get('brief')
                writer_f = json.dumps(res.get('writer'), indent=2) if not isinstance(res.get('writer'), str) else res.get('writer')
                return update_progress('writer', 'complete'), brief_f, writer_f, json.dumps({}, indent=2), json.dumps({}, indent=2), json.dumps({}, indent=2), f"{len(writer_f.split())},{len(writer_f)},{(len(writer_f.split())//200) or 1} min,N/A"

            # fallback to lightweight sequential calls
            b = brief_agent.run(idea_text)
            w = writer_agent.run(b)
            brief_f = json.dumps(b, indent=2) if not isinstance(b, str) else b
            writer_f = json.dumps(w, indent=2) if not isinstance(w, str) else w
            return update_progress('writer', 'complete'), brief_f, writer_f, json.dumps({}, indent=2), json.dumps({}, indent=2), json.dumps({}, indent=2), f"{len(writer_f.split())},{len(writer_f)},{(len(writer_f.split())//200) or 1} min,N/A"

        quick_btn.click(fn=quick_pipeline, inputs=[idea], outputs=[progress_html, brief_out, writer_out, visual_out, reviewer_out, published_out, metrics_data])

        # Full generate uses streaming/sequential pipeline
        generate_btn.click(
            fn=run_pipeline_with_progress,
            inputs=[idea],
            outputs=[progress_html, brief_out, writer_out, visual_out, reviewer_out, published_out, metrics_data]
        )

        # Metrics update callback
        def update_metrics(metrics_str):
            if metrics_str:
                word_count, char_count, read_time, quality_score = metrics_str.split(",")
                return f"""<div class='metrics-row'>
<div class='metric'><div>{word_count}</div><div class='m-label'>Words</div></div>
<div class='metric'><div>{char_count}</div><div class='m-label'>Chars</div></div>
<div class='metric'><div>{read_time}</div><div class='m-label'>Read Time</div></div>
<div class='metric'><div>{quality_score}</div><div class='m-label'>Quality</div></div>
</div>"""
            return create_metrics_display()

        metrics_data.change(fn=update_metrics, inputs=[metrics_data], outputs=[metrics_html])

    return demo


if __name__ == "__main__":
    demo = build_enhanced_ui()
    demo.queue()
    demo.launch(show_api=False, share=False, server_name="127.0.0.1", server_port=7860)
