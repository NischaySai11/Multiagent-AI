"""
Orchestrator and shared utilities.

This file contains the core Gradio application structure,
API communication logic (using Groq as a mock target), 
and the custom CSS for the professional UI design.
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
# NOTE: Removed assert to allow UI to load even if key is missing,
# but the model calls will fail gracefully.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


# -------------------------------------------------------------------------
# 1️⃣ Model Caller (Placeholder/Mock Groq Integration)
# -------------------------------------------------------------------------
def call_model(model, system_prompt, user_prompt, max_retries=3, timeout=30):
    """
    Groq API (OpenAI-compatible) call with retry + backoff.
    Returns model's text response or [ERROR] message.
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
            if attempt == max_retries:
                return f"[ERROR] Model call failed after {attempt} attempts: {e}"
            
            # FIX: Mandatory cooldown for 429 rate limits
            if "429" in str(e):
                time.sleep(3)   # Wait 3 seconds if rate-limited
            else:
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
# 3️⃣ Import Agents (Mocked for safety/completeness)
# -------------------------------------------------------------------------
try:
    # NOTE: This assumes an 'agents.py' file exists.
    from agents import brief_agent, writer_agent, visual_agent, reviewer_agent, publisher_agent
except ImportError:
    print("WARNING: Could not import agents module. Agent functionality is mocked.")
    class MockAgent:
        def run(self, *args):
            # Returns a valid JSON string for gr.JSON to prevent parsing errors
            if "brief" in args:
                 return '{"title": "Mock Story", "logline": "This is a mocked logline.", "themes": ["Mocking"]}'
            return json.dumps({"status": "mocked_output", "message": "Agent not implemented/imported"})
    brief_agent = MockAgent()
    writer_agent = MockAgent()
    visual_agent = MockAgent()
    reviewer_agent = MockAgent()
    publisher_agent = MockAgent()


# -------------------------------------------------------------------------
# 4️⃣ Orchestration Flow
# -------------------------------------------------------------------------
# Simple global cache to prevent double execution
_orch_cache = {}

def orchestrate(idea_text):
    """Run full story-creation pipeline."""

    global _orch_cache
    key = idea_text.strip()

    # --- If cached output exists, return it immediately ---
    if key in _orch_cache:
        return _orch_cache[key]

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
    reviewer_input = {"brief": brief_out, "story": writer_out, "visuals": visual_out}
    reviewer_out = reviewer_agent.run(reviewer_input)
    log_step("ReviewerAgent", str(reviewer_out)[:120])
    results["reviewer"] = reviewer_out

    # --- Publisher Agent ---
    publisher_input = {"brief": brief_out, "story": writer_out, "visuals": visual_out, "reviewer": reviewer_out}
    publisher_out = publisher_agent.run(publisher_input)
    log_step("PublisherAgent", str(publisher_out)[:120])
    results["publisher"] = publisher_out

    # --- Save in cache ---
    _orch_cache[key] = results

    return results



# -------------------------------------------------------------------------
# 5️⃣ UI Components (HTML Generation)
# -------------------------------------------------------------------------
def create_progress_tracker():
    """Create a beautiful progress tracker HTML structure."""
    return gr.HTML("""
    <div class="progress-container">
        <div class="progress-bar">
            <div class="progress-step" id="step-brief">
                <div class="step-icon">📋</div>
                <div class="step-label">Brief</div>
                <div class="step-status">Pending</div>
            </div>
            <div class="progress-step" id="step-writer">
                <div class="step-icon">✍️</div>
                <div class="step-label">Writer</div>
                <div class="step-status">Pending</div>
            </div>
            <div class="progress-step" id="step-visual">
                <div class="step-icon">🎨</div>
                <div class="step-label">Visual</div>
                <div class="step-status">Pending</div>
            </div>
            <div class="progress-step" id="step-reviewer">
                <div class="step-icon">✅</div>
                <div class="step-label">Review</div>
                <div class="step-status">Pending</div>
            </div>
            <div class="progress-step" id="step-publisher">
                <div class="step-icon">📰</div>
                <div class="step-label">Publish</div>
                <div class="step-status">Pending</div>
            </div>
        </div>
    </div>
    """)


