#!/usr/bin/env python3
"""
Gradio UI for Graph RAG Resume Agent

This provides an interactive web interface for querying the Graph RAG Resume Agent
and viewing skills, projects, and system health.

Run with: python app_gradio.py
Or deploy to Hugging Face Spaces (auto-launches via Dockerfile)

The app uses direct imports from the knowledge graph - NO external API needed!
The knowledge graph is static data loaded from local files.
"""

import os
import sys
import gradio as gr

# Add app directory to path for direct imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try direct import first (no API needed), fall back to HTTP
try:
    from app.graph.query import GraphQuerier
    from app.agent.resume_agent import ResumeAgent
    DIRECT_MODE = True
    print("✓ Using direct mode - loading knowledge graph from local files")
except ImportError as e:
    # Fall back to HTTP mode
    import httpx
    DIRECT_MODE = False
    API_URL = os.getenv("API_URL", "http://localhost:8000")
    print(f"ℹ Using HTTP mode - connecting to {API_URL}")


def check_health():
    """Check the health status - direct mode loads from local files."""
    if DIRECT_MODE:
        # Direct mode - check local files
        import os
        graph_path = "data/graph/knowledge_graph.json"
        vector_path = "data/embeddings/faiss_index.faiss"
        graph_loaded = os.path.exists(graph_path)
        vector_loaded = os.path.exists(vector_path)
        graph_status = "✅ Loaded" if graph_loaded else "❌ Not Loaded"
        vector_status = "✅ Loaded" if vector_loaded else "❌ Not Loaded"
        return f"""
        ### System Health

        | Component | Status |
        |-----------|--------|
        | Overall | ✅ Running |
        | Knowledge Graph | {graph_status} |
        | Vector Store | {vector_status} |
        """
    else:
        # HTTP mode
        try:
            response = httpx.get(f"{API_URL}/health", timeout=10)
            data = response.json()
            graph_status = "✅ Loaded" if data.get("graph_loaded") else "❌ Not Loaded"
            vector_status = "✅ Loaded" if data.get("vector_store_loaded") else "❌ Not Loaded"
            return f"""
            ### System Health

            | Component | Status |
            |-----------|--------|
            | Overall | ✅ {data.get('status', 'unknown')} |
            | Knowledge Graph | {graph_status} |
            | Vector Store | {vector_status} |
            """
        except Exception as e:
            return f"### System Health\n\n❌ Error: {str(e)}"


def list_skills(min_confidence=0.3):
    """List all skills - direct mode loads from local knowledge graph."""
    if DIRECT_MODE:
        try:
            querier = GraphQuerier()
            all_skills = querier.get_skills()
            # Filter by confidence
            skills = [s for s in all_skills if s.get("confidence", 0) >= min_confidence]
            skills.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            total = len(skills)

            if not skills:
                return f"No skills found with confidence >= {min_confidence}"

            # Create markdown table
            md = f"### Skills ({total} total, confidence ≥ {min_confidence})\n\n"
            md += "| Skill | Category | Confidence | Mentions |\n"
            md += "|-------|----------|------------|----------|\n"

            for skill in skills:
                name = skill.get("name", "Unknown")
                confidence = skill.get("confidence", 0)
                category = skill.get("category", "general")
                mention_count = skill.get("mention_count", 0)
                md += f"| {name} | {category} | {confidence:.2f} | {mention_count} |\n"

            return md
        except Exception as e:
            return f"❌ Error: {str(e)}"
    else:
        # HTTP mode
        try:
            response = httpx.get(f"{API_URL}/skills?min_confidence={min_confidence}", timeout=10)
            data = response.json()
            skills = data.get("skills", [])
            total = data.get("total", 0)

            if not skills:
                return f"No skills found with confidence >= {min_confidence}"

            # Create markdown table
            md = f"### Skills ({total} total, confidence ≥ {min_confidence})\n\n"
            md += "| Skill | Category | Confidence | Mentions |\n"
            md += "|-------|----------|------------|----------|\n"

            for skill in skills:
                name = skill.get("skill", "Unknown")
                confidence = skill.get("confidence", 0)
                category = skill.get("category", "general")
                evidence_count = skill.get("evidence_count", 0)
                md += f"| {name} | {category} | {confidence:.2f} | {evidence_count} |\n"

            return md
        except Exception as e:
            return f"❌ Error: {str(e)}"


def list_projects():
    """List all projects - direct mode loads from local knowledge graph."""
    if DIRECT_MODE:
        try:
            querier = GraphQuerier()
            projects = querier.get_projects()
            total = len(projects)

            if not projects:
                return "No projects found"

            # Create markdown table
            md = f"### Projects ({total} total)\n\n"
            md += "| Name | Platform | URL |\n"
            md += "|------|----------|-----|\n"

            for project in projects[:50]:  # Limit to 50 for display
                name = project.get("name", "Unknown")
                platform = project.get("platform", "unknown")
                url = project.get("url", "")
                url_display = url[:50] + "..." if len(url) > 50 else url
                md += f"| {name} | {platform} | [{url_display}]({url}) |\n"

            if total > 50:
                md += f"\n*Showing first 50 of {total} projects*"

            return md
        except Exception as e:
            return f"❌ Error: {str(e)}"
    else:
        # HTTP mode
        try:
            response = httpx.get(f"{API_URL}/projects", timeout=10)
            data = response.json()
            projects = data.get("projects", [])
            total = data.get("total", 0)

            if not projects:
                return "No projects found"

            # Create markdown table
            md = f"### Projects ({total} total)\n\n"
            md += "| Name | Platform | URL |\n"
            md += "|------|----------|-----|\n"

            for project in projects[:50]:  # Limit to 50 for display
                name = project.get("name", "Unknown")
                platform = project.get("platform", "unknown")
                url = project.get("url", "")
                url_display = url[:50] + "..." if len(url) > 50 else url
                md += f"| {name} | {platform} | [{url_display}]({url}) |\n"

            if total > 50:
                md += f"\n*Showing first 50 of {total} projects*"

            return md
        except Exception as e:
            return f"❌ Error: {str(e)}"


