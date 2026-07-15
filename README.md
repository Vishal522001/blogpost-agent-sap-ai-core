# Multi-Agent AI Blog Generator using SAP AI Core

## Overview

This project is a multi-agent AI application that automatically generates professional technical blog posts from a user-provided topic. It demonstrates how multiple AI agents can collaborate sequentially to produce high-quality content instead of relying on a single Large Language Model (LLM) prompt.

The application is built using SAP AI Core, SAP Generative AI Hub, LiteLLM, and Streamlit, providing an interactive interface for generating blogs with AI-generated illustrations.

---

## Project Workflow

The application follows a sequential multi-agent workflow:

```
User Topic
      │
      ▼
Research Agent
      │
      ▼
Fact Checker
      │
      ▼
Blog Writer
      │
      ▼
Proofreader
      │
      ▼
Image Generator
      │
      ▼
Final Illustrated Blog
```

---

## AI Agents

### Research Agent
Collects structured information about the requested topic and prepares a detailed research summary.

### Fact Checker
Reviews the research output, verifies important claims, and improves factual accuracy before content generation.

### Blog Writer
Generates a complete technical blog using the verified research, including an introduction, detailed sections, and a conclusion.

### Proofreader
Improves grammar, readability, formatting, and writing style to produce a polished final blog.

### Image Generator
Creates image prompts based on the final blog and generates illustrations such as architecture diagrams and section images, which are embedded into the Markdown document.

---

## Technologies Used

- Python
- SAP AI Core
- SAP Generative AI Hub
- LiteLLM
- Streamlit
- Requests
- Pydantic

---

## Features

- Multi-agent AI workflow
- Enterprise AI using SAP AI Core
- Automatic blog generation
- AI-generated illustrations
- Interactive Streamlit web interface
- Markdown export
- Multiple LLM support through SAP Generative AI Hub

---