def create_metrics_display():
    """Create metrics display HTML structure."""
    return gr.HTML("""
    <div class="metrics-container">
        <div class="metric-card">
            <div class="metric-value" id="word-count">0</div>
            <div class="metric-label">Words</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="char-count">0</div>
            <div class="metric-label">Characters</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="read-time">0 min</div>
            <div class="metric-label">Reading Time</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="quality-score">-</div>
            <div class="metric-label">Quality Score</div>
        </div>
    </div>
    """)


# -------------------------------------------------------------------------
# 6️⃣ Pipeline Execution Logic (with UI updates)
# -------------------------------------------------------------------------
def run_pipeline_with_progress(idea):
    """Runs the agent pipeline and yields intermediate UI updates."""
    
    def fmt(x):
        """Safely formats output for Gradio components."""
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


    try:
        # Initialize UI state
        yield update_progress("brief", "running"), "{}", "", "{}", "{}", "", ""
        
        out = orchestrate(idea)
        
        # Calculate metrics
        story_text = out.get("writer", "") if isinstance(out.get("writer"), str) else ""
        word_count = len(story_text.split())
        char_count = len(story_text)
        read_time = f"{word_count // 200} min"
        
        # Get quality score
        quality_score = "N/A"
        if "reviewer" in out and isinstance(out["reviewer"], dict):
            quality_score = out["reviewer"].get("score", "N/A")
        
        # Format outputs
        brief_formatted = fmt(out.get("brief"))
        writer_formatted = fmt(out.get("writer"))
        visual_formatted = fmt(out.get("visual"))
        reviewer_formatted = fmt(out.get("reviewer"))
        publisher_formatted = fmt(out.get("publisher")) 
        
        # Final update
        progress_html = update_progress("publisher", "complete")
        
        yield (progress_html, brief_formatted, writer_formatted, visual_formatted, 
               reviewer_formatted, publisher_formatted, 
               f"{word_count},{char_count},{read_time},{quality_score}")
        
    except Exception as e:
        error_msg = f"[ERROR] Pipeline Exception: {e}"
        error_html = update_progress("error", "error")
        json_error_output = json.dumps({"status": "pipeline_error", "message": error_msg}, indent=2)
        
        yield (error_html, json_error_output, error_msg, json_error_output, 
               json_error_output, error_msg, "0,0,0 min,N/A")


def update_progress(step, status):
    """Updates progress tracker HTML with current step status."""
    steps = ["brief", "writer", "visual", "reviewer", "publisher"]
    html = '<div class="progress-container"><div class="progress-bar">'
    
    for s in steps:
        icon = {"brief": "📋", "writer": "✍️", "visual": "🎨", "reviewer": "✅", "publisher": "📰"}.get(s, "❓")
        status_icon = "🟡"
        status_text = "Pending"
        
        if s == step:
            if status == "running":
                status_icon = "🟠"
                status_text = "Running..."
            elif status == "complete":
                status_icon = "🟢"
                status_text = "Complete"
            elif status == "error":
                status_icon = "🔴"
                status_text = "Error"
        elif steps.index(s) < steps.index(step) and status != "error":
            status_icon = "🟢"
            status_text = "Complete"
        
        # If any step fails, subsequent steps show error
        if status == "error" and steps.index(s) > steps.index(step):
            status_icon = "🔴"
            status_text = "Error"
        
        html += f"""
            <div class="progress-step {status.lower()}" id="step-{s}">
                <div class="step-icon">{icon}</div>
                <div class="step-label">{s.title()}</div>
                <div class="step-status">{status_icon} {status_text}</div>
            </div>
        """
    
    html += '</div></div>'
    return html


# -------------------------------------------------------------------------
# 7️⃣ Custom CSS (Professional Styling)
# -------------------------------------------------------------------------
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* General Gradio Overrides */
.gradio-container {
    max-width: 1400px !important;
    margin: 0 auto !important;
    font-family: 'Inter', sans-serif;
    background-color: #f8f9fa; /* Light grey background */
    padding: 0;
}

