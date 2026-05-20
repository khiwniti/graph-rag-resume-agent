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
import json
import base64
import io
import gradio as gr
from pathlib import Path

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
            skills = [s for s in all_skills if s.get("confidence", 0) >= min_confidence]
            skills.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            total = len(skills)

            if not skills:
                return f"No skills found with confidence >= {min_confidence}"

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
        try:
            response = httpx.get(f"{API_URL}/skills?min_confidence={min_confidence}", timeout=10)
            data = response.json()
            skills = data.get("skills", [])
            total = data.get("total", 0)

            if not skills:
                return f"No skills found with confidence >= {min_confidence}"

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

            md = f"### Projects ({total} total)\n\n"
            md += "| Name | Platform | URL |\n"
            md += "|------|----------|-----|\n"

            for project in projects[:50]:
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
        try:
            response = httpx.get(f"{API_URL}/projects", timeout=10)
            data = response.json()
            projects = data.get("projects", [])
            total = data.get("total", 0)

            if not projects:
                return "No projects found"

            md = f"### Projects ({total} total)\n\n"
            md += "| Name | Platform | URL |\n"
            md += "|------|----------|-----|\n"

            for project in projects[:50]:
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

            answer = response.answer
            confidence = response.confidence
            skills = response.skills
            sources = response.sources

            md = f"### Answer\n\n{answer}\n\n"
            md += f"**Confidence:** {confidence:.2f}\n\n"

            if skills:
                md += "### Skills Found\n\n"
                for skill in skills[:5]:
                    skill_name = skill.get("name", "Unknown")
                    skill_conf = skill.get("confidence", 0)
                    md += f"- {skill_name} (confidence: {skill_conf:.2f})\n"
                md += "\n"

            if sources:
                md += "### Sources\n\n"
                for source in sources[:5]:
                    md += f"- {source}\n"

            return md
        except Exception as e:
            return f"❌ Error: {str(e)}"
    else:
        try:
            response = httpx.post(
                f"{API_URL}/query",
                json={"question": question, "top_k": top_k},
                timeout=60
            )
            data = response.json()

            answer = data.get("answer", "No answer provided")
            confidence = data.get("confidence", 0)
            skills = data.get("skills", [])
            sources = data.get("sources", [])

            md = f"### Answer\n\n{answer}\n\n"
            md += f"**Confidence:** {confidence:.2f}\n\n"

            if skills:
                md += "### Skills Found\n\n"
                for skill in skills[:5]:
                    skill_name = skill.get("name", "Unknown")
                    skill_conf = skill.get("confidence", 0)
                    md += f"- {skill_name} (confidence: {skill_conf:.2f})\n"
                md += "\n"

            if sources:
                md += "### Sources\n\n"
                for source in sources[:5]:
                    md += f"- {source}\n"

            return md
        except Exception as e:
            return f"❌ Error: {str(e)}"


