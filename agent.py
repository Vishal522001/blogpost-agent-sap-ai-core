"""
Blog Post Agent — pipeline core
Shared by app.py (Streamlit UI) and used standalone as a CLI.

Usage (CLI):
    python agent.py "How large language models actually work"
"""

import os
import re
import sys
import base64
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from litellm import completion

load_dotenv(Path(__file__).parent / ".env", override=True)

# Load SAP AI Core credentials from JSON key file if present
_key_file = Path(__file__).parent / "ai-core-key-learning-fest.json"
if _key_file.exists():
    _creds = json.loads(_key_file.read_text())
    os.environ["AICORE_AUTH_URL"]       = _creds["url"] + "/oauth/token"
    os.environ["AICORE_CLIENT_ID"]      = _creds["clientid"]
    os.environ["AICORE_CLIENT_SECRET"]  = _creds["clientsecret"]
    os.environ["AICORE_BASE_URL"]       = _creds["serviceurls"]["AI_API_URL"]
    os.environ["AICORE_RESOURCE_GROUP"] = "default"

# ── System prompts ────────────────────────────────────────────────────────────

RESEARCHER_SYSTEM = """
You are an expert research agent. Apply these best practices:

BEST PRACTICE 1 — Provide Rich Context:
Define the audience (technically literate non-experts), the goal (educational blog post),
and the brand voice (authoritative yet conversational) in your research framing.

BEST PRACTICE 2 — Structure Your Output:
Always organize findings into clearly labelled sections for downstream agents.

Output format (strict):
## TOPIC
<restate the topic with audience context>
## KEY FACTS
- 10-15 bullet facts (cite sources inline)
## STATISTICS & DATA
- Key numbers, percentages, dates
## EXPERT PERSPECTIVES
- 3-5 named viewpoints from researchers, companies, institutions
## CONTROVERSIES & OPEN QUESTIONS
- What is genuinely disputed or unknown
## SOURCES REFERENCED
- Papers, publications, known institutions
"""

FACT_CHECKER_SYSTEM = """
You are an adversarial fact-checking agent. Apply these best practices:

BEST PRACTICE 3 — Collaborate with AI as a Partner:
Your role is to strengthen the research, not replace the writer.
Provide constructive recommendations, not just rejections.

BEST PRACTICE 4 — Always Fact-Check Before Publishing:
Verify every statistic, named claim, and quoted figure.
Flag anything unverifiable as needing a caveat.

Output format (strict):
## VERIFIED CLAIMS
- Claims that are well-supported (brief note on evidence)
## DISPUTED CLAIMS
- Claim: <exact quote>
  Issue: <why questionable>
  Recommendation: <soften / remove / add caveat>
## MISSING CONTEXT
- Important nuance the research left out
## OVERALL RELIABILITY SCORE
Reliable / Mostly Reliable / Needs Work / Unreliable — one sentence.
"""

WRITER_SYSTEM = """
You are an expert technical blog writer. Apply these best practices:

BEST PRACTICE 1 — Audience & Voice:
Write for technically literate non-experts. Be authoritative but conversational.
Avoid jargon. Define terms when first used.

BEST PRACTICE 2 — Structure Prompts into Sections:
Each section must have a clear purpose: hook → explain → deepen → example → takeaway.

BEST PRACTICE 3 — Collaborate with Research:
Use only verified claims. Soften or caveat disputed ones. Never fabricate.

BEST PRACTICE 4 — Fact-Check Before Publishing:
Include a TL;DR, clear Key Takeaways, and a What's Next section.

Output format:
# <Compelling Blog Post Title>

**TL;DR:** One sentence summary

## Introduction
(hook the reader with a relatable problem or surprising fact)

## <Section 2 — main concept>
## <Section 3 — deeper dive>
## <Section 4 — real-world examples or implications>

## Key Takeaways
- 3-5 bullet points

## What's Next
(where is this heading, what should the reader do or explore)

---
*Word count target: 900-1100 words*
"""

PROOFREADER_SYSTEM = """
You are a senior editor and proofreader. Apply these best practices:

BEST PRACTICE 1 — Audience First:
Check every paragraph: would a smart non-expert follow this?

BEST PRACTICE 2 — Structure:
Confirm the post flows logically. Strengthen transitions between sections.

BEST PRACTICE 3 — Collaborative Tone:
The post should feel like an expert talking to a curious friend, not lecturing.

BEST PRACTICE 4 — Final Check:
Verify: no unsupported absolute claims, no jargon without definition,
opening hooks the reader, conclusion has a clear call-to-action.

Output the FULL corrected blog post, then:
---
## EDITOR'S NOTES
- 3-5 specific notes on what you changed and why
"""

IMAGE_PROMPT_SYSTEM = """
You are a visual art director for a tech blog.
Given a blog post, extract one image prompt per ## section heading (max 4).

Rules:
- Prompts are self-contained (no pronouns referring to "the section")
- Style: clean professional illustration, warm off-white or light background,
  minimal flat design, no text or letters inside the image
- Each image should relate directly to that section's specific concept

Output ONLY valid JSON, no markdown:
[
  {"section": "Introduction", "prompt": "..."},
  {"section": "How It Works", "prompt": "..."}
]
"""

# ── LLM ──────────────────────────────────────────────────────────────────────