/* --- HERO HEADER --- */
.hero-header {
    text-align: center;
    padding: 5rem 0;
    background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%); /* Soft gradient */
    border-radius: 12px;
    margin-bottom: 2rem;
    color: #333;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.hero-header h1 {
    font-size: 3.5rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
    background: linear-gradient(45deg, #667eea, #764ba2); /* Primary text gradient */
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-header p {
    font-size: 1.5rem;
    opacity: 0.8;
    font-weight: 500;
}

/* --- INPUT/AGENT COLUMN --- */
.input-column {
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    height: 100%;
}

/* --- OUTPUT/PROGRESS COLUMN --- */
.output-column {
    padding: 0 0 0 1rem; /* Adjust padding to match design */
}

/* --- AGENT CARDS (Styled list) --- */
.agent-list h3 {
    font-size: 1.25rem;
    font-weight: 700;
    color: #2d3748;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid #eee;
    padding-bottom: 0.5rem;
}

.agent-card {
    display: flex;
    align-items: center;
    background: #fcfcfc;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    margin-bottom: 0.5rem;
    border: 1px solid #eee;
    transition: all 0.2s ease;
}

.agent-card:hover {
    background: #e0e7ff;
    border-color: #667eea;
    cursor: pointer;
}

.agent-icon {
    font-size: 1.2rem;
    margin-right: 1rem;
    color: #667eea;
}

.agent-name {
    font-weight: 600;
    color: #333;
    flex-grow: 1;
}

.agent-status {
    font-size: 0.85rem;
    font-weight: 500;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    background: #e2e8f0;
    color: #718096;
}

/* --- PROGRESS TRACKER --- */
.progress-container {
    margin: 2rem 0;
    padding: 1rem;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
}

.progress-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
}

.progress-step {
    text-align: center;
    flex: 1;
    padding: 0.5rem;
    border-radius: 8px;
    transition: all 0.3s ease;
    border: 2px solid transparent;
}

.progress-step.running {
    background: #fff3cd;
    border-color: #ffc107;
    transform: scale(1.02);
}

.progress-step.complete {
    background: #d4edda;
    border-color: #28a745;
}

.progress-step.error {
    background: #f8d7da;
    border-color: #dc3545;
}

.step-icon {
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
}

.step-label {
    font-weight: 600;
    font-size: 0.9rem;
    color: #2d3748;
}

.step-status {
    font-size: 0.75rem;
    color: #718096;
}

/* --- METRICS DISPLAY --- */
.metrics-container {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 10px;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    border: 1px solid #e2e8f0;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #667eea; /* Highlighted primary color */
    margin-bottom: 0.25rem;
}

.metric-label {
    font-size: 0.8rem;
    color: #718096;
    font-weight: 500;
}

/* FIX: Published Story text visibility */
.gr-markdown, 
.gr-markdown *, 
.prose, 
.prose * {
    color: #111 !important;        /* Dark readable text */
    background: transparent !important;
}



/* --- Gradio Component Overrides --- */
button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 1rem 2rem !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
}

textarea.gr-box, .gr-json-display, .gr-markdown, .gr-textbox {
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    background: #ffffff !important;
    padding: 1rem !important;
    box-shadow: none !important;
    min-height: 250px;
    overflow-y: auto !important;
    max-height: 400px !important;
    resize: vertical !important;
}

.gr-tab-container {
    border: none !important;
}

