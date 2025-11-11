# AI Story Studio

Purpose
Building Collaborative Agentic AI Systems for Creative Media. AI Story Studio is a multi-agent system that turns a short idea into an illustrated story via five collaborating agents.

Agents
- Brief Agent: Turns a short idea into a structured brief (JSON) that includes title, themes, characters, setting, tone, and image requirements.
- Writer Agent: Writes the story text based on the brief.
- Visual Agent: Produces detailed image-generation prompts for key scenes.
- Reviewer Agent: Evaluates outputs and returns strict JSON with validation.
- Publisher Agent: Assembles the final published Markdown story with image placeholders.

Stack
- Open-source models via the Groq API (LLaMA-3-8B, Mistral-7B, Phi-3-Mini)
- Python, requests, jsonschema
- Gradio UI for local interaction

Local run
1. Install dependencies:
   pip install -r requirements.txt
2. Set Groq API key:
   export GROQ_API_KEY="your_key"   (Windows PowerShell: $env:GROQ_API_KEY="your_key")
3. Run:
   python app.py
4. Open the local Gradio link printed by the app.

Hugging Face Spaces
- Push this repository to a Space.
- Add a secret named `GROQ_API_KEY` with your key in the Space settings.
- Configure runtime as needed for CPU/GPU.

Example usage
1. Enter a one-line idea: "A young clockmaker finds a pocket watch that rewinds small moments."
2. Agents run: Brief → Writer → Visual → Reviewer → Publisher.
3. Outputs displayed: brief JSON, story text, visual prompts, reviewer JSON, final Markdown.

Notes
- Each agent writes its latest output to `memories/<agent>_mem.json`.
- Logs appended to `logs.txt`.
- Reviewer output is strict JSON validated with jsonschema.