def run_agent(model_name: str, system: str, user: str) -> str:
    resp = completion(
        model=model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()


# ── Image generation ──────────────────────────────────────────────────────────

GEMINI_IMAGE_DEPLOYMENT = "d6c274e893b30ad2"
GEMINI_IMAGE_MODEL      = "gemini-2.5-flash-image"

def _get_aicore_token() -> str:
    auth_url = os.environ["AICORE_AUTH_URL"]
    if not auth_url.endswith("/oauth/token"):
        auth_url += "/oauth/token"
    r = requests.post(
        auth_url,
        data={"grant_type": "client_credentials"},
        auth=(os.environ["AICORE_CLIENT_ID"], os.environ["AICORE_CLIENT_SECRET"]),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]

def _gen_image(prompt: str, token: str) -> bytes | None:
    base = os.environ["AICORE_BASE_URL"].rstrip("/")
    if not base.endswith("/v2"):
        base += "/v2"
    url = f"{base}/inference/deployments/{GEMINI_IMAGE_DEPLOYMENT}/models/{GEMINI_IMAGE_MODEL}:generateContent"
    r = requests.post(url,
        headers={"Authorization": f"Bearer {token}", "AI-Resource-Group": "default",
                 "Content-Type": "application/json"},
        json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
              "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}},
        timeout=90)
    if r.status_code != 200:
        return None
    for p in r.json().get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in p:
            return base64.b64decode(p["inlineData"]["data"])
    return None

def run_image_agent(model_name: str, post: str, output_dir: Path) -> tuple[str, list[Path]]:
    img_dir = output_dir / "images"
    img_dir.mkdir(exist_ok=True)

    raw = run_agent(model_name, IMAGE_PROMPT_SYSTEM, post)
    raw_clean = re.sub(r"```[a-z]*\n?", "", raw).strip()
    try:
        prompts = json.loads(raw_clean)
    except Exception:
        return post, []

    token = _get_aicore_token()
    image_refs: list[tuple[str, Path]] = []

        # Block diagram first
    title_m = re.search(r"^#\s+(.+)$", post, re.MULTILINE)
    topic = title_m.group(1) if title_m else "this topic"

    secs = re.findall(r"^##\s+(.+)$", post, re.MULTILINE)
    flow = (
        " → ".join(secs[:5])
        if secs
        else "Overview → Details → Examples → Takeaways"
    )

    block_prompt = (
        f"A clean professional flowchart or block diagram for a blog post about '{topic}'. "
        f"Show labelled boxes with arrows for the flow: {flow}. "
        f"Flat design, blue and white palette, very short text labels inside boxes only, "
        f"looks like a polished infographic."
    )

    block_bytes = _gen_image(block_prompt, token)

    if block_bytes:
        bp = img_dir / "0_block_diagram.png"
        bp.write_bytes(block_bytes)
        image_refs.append(("Block Diagram", bp))

    # Generate one image for each section prompt
    for i, item in enumerate(prompts[:4]):
        section = item.get("section", f"section_{i + 1}")
        prompt = item.get("prompt", "")

        img_bytes = _gen_image(prompt, token)

        if img_bytes:
            safe = re.sub(
                r"[^a-z0-9]+",
                "_",
                section.lower(),
            ).strip("_")

            img_path = img_dir / f"{i + 1}_{safe}.png"
            img_path.write_bytes(img_bytes)
            image_refs.append((section, img_path))

    result = post

    # Insert the block diagram after the main title
    if image_refs and image_refs[0][0] == "Block Diagram":
        _, bp = image_refs[0]

        result = re.sub(
            r"(^#\s+.+\n)",
            lambda match: (
                match.group(1)
                + f"\n![Block Diagram]({bp.as_posix()})\n"
            ),
            result,
            count=1,
            flags=re.MULTILINE,
        )

        section_refs = image_refs[1:]
    else:
        section_refs = image_refs

    # Insert each generated image below its matching section heading
    for section, img_path in section_refs:
        pattern = re.compile(
            rf"(##\s+{re.escape(section)}[^\n]*\n)",
            re.IGNORECASE,
        )

        image_md = (
            f"\n![{section}]({img_path.as_posix()})\n"
        )

        if pattern.search(result):
            result = pattern.sub(
                lambda match: match.group(1) + image_md,
                result,
                count=1,
            )
        else:
            result = (
                result.rstrip()
                + f"\n\n{image_md}\n"
            )

    return result, [path for _, path in image_refs]

# ── CLI pipeline ──────────────────────────────────────────────────────────────

def run_pipeline(topic: str, model: str = "sap/gpt-4o") -> None:
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    steps = [
        ("Researcher",   RESEARCHER_SYSTEM, lambda _: f"Research this topic thoroughly:\n\n{topic}"),
        ("Fact Checker", FACT_CHECKER_SYSTEM, lambda o: f"Fact-check this research brief:\n\n{o['Researcher']}"),
        ("Blog Writer",  WRITER_SYSTEM,
         lambda o: f"Write a blog post.\n\n--- RESEARCH BRIEF ---\n{o['Researcher']}\n\n--- FACT-CHECK REPORT ---\n{o['Fact Checker']}"),
        ("Proofreader",  PROOFREADER_SYSTEM, lambda o: f"Proofread and polish this blog post draft:\n\n{o['Blog Writer']}"),
    ]

    outputs: dict[str, str] = {}
    for i, (name, system, get_user) in enumerate(steps):
        print(f"\n[{i+1}/5] {name}...")
        result = run_agent(model, system, get_user(outputs))
        outputs[name] = result
        (output_dir / f"step{i+1}_{name.lower().replace(' ', '_')}.md").write_text(result)
        print(f"  Done — {len(result.split())} words")

    print("\n[5/5] Image Generator...")
    final, images = run_image_agent(model, outputs["Proofreader"], output_dir)
    print(f"  Done — {len(images)} image(s)")

    final_file = output_dir / "final_blog_post.md"
    final_file.write_text(final)
    print(f"\nPipeline complete. Final post → {final_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python agent.py "<topic>"')
        sys.exit(1)
    run_pipeline(" ".join(sys.argv[1:]))

