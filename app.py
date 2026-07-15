"""
Blog Post Agent — Streamlit UI
Imports the pipeline from agent.py and adds the web interface.
"""

import streamlit as st
import base64
import time
from pathlib import Path

from agent import (
    RESEARCHER_SYSTEM,
    FACT_CHECKER_SYSTEM,
    WRITER_SYSTEM,
    PROOFREADER_SYSTEM,
    run_agent,
    run_image_agent,
)

AGENT_META = [
    ("🔍 Researcher",      "Building research brief..."),
    ("✅ Fact Checker",    "Checking claims adversarially..."),
    ("✍️ Blog Writer",     "Writing the draft post..."),
    ("🔤 Proofreader",     "Polishing tone and clarity..."),
    ("🖼️ Image Generator", "Generating section images..."),
]

st.set_page_config(
    page_title="Blog Post Agent",
    page_icon="✍️",
    layout="wide",
)

st.markdown("""
<style>
    .agent-card {
        background: #f8f9fb;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #6c63ff;
    }
    .agent-card.done  { border-left-color: #22c55e; background: #f0fdf4; }
    .agent-card.error { border-left-color: #ef4444; background: #fff5f5; }
    .agent-title { font-size: 1rem; font-weight: 600; color: #1e293b; }
    .agent-meta  { font-size: 0.78rem; color: #64748b; margin-top: 4px; }
    .final-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 24px;
        margin-top: 8px;
        color: #1e293b;
    }
    .final-box img {
        max-width: 420px;
        width: 100%;
        border-radius: 8px;
        margin: 16px 0;
        border: 1px solid #e2e8f0;
        display: block;
    }
    div[data-testid="stTabs"] button { font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ Settings")
    model = st.selectbox("Model", ["sap/gpt-4o", "sap/gpt-4.1-nano", "sap/gpt-5-mini"], index=0)
    st.markdown("---")
    st.markdown("**Pipeline**")
    st.markdown("1. 🔍 Researcher")
    st.markdown("2. ✅ Fact Checker")
    st.markdown("3. ✍️ Blog Writer")
    st.markdown("4. 🔤 Proofreader")
    st.markdown("5. 🖼️ Image Generator")
    st.markdown("---")
    st.caption("Powered by SAP AI Core · Generative AI Hub")

def _embed_images(text: str) -> str:
    import re
    def replacer(m: re.Match) -> str:
        try:
            data = base64.b64encode(Path(m.group(2)).read_bytes()).decode()
            return (f'<img src="data:image/png;base64,{data}" alt="{m.group(1)}" '
                    f'style="max-width:420px;width:100%;border-radius:8px;'
                    f'margin:16px 0;border:1px solid #334155;display:block">')
        except Exception:
            return ""
    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replacer, text)

st.title("✍️ Blog Post Agent")
st.caption("Enter a topic and let 5 AI agents research, fact-check, write, polish, and illustrate a blog post.")

topic = st.text_input(
    "Topic",
    placeholder="e.g. How large language models actually work",
    label_visibility="collapsed",
)

run_btn = st.button("🚀 Generate Blog Post", type="primary", disabled=not topic.strip())

if run_btn and topic.strip():
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    st.markdown("---")
    st.subheader("Pipeline Progress")

    placeholders = [st.empty() for _ in AGENT_META]

    outputs: dict[str, str] = {}
    generated_images: list[Path] = []
    start_total = time.time()
    error_occurred = False

    text_steps = [
        ("Researcher",   RESEARCHER_SYSTEM,
         lambda: f"Research this topic thoroughly:\n\n{topic}"),
        ("Fact Checker", FACT_CHECKER_SYSTEM,
         lambda: f"Fact-check this research brief:\n\n{outputs['Researcher']}"),
        ("Blog Writer",  WRITER_SYSTEM,
         lambda: (f"Write a blog post.\n\n--- RESEARCH BRIEF ---\n{outputs['Researcher']}\n\n"
                  f"--- FACT-CHECK REPORT ---\n{outputs['Fact Checker']}")),
        ("Proofreader",  PROOFREADER_SYSTEM,
         lambda: f"Proofread and polish this blog post draft:\n\n{outputs['Blog Writer']}"),
    ]

    for i, (name, system, get_user) in enumerate(text_steps):
        emoji, desc = AGENT_META[i]
        placeholders[i].markdown(f"""
<div class="agent-card">
  <div class="agent-title">{emoji} <span style="color:#f59e0b">⟳ running...</span></div>
  <div class="agent-meta">{desc}</div>
</div>""", unsafe_allow_html=True)

        t0 = time.time()
        try:
            result  = run_agent(model, system, get_user())
            elapsed = round(time.time() - t0, 1)
            outputs[name] = result
            fname = output_dir / f"step{i+1}_{name.lower().replace(' ', '_')}.md"
            fname.write_text(result)
            placeholders[i].markdown(f"""
<div class="agent-card done">
  <div class="agent-title">{emoji} <span style="color:#22c55e">✓ done</span></div>
  <div class="agent-meta">{elapsed}s · {len(result.split())} words · saved → {fname}</div>
</div>""", unsafe_allow_html=True)
        except Exception as e:
            placeholders[i].markdown(f"""
<div class="agent-card error">
  <div class="agent-title">{emoji} <span style="color:#ef4444">✗ failed</span></div>
  <div class="agent-meta">{str(e)[:120]}</div>
</div>""", unsafe_allow_html=True)
            error_occurred = True
            break

    if not error_occurred:
        emoji, desc = AGENT_META[4]
        placeholders[4].markdown(f"""
<div class="agent-card">
  <div class="agent-title">{emoji} <span style="color:#f59e0b">⟳ running...</span></div>
  <div class="agent-meta">{desc}</div>
</div>""", unsafe_allow_html=True)

        t0 = time.time()
        try:
            final_with_images, generated_images = run_image_agent(
                model, outputs["Proofreader"], output_dir)
            elapsed = round(time.time() - t0, 1)
            (output_dir / "step5_image_generator.md").write_text(final_with_images)
            placeholders[4].markdown(f"""
<div class="agent-card done">
  <div class="agent-title">{emoji} <span style="color:#22c55e">✓ done</span></div>
  <div class="agent-meta">{elapsed}s · {len(generated_images)} image(s) generated</div>
</div>""", unsafe_allow_html=True)
        except Exception as e:
            placeholders[4].markdown(f"""
<div class="agent-card error">
  <div class="agent-title">{emoji} <span style="color:#ef4444">✗ failed</span></div>
  <div class="agent-meta">{str(e)[:120]}</div>
</div>""", unsafe_allow_html=True)
            final_with_images = outputs.get("Proofreader", "")

        total = round(time.time() - start_total, 1)
        final_file = output_dir / "final_blog_post.md"
        final_file.write_text(final_with_images)

        st.markdown("---")
        st.success(f"✅ Pipeline complete in {total}s · {len(generated_images)} image(s) · saved to output/final_blog_post.md")

        tab_final, tab_images, tab_research, tab_factcheck, tab_draft = st.tabs([
            "📄 Final Post", "🖼️ Images", "🔍 Research", "✅ Fact Check", "✍️ Draft"
        ])

        with tab_final:
            st.markdown('<div class="final-box">', unsafe_allow_html=True)
            st.markdown(_embed_images(final_with_images), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.download_button(
                "⬇️ Download Final Post",
                data=final_with_images,
                file_name="blog_post.md",
                mime="text/markdown",
            )

        with tab_images:
            if generated_images:
                cols = st.columns(2)
                for idx, img_path in enumerate(generated_images):
                    with cols[idx % 2]:
                        st.image(str(img_path),
                                 caption=img_path.stem.replace("_", " ").title(),
                                 width=360)
            else:
                st.info("No images were generated.")

        with tab_research:
            st.markdown(outputs.get("Researcher", ""))

        with tab_factcheck:
            st.markdown(outputs.get("Fact Checker", ""))

        with tab_draft:
            st.markdown(outputs.get("Blog Writer", ""))