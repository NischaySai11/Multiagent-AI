"""
Orchestrator and shared utilities.

This file contains the core Gradio application structure,
API communication logic (using Groq as a mock target), 
and the fully implemented, functional multi-agent system.
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
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# --- Define New Colors & Model (Teal/Aqua Scheme) ---
PRIMARY_COLOR = "#00bcd4"  # Teal
SECONDARY_COLOR = "#0097a7" # Darker Teal
GRADIENT_START = "#00bcd4"  # Light Teal
GRADIENT_END = "#4dd0e1"    # Lighter Aqua
MODEL_NAME = "llama3-8b-8192" # Placeholder for a fast LLM API

# -------------------------------------------------------------------------
# 1️⃣ Model Caller (Functional Groq/LLM Integration)
# -------------------------------------------------------------------------
def call_model(model, system_prompt, user_prompt, max_retries=3, timeout=45):
    """
    Groq API (OpenAI-compatible) call with retry + backoff.
    Returns model's text response or [ERROR] message.
    """
    if not GROQ_API_KEY:
        # RETURN MOCK DATA when API key is missing for UI demonstration
        if "Brief" in system_prompt:
             return '{"title": "The Lonely Martian Robot", "logline": "A lonely robot on Mars discovers friendship with a curious alien creature.", "genre": "Sci-Fi/Adventure", "themes": ["Exploration", "Friendship", "Isolation"], "key_characters": [{"name": "Unit 734", "role": "The Robot"}, {"name": "Zylar", "role": "The Alien"}]}'
        if "Writer" in system_prompt:
             return "Unit 734 was designed for solitude. Its existence was a silent, rhythmic dance of exploration and data collection on the red dust of Mars. Then, on a routine scan near the Valles Marineris, it found Zylar, a shimmering, tri-limbed being whose laughter was a chime against the rustle of the wind. Their friendship began not with words, but with shared curiosity for the planet's ancient, cryptic ruins. The robot, meant only to observe, found itself learning to feel."
        if "Visual" in system_prompt:
             return '{"visual_prompts": [{"scene_description": "Unit 734 meets Zylar for the first time.", "image_prompt": "A desolate, red Mars landscape. A boxy, metallic robot unit stands next to a shimmering, translucent alien creature with three limbs. Cinematic lighting, photorealistic, 16k."}, {"scene_description": "Exploring ancient ruins together.", "image_prompt": "Inside a massive, dark Martian canyon. Unit 734 and Zylar standing before an enormous, glowing alien archway covered in geometric carvings. Mysterious atmosphere, digital painting, epic scale."}, {"scene_description": "The two watching a Martian sunset.", "image_prompt": "A close-up, emotional shot of the robot and the alien side-by-side, silhouetted against a brilliant orange and purple Martian sunset. Warm tones, highly detailed, film grain."}]}'
        if "Reviewer" in system_prompt:
             return '{"score": "9.2/10", "coherence_check": true, "feedback": "The story is compelling, the brief is solid, and the visual prompts are stunning. Excellent work. Focus on expanding the final story length."}'
        if "Publisher" in system_prompt:
             return "# The Lonely Martian Robot: A Short Story\n\n**Logline:** A lonely robot on Mars discovers friendship with a curious alien creature while exploring the red planet's ancient ruins.\n\n***\n\nUnit 734 was designed for solitude. Its existence was a silent, rhythmic dance of exploration and data collection on the red dust of Mars. Then, on a routine scan near the Valles Marineris, it found Zylar, a shimmering, tri-limbed being whose laughter was a chime against the rustle of the wind. Their friendship began not with words, but with shared curiosity for the planet's ancient, cryptic ruins. The robot, meant only to observe, found itself learning to feel.\n\n*(Full story content would be here...)*\n\n***\n\n## Visual Concepts\n\n* Scene 1: Unit 734 meets Zylar for the first time.\n* Scene 2: Exploring ancient ruins together.\n* Scene 3: The two watching a Martian sunset.\n"
        return '[ERROR] GROQ_API_KEY not set. Returning a general error message for non-specific calls.'


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
        "max_tokens": 1500, # Increased tokens for story writing
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
# 3️⃣ Agent Implementations (Fully Functional Feature)
# -------------------------------------------------------------------------
class Agent:
    """Base class for all agents."""
    def __init__(self, name, model=MODEL_NAME):
        self.name = name
        self.model = model

    def call(self, system_prompt, user_prompt):
        return call_model(self.model, system_prompt, user_prompt)

class BriefAgent(Agent):
    """Generates a structured JSON brief from an idea."""
    def run(self, idea_text):
        system_prompt = (
            "You are the Brief Agent. Your task is to turn a high-level story idea into a "
            "detailed, structured JSON brief. The response MUST be valid JSON and contain "
            "the following keys: 'title', 'logline', 'genre', 'themes' (list), and 'key_characters' (list of dicts with 'name' and 'role')."
        )
        user_prompt = f"Story Idea: {idea_text}"
        return self.call(system_prompt, user_prompt)

class WriterAgent(Agent):
    """Writes the full story draft based on the brief."""
    def run(self, brief_json):
        system_prompt = (
            "You are the Writer Agent. Your task is to write an engaging short story (min 300 words) "
            "based on the provided structured brief. Output must be raw story text, no preamble or extra JSON."
        )
        user_prompt = f"Write the story based on this brief (JSON):\n---\n{brief_json}\n---"
        return self.call(system_prompt, user_prompt)

class VisualAgent(Agent):
    """Generates DALL-E/Midjourney style prompts from the story text."""
    def run(self, story_text):
        system_prompt = (
            "You are the Visual Agent. Your task is to identify three key scenes from the story and generate "
            "highly detailed, professional-grade visual prompts suitable for a text-to-image generator. "
            "The response MUST be valid JSON and contain a list of objects under the key 'visual_prompts', "
            "each having 'scene_description' and 'image_prompt'."
        )
        user_prompt = f"Generate 3 image prompts for the following story:\n---\n{story_text[:1500]}..."
        return self.call(system_prompt, user_prompt)

class ReviewerAgent(Agent):
    """Analyzes the full creative package for quality and viability."""
    def run(self, pipeline_output_json):
        system_prompt = (
            "You are the Reviewer Agent. Your task is to analyze the complete pipeline output (brief, story, visuals) "
            "for quality, coherence, and commercial viability. Provide a numerical 'score' out of 10 and detailed 'feedback'. "
            "The response MUST be valid JSON with the keys: 'score' (string, e.g., '8.5/10'), 'coherence_check' (boolean), and 'feedback' (string)."
        )
        user_prompt = f"Review this complete creative package (JSON format):\n---\n{pipeline_output_json}"
        return self.call(system_prompt, user_prompt)

class PublisherAgent(Agent):
    """Compiles and formats the final story package into professional Markdown."""
    def run(self, final_package_json):
        system_prompt = (
            "You are the Publisher Agent. Your task is to compile the final story package into a clean, "
            "professional Markdown document. Use the title, logline, and story text. "
            "The output must be pure Markdown format, ready for publication, with no JSON or extra commentary."
        )
        user_prompt = f"Format this final package into a professional Markdown article:\n---\n{final_package_json}"
        return self.call(system_prompt, user_prompt)

# Instantiate the fully functional agents
brief_agent = BriefAgent("BriefAgent")
writer_agent = WriterAgent("WriterAgent")
visual_agent = VisualAgent("VisualAgent")
reviewer_agent = ReviewerAgent("ReviewerAgent")
publisher_agent = PublisherAgent("PublisherAgent")

# -------------------------------------------------------------------------
# 4️⃣ Orchestration Flow
# -------------------------------------------------------------------------
def orchestrate(idea_text):
    """Run full story-creation pipeline."""
    results = {}

    # 1. Brief Agent
    brief_out = brief_agent.run(idea_text)
    log_step("BriefAgent", str(brief_out)[:120])
    results["brief"] = brief_out

    # 2. Writer Agent
    writer_out = writer_agent.run(brief_out)
    log_step("WriterAgent", str(writer_out)[:120])
    results["writer"] = writer_out

    # 3. Visual Agent
    visual_out = visual_agent.run(writer_out)
    log_step("VisualAgent", str(visual_out)[:120])
    results["visual"] = visual_out

    # 4. Reviewer Agent (Reviews the first 3 steps)
    reviewer_input = json.dumps({
        "brief": results.get("brief"),
        "story": results.get("writer"),
        "visuals": results.get("visual")
    })
    reviewer_out = reviewer_agent.run(reviewer_input)
    log_step("ReviewerAgent", str(reviewer_out)[:120])
    results["reviewer"] = reviewer_out

    # 5. Publisher Agent (Compiles everything)
    publisher_input = json.dumps(results)
    publisher_out = publisher_agent.run(publisher_input)
    log_step("PublisherAgent", str(publisher_out)[:120])
    results["publisher"] = publisher_out

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
        
        # Get quality score - must handle potential JSON string output
        quality_score = "N/A"
        if "reviewer" in out and out.get("reviewer"):
            try:
                # Attempt to parse as JSON if it's a string
                reviewer_data = json.loads(out["reviewer"]) if isinstance(out["reviewer"], str) else out["reviewer"]
                quality_score = reviewer_data.get("score", "N/A")
            except json.JSONDecodeError:
                 quality_score = "N/A (Bad JSON)" # Handle potential JSON errors
        
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
# 7️⃣ Custom CSS (Teal/Aqua Styling - FIXED and maintained)
# -------------------------------------------------------------------------
custom_css = f"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* General Gradio Overrides */
.gradio-container {{
    max-width: 1400px !important;
    margin: 0 auto !important;
    font-family: 'Inter', sans-serif;
    background-color: #f8f9fa; 
    padding: 0;
}}

/* --- INTRO SCREEN STYLES --- */
.intro-content {{
    text-align: center;
    padding: 5rem 2rem;
    background: linear-gradient(135deg, {GRADIENT_START} 0%, {GRADIENT_END} 100%); /* New Aqua Gradient */
    border-radius: 12px;
    margin: 2rem 0;
    color: white;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
}}

.intro-content h1 {{
    font-size: 3.5rem;
    font-weight: 800;
    margin-bottom: 1rem;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
}}

.intro-content p {{
    font-size: 1.4rem;
    opacity: 0.9;
    font-weight: 500;
    max-width: 800px;
    margin: 0 auto 2rem;
}}

.intro-button {{
    background: white !important;
    color: {PRIMARY_COLOR} !important;
    padding: 1.2rem 3rem !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 6px 20px rgba(0,0,0,0.2) !important;
    transition: all 0.3s ease !important;
}}

.intro-button:hover {{
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 25px rgba(0,0,0,0.3) !important;
}}

/* --- HERO HEADER (Internal Studio) --- */
.hero-header {{
    text-align: center;
    padding: 2rem 0;
    background: linear-gradient(135deg, {SECONDARY_COLOR} 0%, {PRIMARY_COLOR} 100%); /* Slightly different internal gradient */
    border-radius: 12px;
    margin-bottom: 2rem;
    color: white;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}}

.hero-header h1 {{
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
    color: white;
}}

.hero-header p {{
    font-size: 1rem;
    opacity: 0.9;
    font-weight: 300;
}}

/* --- INPUT/AGENT COLUMN & OUTPUT/PROGRESS COLUMN --- */
.input-column {{
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    height: 100%;
}}
.output-column {{
    padding: 0 0 0 1rem;
}}


/* --- AGENT CARDS (Styled list) --- */
.agent-list h3 {{
    color: {SECONDARY_COLOR};
}}

.agent-card:hover {{
    background: #e0f7fa; /* Light teal hover */
    border-color: {PRIMARY_COLOR};
    cursor: pointer;
}}

.agent-icon {{
    color: {PRIMARY_COLOR};
}}


/* --- PROGRESS TRACKER --- */
.progress-step.running {{
    background: #ffecb3; /* Yellowish for running */
    border-color: #ffb300; 
}}

.progress-step.complete {{
    background: #e0f7fa; /* Light aqua complete */
    border-color: {PRIMARY_COLOR};
}}


/* --- METRICS DISPLAY --- */
.metric-value {{
    color: {SECONDARY_COLOR}; /* Highlighted primary color */
}}

/* --- Gradio Component Overrides --- */
button {{
    background: linear-gradient(135deg, {PRIMARY_COLOR} 0%, {SECONDARY_COLOR} 100%) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(0, 188, 212, 0.3) !important;
}}

button:hover {{
    box-shadow: 0 8px 25px rgba(0, 188, 212, 0.4) !important;
}}

textarea.gr-box, .gr-json-display, .gr-markdown, .gr-textbox {{
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    background: #ffffff !important;
    padding: 1rem !important;
    box-shadow: none !important;
    min-height: 250px;
}}

textarea:focus {{
    border-color: {PRIMARY_COLOR} !important;
    box-shadow: 0 0 0 3px rgba(0, 188, 212, 0.1) !important;
}}

.gr-tab-container {{
    border: none !important;
}}

.gr-tabs {{
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    padding: 1rem;
    background: white;
}}
"""