def query_agent(question, top_k=5):
    """Query the resume agent - direct mode uses local ResumeAgent."""
    if not question or not question.strip():
        return "Please enter a question."

    if DIRECT_MODE:
        try:
            agent = ResumeAgent()
            response = agent.query(question=question, top_k=top_k)

            # Format the response
            answer = response.answer
            confidence = response.confidence
            skills = response.skills
            sources = response.sources

            # Build response
            md = f"### Answer\n\n{answer}\n\n"
            md += f"**Confidence:** {confidence:.2f}\n\n"

            # Skills found
            if skills:
                md += "### Skills Found\n\n"
                for skill in skills[:5]:
                    skill_name = skill.get("name", "Unknown")
                    skill_conf = skill.get("confidence", 0)
                    md += f"- {skill_name} (confidence: {skill_conf:.2f})\n"
                md += "\n"

            # Sources
            if sources:
                md += "### Sources\n\n"
                for source in sources[:5]:
                    md += f"- {source}\n"

            return md
        except Exception as e:
            return f"❌ Error: {str(e)}"
    else:
        # HTTP mode
        try:
            response = httpx.post(
                f"{API_URL}/query",
                json={"question": question, "top_k": top_k},
                timeout=60
            )
            data = response.json()

            # Format the response
            answer = data.get("answer", "No answer provided")
            confidence = data.get("confidence", 0)
            skills = data.get("skills", [])
            sources = data.get("sources", [])

            # Build response
            md = f"### Answer\n\n{answer}\n\n"
            md += f"**Confidence:** {confidence:.2f}\n\n"

            # Skills found
            if skills:
                md += "### Skills Found\n\n"
                for skill in skills[:5]:
                    skill_name = skill.get("name", "Unknown")
                    skill_conf = skill.get("confidence", 0)
                    md += f"- {skill_name} (confidence: {skill_conf:.2f})\n"
                md += "\n"

            # Sources
            if sources:
                md += "### Sources\n\n"
                for source in sources[:5]:
                    md += f"- {source}\n"

            return md
        except Exception as e:
            return f"❌ Error: {str(e)}"


def create_demo():
    """Create the Gradio demo interface."""

    with gr.Blocks(title="Graph RAG Resume Agent", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🧠 Graph RAG Resume Agent

        Query your resume knowledge graph to find skills, projects, and experience.
        """)

        with gr.Tabs():
            # Tab 1: Query
            with gr.Tab("🔍 Query Agent"):
                gr.Markdown("Ask questions about your skills and experience")

                with gr.Row():
                    question_input = gr.Textbox(
                        label="Question",
                        placeholder="e.g., What are my Python skills?",
                        lines=2,
                        scale=4
                    )
                    top_k_slider = gr.Slider(
                        minimum=1,
                        maximum=20,
                        value=5,
                        step=1,
                        label="Top K Results",
                        scale=1
                    )

                query_btn = gr.Button("🚀 Query", variant="primary")
                query_output = gr.Markdown(label="Response")

                query_btn.click(
                    fn=query_agent,
                    inputs=[question_input, top_k_slider],
                    outputs=query_output
                )

                # Example questions
                gr.Examples(
                    examples=[
                        ["What are my Python skills?"],
                        ["Which projects use React?"],
                        ["What cloud technologies have I used?"],
                        ["Show me my backend development experience"],
                        ["What are my top 5 skills by confidence?"],
                    ],
                    inputs=question_input
                )

            # Tab 2: Skills
            with gr.Tab("📚 Skills"):
                gr.Markdown("View all extracted skills from your knowledge graph")

                confidence_slider = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.3,
                    step=0.1,
                    label="Minimum Confidence"
                )

                skills_btn = gr.Button("🔄 Refresh Skills", variant="secondary")
                skills_output = gr.Markdown(label="Skills")

                skills_btn.click(
                    fn=list_skills,
                    inputs=[confidence_slider],
                    outputs=skills_output
                )

                # Load skills on tab click
                demo.load(
                    fn=list_skills,
                    inputs=[confidence_slider],
                    outputs=skills_output
                )

            # Tab 3: Projects
            with gr.Tab("📁 Projects"):
                gr.Markdown("View all projects in your knowledge graph")

                projects_btn = gr.Button("🔄 Refresh Projects", variant="secondary")
                projects_output = gr.Markdown(label="Projects")

                projects_btn.click(
                    fn=list_projects,
                    inputs=[],
                    outputs=projects_output
                )

            # Tab 4: Health
            with gr.Tab("🏥 System Health"):
                gr.Markdown("Check the status of the knowledge graph and vector store")

                health_btn = gr.Button("🔄 Check Health", variant="secondary")
                health_output = gr.Markdown(label="Health Status")

                health_btn.click(
                    fn=check_health,
                    inputs=[],
                    outputs=health_output
                )

                # Auto-check health on load
                demo.load(
                    fn=check_health,
                    inputs=[],
                    outputs=health_output
                )

        gr.Markdown("""
        ---
        **Graph RAG Resume Agent** - Built with Knowledge Graph + RAG
        """)

    return demo


if __name__ == "__main__":
    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