def view_graph(filter_type="all", min_confidence=0.0):
    """Visualize the knowledge graph with filtering options."""
    try:
        graph_path = Path("data/graph/knowledge_graph.json")
        if not graph_path.exists():
            return None, "❌ Graph file not found. Run metadata extraction first."

        with open(graph_path, "r") as f:
            graph_data = json.load(f)

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        # Filter nodes by type
        if filter_type != "all":
            filtered_nodes = [n for n in nodes if n.get("type") == filter_type]
            node_ids = {n.get("id") for n in filtered_nodes}
            filtered_edges = [e for e in edges if e.get("from") in node_ids and e.get("to") in node_ids]
        else:
            filtered_nodes = nodes[:50]
            node_ids = {n.get("id") for n in filtered_nodes}
            filtered_edges = [e for e in edges if e.get("from") in node_ids and e.get("to") in node_ids]

        import networkx as nx
        import matplotlib.pyplot as plt

        G = nx.DiGraph()

        type_colors = {
            "person": "#FF6B6B",
            "project": "#4ECDC4",
            "skill": "#45B7D1",
            "domain": "#FFA07A",
            "tech": "#98D8C8",
            "platform": "#F7DC6F"
        }

        for node in filtered_nodes:
            n_type = node.get("type", "unknown")
            node_id = node.get("id", "")
            node_name = node.get("properties", {}).get("name", node_id)
            G.add_node(node_id, label=node_name, type=n_type, color=type_colors.get(n_type, "#CCCCCC"))

        for edge in filtered_edges[:200]:
            G.add_edge(edge.get("from", ""), edge.get("to", ""), label=edge.get("label", ""))

        plt.figure(figsize=(12, 10))
        pos = nx.spring_layout(G, k=2, iterations=50)

        for draw_type in type_colors.keys():
            type_nodes = [n for n, attr in G.nodes(data="type") if attr == draw_type]
            if type_nodes:
                nx.draw_networkx_nodes(G, pos, nodelist=type_nodes,
                                     node_color=type_colors.get(draw_type, "#CCCCCC"),
                                     node_size=800, alpha=0.8)

        nx.draw_networkx_edges(G, pos, edge_color="#888888", arrows=True, arrowsize=20, alpha=0.6)

        labels = {node: attr.get("label", node) for node, attr in G.nodes(data=True)}
        nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight="bold")

        graph_title = filter_type.title() if filter_type != "all" else "Overview"
        plt.title(f"Knowledge Graph - {graph_title} ({len(filtered_nodes)} nodes)", fontsize=14)
        plt.axis("off")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        plt.close()

        stats = f"""### Graph Statistics
- **Total Nodes:** {len(filtered_nodes)}
- **Total Edges:** {len(filtered_edges)}
- **Node Types:** {len(set(n.get('type') for n in filtered_nodes))}

### Node Type Distribution
"""
        type_counts = {}
        for node in filtered_nodes:
            t = node.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        for t, count in sorted(type_counts.items()):
            stats += f"- {t}: {count}\n"

        return buf, stats

    except Exception as e:
        import traceback
        error_msg = f"❌ Error: {str(e)}\n\n```\n{traceback.format_exc()}\n```"
        return None, error_msg


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

                demo.load(
                    fn=list_skills,
                    inputs=[confidence_slider],
                    outputs=skills_output
                )

            # Tab 3: Graph View
            with gr.Tab("🕸️ Graph View"):
                gr.Markdown("Visualize your knowledge graph structure")

                with gr.Row():
                    graph_type = gr.Dropdown(
                        choices=["all", "person", "project", "skill", "domain", "tech", "platform"],
                        value="all",
                        label="Node Type Filter"
                    )
                    confidence_slider = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        value=0.0,
                        step=0.1,
                        label="Min Confidence"
                    )

                graph_btn = gr.Button("🔄 Generate Graph View", variant="primary")
                graph_output = gr.Image(label="Knowledge Graph Visualization")
                graph_stats = gr.Markdown(label="Statistics")

                graph_btn.click(
                    fn=view_graph,
                    inputs=[graph_type, confidence_slider],
                    outputs=[graph_output, graph_stats]
                )

                demo.load(
                    fn=view_graph,
                    inputs=[graph_type, confidence_slider],
                    outputs=[graph_output, graph_stats]
                )

            # Tab 4: Projects
            with gr.Tab("📁 Projects"):
                gr.Markdown("View all projects in your knowledge graph")

                projects_btn = gr.Button("🔄 Refresh Projects", variant="secondary")
                projects_output = gr.Markdown(label="Projects")

                projects_btn.click(
                    fn=list_projects,
                    inputs=[],
                    outputs=projects_output
                )

            # Tab 5: Health
            with gr.Tab("🏥 System Health"):
                gr.Markdown("Check the status of the knowledge graph and vector store")

                health_btn = gr.Button("🔄 Check Health", variant="secondary")
                health_output = gr.Markdown(label="Health Status")

                health_btn.click(
                    fn=check_health,
                    inputs=[],
                    outputs=health_output
                )

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