.gr-tabs {
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    padding: 1rem;
    background: white;
}
"""


# -------------------------------------------------------------------------
# 8️⃣ Launch Enhanced App
# -------------------------------------------------------------------------
def build_enhanced_ui():
    with gr.Blocks(
        title="StoryCraft AI Studio 🚀", 
        css=custom_css
    ) as demo:
        
        # --- 1. Hero Header ---
        gr.HTML("""
        <div class="hero-header">
            <h1>StoryCraft AI Studio 🚀</h1>
            <p>Unleash the full power of multi-agent AI to create professional stories and visual concepts instantly.</p>
        </div>
        """)
        
        with gr.Row():
            # --- Left Column: Input and Agent List ---
            with gr.Column(scale=2, elem_classes="input-column"):
                
                # Input Section
                idea = gr.Textbox(
                    lines=4,
                    placeholder="✨ Enter your story idea...\nExample: 'A lonely robot on Mars discovers friendship with a curious alien creature while exploring the red planet's ancient ruins'",
                    label="Your Story Idea"
                )
                
                generate_btn = gr.Button(
                    "🚀 Start Full Pipeline Generation", 
                    variant="primary", 
                    scale=1
                )
                
                # Agent List
                gr.HTML("""<div class="agent-list"><h3>Pipeline Agents</h3></div>""")
                gr.HTML("""
                <div class="agent-card">
                    <span class="agent-icon">📋</span>
                    <span class="agent-name">Brief Agent</span>
                    <span class="agent-status">Ready</span>
                </div>
                <div class="agent-card">
                    <span class="agent-icon">✍️</span>
                    <span class="agent-name">Writer Agent</span>
                    <span class="agent-status">Ready</span>
                </div>
                <div class="agent-card">
                    <span class="agent-icon">🎨</span>
                    <span class="agent-name">Visual Agent</span>
                    <span class="agent-status">Ready</span>
                </div>
                <div class="agent-card">
                    <span class="agent-icon">✅</span>
                    <span class="agent-name">Reviewer Agent</span>
                    <span class="agent-status">Ready</span>
                </div>
                <div class="agent-card">
                    <span class="agent-icon">📰</span>
                    <span class="agent-name">Publisher Agent</span>
                    <span class="agent-status">Ready</span>
                </div>
                """)

            # --- Right Column: Progress, Metrics, and Output Tabs ---
            with gr.Column(scale=3, elem_classes="output-column"):
                
                gr.HTML("<h3>Progress Tracker</h3>")
                progress_html = create_progress_tracker()
                
                gr.HTML("<h3>Story Metrics</h3>")
                metrics_html = create_metrics_display()
                
                gr.HTML("<h3>Final Output</h3>")
                
                # Output Tabs
                with gr.Tabs() as tabs:
                    with gr.TabItem("📰 Final Published Story"):
                        published_out = gr.Markdown(label="Published Story", show_label=False)
                    
                    with gr.TabItem("📋 Story Brief (JSON)"):
                        brief_out = gr.JSON(label="Brief", show_label=False)
                    
                    with gr.TabItem("📖 Full Draft"):
                        writer_out = gr.Textbox(
                            label="Story",
                            show_label=False,
                            lines=15,
                            interactive=True,
                            autoscroll=True
                        )

                    
                    with gr.TabItem("🎨 Visual Prompts (JSON)"):
                        visual_out = gr.JSON(label="Visual Prompts", show_label=False)
                    
                    with gr.TabItem("✅ Quality Review (JSON)"):
                        reviewer_out = gr.JSON(label="Review", show_label=False)
        
        # Hidden output for metrics (used for dynamic updates)
        metrics_data = gr.Textbox(visible=False)
        
        # --- Event Handling ---
        generate_btn.click(
            fn=run_pipeline_with_progress,
            inputs=[idea],
            outputs=[
                progress_html, brief_out, writer_out, visual_out, 
                reviewer_out, published_out, metrics_data
            ]
        )
        
        # Update metrics when data changes
        def update_metrics(metrics_str):
            if metrics_str:
                word_count, char_count, read_time, quality_score = metrics_str.split(",")
                # Return the HTML structure populated with live data
                return f"""
                <div class="metrics-container">
                    <div class="metric-card">
                        <div class="metric-value">{word_count}</div>
                        <div class="metric-label">Words</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{char_count}</div>
                        <div class="metric-label">Characters</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{read_time}</div>
                        <div class="metric-label">Reading Time</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{quality_score}</div>
                        <div class="metric-label">Quality Score</div>
                    </div>
                </div>
                """
            return create_metrics_display()
        
        metrics_data.change(
            fn=update_metrics,
            inputs=[metrics_data],
            outputs=[metrics_html]
        )

    return demo


if __name__ == "__main__":
    demo = build_enhanced_ui()
    demo.queue()
    demo.launch(
        show_api=False,
        share=False,
        server_name="127.0.0.1",
        server_port=7860
    )