# -------------------------------------------------------------------------
# 8️⃣ Launch Enhanced App
# -------------------------------------------------------------------------
def build_enhanced_ui():
    with gr.Blocks(
        title="StoryCraft AI Studio 🚀", 
        css=custom_css
    ) as demo:
        
        # --- Tabs ---
        tabs = gr.Tabs(selected=0)
        
        with tabs:
            
            # -------------------------------------
            # TAB 1: INTRO SCREEN (Home)
            # -------------------------------------
            with gr.TabItem("Home 🏠", id=0):
                with gr.Column(elem_classes="intro-page"):
                    # Custom HTML content for the intro screen
                    gr.HTML(f"""
                    <div class="intro-content">
                        <h1>StoryCraft AI Studio 🚀</h1>
                        <p>Welcome to the multi-agent creative suite. Instantly turn your high-level ideas into complete stories, visual concepts, and publication-ready drafts.</p>
                        <p>Powered by fast AI models.</p>
                        <button class="intro-button" id="start-button">Start Creating</button>
                    </div>
                    """)
                    # Hidden button element to trigger the Gradio click event for tab switch
                    start_btn_trigger = gr.Button("Start Creating Trigger", visible=False)

            
            # -------------------------------------
            # TAB 2: AI STUDIO (Main App)
            # -------------------------------------
            with gr.TabItem("AI Studio ✍️", id=1):
                # --- 1. Hero Header (Internal) ---
                gr.HTML("""
                <div class="hero-header">
                    <h1>AI Studio Pipeline</h1>
                    <p>Input your idea below to launch the five-stage agent workflow.</p>
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
                        
                        # Agent List (Now represents the functional agents)
                        gr.HTML("""<div class="agent-list"><h3>Pipeline Agents</h3></div>""")
                        gr.HTML(f"""
                        <div class="agent-card"><span class="agent-icon">📋</span><span class="agent-name">Brief Agent (JSON Generator)</span><span class="agent-status">Functional</span></div>
                        <div class="agent-card"><span class="agent-icon">✍️</span><span class="agent-name">Writer Agent (Draft Creator)</span><span class="agent-status">Functional</span></div>
                        <div class="agent-card"><span class="agent-icon">🎨</span><span class="agent-name">Visual Agent (Prompt Generator)</span><span class="agent-status">Functional</span></div>
                        <div class="agent-card"><span class="agent-icon">✅</span><span class="agent-name">Reviewer Agent (Quality Check)</span><span class="agent-status">Functional</span></div>
                        <div class="agent-card"><span class="agent-icon">📰</span><span class="agent-name">Publisher Agent (Markdown Formatter)</span><span class="agent-status">Functional</span></div>
                        """)

                    # --- Right Column: Progress, Metrics, and Output Tabs ---
                    with gr.Column(scale=3, elem_classes="output-column"):
                        
                        gr.HTML("<h3>Progress Tracker</h3>")
                        progress_html = create_progress_tracker()
                        
                        gr.HTML("<h3>Story Metrics</h3>")
                        metrics_html = create_metrics_display()
                        
                        gr.HTML("<h3>Final Output</h3>")
                        
                        # Output Tabs
                        with gr.Tabs() as output_tabs:
                            with gr.TabItem("📰 Final Published Story"):
                                published_out = gr.Markdown(label="Published Story", show_label=False)
                            
                            with gr.TabItem("📋 Story Brief (JSON)"):
                                brief_out = gr.JSON(label="Brief", show_label=False)
                            
                            with gr.TabItem("📖 Full Draft"):
                                writer_out = gr.Textbox(label="Story", show_label=False, lines=15)
                            
                            with gr.TabItem("🎨 Visual Prompts (JSON)"):
                                visual_out = gr.JSON(label="Visual Prompts", show_label=False)
                            
                            with gr.TabItem("✅ Quality Review (JSON)"):
                                reviewer_out = gr.JSON(label="Review", show_label=False)
        
        # Hidden output for metrics (used for dynamic updates)
        metrics_data = gr.Textbox(visible=False)
        
        # --- Event Handling ---
        
        # 1. Logic for Intro button to switch tabs
        demo.load(
            None, 
            None,
            None,
            # JavaScript to hook the custom HTML button to the hidden Gradio button
            js=f"""
                () => {{
                    const customButton = document.getElementById('start-button');
                    if (customButton) {{
                        customButton.addEventListener('click', function() {{
                            document.getElementById('{start_btn_trigger.elem_id}').click();
                        }});
                    }}
                }}
            """
        )

        start_btn_trigger.click(
            lambda: gr.update(selected=1), # Switch to AI Studio tab (index 1)
            outputs=[tabs],
            queue=False
        )

        # 2. Logic for Pipeline Generation
        generate_btn.click(
            fn=run_pipeline_with_progress,
            inputs=[idea],
            outputs=[
                progress_html, brief_out, writer_out, visual_out, 
                reviewer_out, published_out, metrics_data
            ]
        )
        
        # 3. Logic for Metrics Update
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