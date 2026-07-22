# 🤖 DocuCite — Context-Grounded AI Document QA

> **Zero-hallucination, interactive document intelligence engine with inline source page citations and jump-link previews.**

[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Google Gemini API](https://img.shields.io/badge/Google%20Gemini-3.1%20Flash--Lite-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

---

## 🌟 Overview

**DocuCite** is an academic and technical Document QA assistant designed to eliminate AI hallucination by grounding responses strictly within uploaded PDF documents. 

Instead of generating unverified summaries, DocuCite indexes documents page-by-page, dynamically injects exact page citations (`{cite:X}`) into section headings, and provides interactive `🔗` link triggers that pop up a preview of the source PDF page without re-rendering or disrupting user scroll position.

---

## ✨ Key Features

* 📄 **Page-Aware PDF Indexing:** Leverages `pypdf` to extract and structure documents into page-tagged context streams (`--- PAGE X ---`).
* 🔗 **Header-Anchored Page Citations:** Custom prompt constraints force the language model to attach source citations strictly to section titles where topics originate.
* 👁️ **Zero-Shift Source Previews (`@st.dialog`):** Clicking a citation button (`🔗`) opens an embedded, base64-encoded PDF preview jump-linked directly to `#page=X` inside a Streamlit overlay modal.
* ⚡ **Response Caching (`@st.cache_data`):** Heavy PDF text extraction and indexing steps are cached in memory to avoid re-parsing on app re-runs.
* 💡 **Quick Starter Queries:** One-click prompt chips (`Summarize key topics`, `Explain main definitions`, `List important takeaways`) allow users to query documents immediately.
* 📥 **Transcript Export:** Download full Q&A chat transcripts in plain text (`.txt`) format.
* ⏱️ **Automatic Backoff Guard:** Native exception handling that catches API rate-limit errors (HTTP 429) and pauses gracefully before auto-retrying.

---

## 🏗️ System Architecture

┌────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│  Uploaded PDF  │ ───> │ Page-Indexed Extraction │ ───> │  Streamlit Caching      │
└────────────────┘      │    (pypdf / io.BytesIO) │      │   (@st.cache_data)      │
                        └─────────────────────────┘      └─────────────────────────┘
                                                                      │
┌────────────────┐      ┌─────────────────────────┐                   │
│ Citation Modal │ <─── │ Streamlit App Workspace │ <─────────────────┘
│  (@st.dialog)  │      │ (Regex Parsing Engine)  │
└────────────────┘      └─────────────────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │   Google GenAI SDK      │
                        │  (gemini-3.1-flash-lite)│
                        └─────────────────────────┘

---

## 📁 Repository Structure

DocuCite/
├── app.py              # Main Streamlit application & LLM orchestration (~280 lines)
├── styles.css          # External CSS stylesheet for dark-theme styling
├── requirements.txt    # Python dependencies
├── .gitignore          # Git exclusions file
└── README.md           # Repository documentation

---

## ⚙️ Local Installation & Setup

### 1. Prerequisites
* Python 3.10+
* A Google Gemini API Key (Get one at Google AI Studio)

### 2. Clone & Install
git clone https://github.com/your-username/DocuCite.git
cd DocuCite
pip install -r requirements.txt

### 3. Run the Application
Set your GEMINI_API_KEY in environment variables or .streamlit/secrets.toml, then execute:
streamlit run app.py

---

## 🛠️ Tech Stack & Credits

* Frontend: Streamlit
* LLM Engine: Google GenAI SDK (gemini-3.1-flash-lite)
* Document Parser: PyPDF
* Styling: Custom CSS3 & HTML5
* Developer: Anushka Yogendra Joshi (MIT-WPU, Pune)