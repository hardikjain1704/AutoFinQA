---
title: AutoFinQA - Financial Q&A System
emoji: 💼
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# AutoFinQA - Intelligent Financial Q&A System

A dual-mode RAG (Retrieval-Augmented Generation) system for financial document analysis with Simple RAG and Agentic RAG capabilities.

## Features

- **Dual-Mode RAG**: Choose between Simple RAG (fast) or Agentic RAG (reasoning-based)
- **Multi-Format Support**: PDF, CSV, Excel, DOCX, JSON, TXT
- **Source Citations**: Track answers back to specific documents and pages
- **Agent Reasoning**: Visualize step-by-step agent thought process
- **Session Management**: Maintain separate conversation contexts
- **Dark Mode**: Eye-friendly interface with theme toggle

## Tech Stack

- **Backend**: FastAPI, LangChain, MongoDB
- **Frontend**: Vanilla JS, Vite
- **LLM**: Groq (Llama models), Google Embeddings
- **Deployment**: Docker, Nginx

## Usage

1. Upload your financial documents (PDF, CSV, Excel, etc.)
2. Select RAG mode (Simple or Agentic)
3. Ask questions about your documents
4. View answers with source citations

## Environment Variables

Required secrets in Hugging Face Space settings:
- `GROQ_API_KEY`
- `GOOGLE_API_KEY`
- `MONGODB_URI`