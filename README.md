🚀 StoryCraft AI Studio
Multi-Agent Story Generation Engine powered by Groq + LLaMA 8B
<img width="1216" height="832" alt="banner" src="https://github.com/user-attachments/assets/cc5214ff-8c42-451b-a5af-e889c62b340f" />

🌟 Overview

StoryCraft AI Studio is a next-gen multi-agent creative writing system that transforms a simple idea into a fully published story, enriched with visuals, metadata, and quality scoring.

The system uses a parallel multi-runtime architecture, where each agent operates independently, communicating through structured JSON payloads. This enables:

✔ Faster generation
✔ Better modularity
✔ True multi-agent orchestration
✔ Clear diagnostic logs
✔ Professional-grade story outputs

Built using:

🧠 Groq API (Open-Source LLM hosting)

🦙 LLaMA-3.1 8B model

🎨 Gradio UI (Fully customized with CSS gradient theme)

🔄 Agent-to-Agent pipeline with isolated runtimes

🧩 Features
💡 Multi-Agent Architecture

Each agent runs in its own runtime, ensuring true distributed multi-agent behavior:

Agent	Role
📋 Brief Agent	Converts a rough idea into a clean story brief
✍️ Writer Agent	Expands the brief into a structured story
🎨 Visual Agent	Generates visual prompts for illustrations
✅ Reviewer Agent	Applies quality, structure & consistency checks
📰 Publisher Agent	Produces final polished content
⚡ Technical Stack
Component	Technology
Model	Groq LLaMA-3.1 8B (Open Source)
API	OpenAI-compatible Groq API
Frontend	Gradio 4.x (custom styled)
Backend	Python multi-agent orchestrator
Logging	Timestamped pipeline logs
Memory	Local file-based memory stores
🖥️ UI Highlights

✔ Hero gradient header
✔ Multi-step progress tracker
✔ Live metrics (word count, read time, quality score)
✔ JSON & Markdown output tabs
✔ Smooth UI animations & modern card layout
✔ Beautiful agent list display

🔗 Pipeline Flow
graph TD;
    A[User Input: Idea] --> B[📋 Brief Agent];
    B --> C[✍️ Writer Agent];
    C --> D[🎨 Visual Agent];
    B --> D;
    C --> E[✅ Reviewer Agent];
    D --> E;
    E --> F[📰 Publisher Agent → Final Story];

🚀 How It Works
1️⃣ User enters a simple idea

→ “A lonely robot on Mars befriends a tiny alien…”

2️⃣ Agents run independently

Every agent call uses:

A separate Python runtime

Groq LLaMA-8B model

JSON-validated prompt templates

Gradio streaming updates

3️⃣ Pipeline orchestrator coordinates results

Using:

brief_out = brief_agent.run(idea)
writer_out = writer_agent.run(brief_out)
visual_out = visual_agent.run(writer_out)
reviewer_out = reviewer_agent.run({...})
publisher_out = publisher_agent.run({...})

4️⃣ UI updates in real-time

Progress bar changes color

Metrics refresh dynamically

Tabs populate instantly

📦 Project Structure
storycraft/
│── app.py        # Main multi-agent pipeline logic
│── agents              # All agent definitions
│── memories/              # Memory storage
│── logs.txt               # Pipeline logs
│── assets/                # Images (Optional)
│── README.md              # You’re here

🛠️ Setup
1️⃣ Install Dependencies
pip install -r requirements.txt

2️⃣ Add Groq API Key

Create .env:

GROQ_API_KEY=your_key_here

3️⃣ Run App
python orchestrator.py


App runs at:
👉 http://127.0.0.1:7860

📸 Screenshots

You can add screenshots here once UI is running.

🧪 Agent Isolation Logic

Each agent is explicitly decoupled and executed with:

✔ Its own system prompt
✔ Its own runtime context
✔ Sanitized JSON responses
✔ Retry logic with exponential backoff
✔ Error-proof fallback responses

This ensures fault-tolerance even under missing API keys or malformed outputs.

🧠 Why Groq + LLaMA 8B?
🌩️ Groq Advantages

Extreme inference speed

Open-source model compatibility

Fully OpenAI-API compatible

Free-tier friendliness

Production-grade stability

🦙 LLaMA-3.1 8B Advantages

Lightweight yet powerful

Excellent for creative generation

Fast inference

Perfect for multi-agent reasoning

🗺️ Roadmap

 Add image generation agent

 Add agent memory & persona systems

 Add PDF/ebook export

 Add voice narration output

 Make agents asynchronous for speed

🏆 Credits

Built with ❤️ using:

Groq API

LLaMA-3.1 8B

Gradio

Python

🧑‍💻 Contributing

Pull requests welcome!
Please follow the multi-agent coding guidelines inside agents.py.

📜 License

MIT License — Free for all use.
