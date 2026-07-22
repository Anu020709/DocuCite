import base64
import io
import re
import time
from google import genai
from pypdf import PdfReader
import streamlit as st

# Set up webpage title and layout icon
st.set_page_config(
    page_title="DocuCite - Context-Grounded Document QA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)
# --- INITIALIZE THEME STATE ---
if "theme" not in st.session_state:
  st.session_state.theme = "dark"

# Helper function to load external CSS
def load_css(file_name):
  with open(file_name, "r") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css("styles.css")

# --- DYNAMICALLY APPLY THEME ATTRIBUTE ---
st.markdown(
    f"""
    <script>
        var body = window.parent.document.querySelector('.stApp');
        if (body) {{
            body.setAttribute('data-theme', '{st.session_state.theme}');
        }}
    </script>
    """,
    unsafe_allow_html=True,
)

# --- CORE SESSION STATE INITIALIZATION ---
if "chat_history" not in st.session_state:
  st.session_state.chat_history = []

if "extracted_context" not in st.session_state:
  st.session_state.extracted_context = ""

if "attached_filename" not in st.session_state:
  st.session_state.attached_filename = ""

if "total_pages" not in st.session_state:
  st.session_state.total_pages = 0

if "nav_tab" not in st.session_state:
  st.session_state.nav_tab = "💬 Chat Workspace"

if "pending_query" not in st.session_state:
  st.session_state.pending_query = None


# --- CACHED PDF TEXT EXTRACTION ---
@st.cache_data(show_spinner=False)
def extract_text_from_bytes(file_bytes):
  reader = PdfReader(io.BytesIO(file_bytes))
  extracted_text = ""
  for page_num, page in enumerate(reader.pages, start=1):
    text = page.extract_text()
    if text:
      extracted_text += f"\n--- PAGE {page_num} ---\n{text}\n"
  return extracted_text, len(reader.pages)


# --- STREAMLIT OVERLAY DIALOG (FULL MULTI-PAGE CONTINUOUS SCROLL) ---
@st.dialog("📄 Source Document Preview", width="large")
def show_pdf_preview_modal(uploaded_file, page_num):
    st.caption(f"Jumped to Page **{page_num}** in **{st.session_state.attached_filename}** (Scroll for all pages)")
    
    base64_pdf = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
    
    # PDF.js Multi-Page Continuous Canvas Viewer
    pdfjs_viewer = f"""
    <div id="pdf-container" style="width:100%; height:500px; overflow-y:auto; background:#1e212b; padding:15px; border-radius:8px; border:1px solid #2e303d;">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js"></script>
        <div id="canvas-wrapper" style="display:flex; flex-direction:column; align-items:center; gap:15px;"></div>
        <script>
            const url = 'data:application/pdf;base64,{base64_pdf}';
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
            
            pdfjsLib.getDocument(url).promise.then(async (pdf) => {{
                const wrapper = document.getElementById('canvas-wrapper');
                let targetCanvas = null;

                for (let num = 1; num <= pdf.numPages; num++) {{
                    const page = await pdf.getPage(num);
                    const canvas = document.createElement('canvas');
                    canvas.id = 'page-' + num;
                    canvas.style.maxWidth = '100%';
                    canvas.style.height = 'auto';
                    canvas.style.borderRadius = '6px';
                    canvas.style.boxShadow = '0 4px 12px rgba(0,0,0,0.4)';
                    wrapper.appendChild(canvas);

                    const context = canvas.getContext('2d');
                    const viewport = page.getViewport({{ scale: 1.3 }});
                    canvas.height = viewport.height;
                    canvas.width = viewport.width;

                    await page.render({{ canvasContext: context, viewport: viewport }}).promise;

                    if (num === {page_num}) {{
                        targetCanvas = canvas;
                    }}
                }}

                // Smooth scroll to target cited page
                if (targetCanvas) {{
                    targetCanvas.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}
            }}).catch(err => {{
                console.error("PDF.js rendering error:", err);
            }});
        </script>
    </div>
    """
    
    # Render Canvas Component
    st.components.v1.html(pdfjs_viewer, height=540, scrolling=False)
    
    # Backup Download/Open Button
    st.download_button(
        label=f"📥 Download / Open Full Document",
        data=uploaded_file.getvalue(),
        file_name=st.session_state.attached_filename,
        mime="application/pdf",
        use_container_width=True
    )

# --- SIDEBAR (DocuCite Navigation, Export & History) ---
with st.sidebar:
  st.markdown(
      '<div class="sidebar-sticky-header">🤖 <span>DocuCite</span></div>',
      unsafe_allow_html=True,
  )

  st.markdown("### 🗺️ Navigation")
  if st.button(
      "💬 Chat Workspace",
      use_container_width=True,
      type=(
          "secondary"
          if st.session_state.nav_tab != "💬 Chat Workspace"
          else "primary"
      ),
  ):
    st.session_state.nav_tab = "💬 Chat Workspace"
    st.rerun()
  if st.button(
      "📖 About Us",
      use_container_width=True,
      type=(
          "secondary" if st.session_state.nav_tab != "📖 About Us" else "primary"
      ),
  ):
    st.session_state.nav_tab = "📖 About Us"
    st.rerun()
  if st.button(
      "✉️ Contact Me",
      use_container_width=True,
      type=(
          "secondary"
          if st.session_state.nav_tab != "✉️ Contact Me"
          else "primary"
      ),
  ):
    st.session_state.nav_tab = "✉️ Contact Me"
    st.rerun()

  st.markdown("---")

  user_questions = [
      (idx, msg)
      for idx, (role, msg) in enumerate(st.session_state.chat_history)
      if role == "user"
  ]

  if user_questions and st.session_state.nav_tab == "💬 Chat Workspace":
    st.markdown("### 📜 Session History")
    for idx, q in reversed(user_questions):
      preview = q[:28] + "..." if len(q) > 28 else q
      st.markdown(
          f'<a href="#msg-{idx}" target="_self"><button'
          f' class="history-btn">💬 {preview}</button></a>',
          unsafe_allow_html=True,
      )

    st.markdown("---")

    # Download Chat Log Button
    chat_text = "\n\n".join([
        f"{'USER' if role == 'user' else 'DOCUCITE AI'}:\n{text}"
        for role, text in st.session_state.chat_history
    ])
    st.download_button(
        label="📥 Export Chat Log",
        data=chat_text,
        file_name=(
            f"DocuCite_Transcript_{st.session_state.attached_filename}.txt"
        ),
        mime="text/plain",
        use_container_width=True,
    )

    if st.button("Clear History", use_container_width=True):
      st.session_state.chat_history = []
      st.session_state.extracted_context = ""
      st.session_state.attached_filename = ""
      st.session_state.total_pages = 0
      st.session_state.pending_query = None
      st.toast("🧹 Chat history and context cleared!", icon="✨")
      st.rerun()
  elif st.session_state.nav_tab == "💬 Chat Workspace":
    st.caption("Conversations will update here natively.")



# --- PROMINENT RESPONSIVE HEADER BAR ---
st.markdown("""
    <div class="responsive-header-container">
        <div class="responsive-header-title">
            🤖 DocuCite <span class="responsive-header-badge">AI Document QA</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- MAIN WORKSPACE INTERFACE ---
if st.session_state.nav_tab == "💬 Chat Workspace":
  st.write(
      "Upload your document context and ask questions instantly with verified"
      " page citations."
  )

  uploaded_pdf = st.file_uploader(
      "➕ Upload Context Document (PDF)",
      type=["pdf"],
      label_visibility="visible",
  )

  if uploaded_pdf:
    if st.session_state.attached_filename != uploaded_pdf.name:
      with st.spinner("Parsing document framework & caching pages..."):
        file_bytes = uploaded_pdf.getvalue()
        text, pages = extract_text_from_bytes(file_bytes)
        st.session_state.extracted_context = text
        st.session_state.total_pages = pages
        st.session_state.attached_filename = uploaded_pdf.name
        st.toast(f"📄 Successfully indexed {uploaded_pdf.name}!", icon="🎉")

    # Active Document Info Badge
    st.info(
        f"📎 **Active File:** `{st.session_state.attached_filename}` | 📄 **Total"
        f" Pages:** {st.session_state.total_pages}"
    )

    # Suggested Starter Questions (when conversation is fresh)
    if not st.session_state.chat_history:
      st.markdown("##### 💡 Quick Starter Questions:")
      col1, col2, col3 = st.columns(3)
      if col1.button("📌 Summarize key topics", use_container_width=True):
        st.session_state.pending_query = (
            "Provide a comprehensive summary of the key topics in this"
            " document."
        )
        st.rerun()
      if col2.button("🔍 Explain main definitions", use_container_width=True):
        st.session_state.pending_query = (
            "List and explain all key terms and definitions."
        )
        st.rerun()
      if col3.button("📝 List important takeaways", use_container_width=True):
        st.session_state.pending_query = (
            "What are the most important takeaways from this document?"
        )
        st.rerun()

  st.markdown("---")

  # CHAT MESSAGES TIMELINE
  for idx, (role, text) in enumerate(st.session_state.chat_history):
    st.markdown(f'<div id="msg-{idx}"></div>', unsafe_allow_html=True)

    if role == "user":
      st.markdown(
          '<div class="user-msg-container"><div'
          f' class="user-msg-box">{text}</div></div>',
          unsafe_allow_html=True,
      )
    else:
      st.markdown("🤖 **AI Assistant**")

      cleaned_text = re.sub(r"\[Page\s*[\d\s,-]+\]|\(Page\s*[\d\s,-]+\)", "", text)
      parts = re.split(r"(\{cite:\d+\})", cleaned_text)

      for part_idx, part in enumerate(parts):
        cite_match = re.match(r"\{cite:(\d+)\}", part)
        if cite_match:
          page_num = int(cite_match.group(1))
          if st.button(
              "🔗",
              key=f"cite_btn_{idx}_{part_idx}_{page_num}",
              help=f"View Page {page_num}",
          ):
            if uploaded_pdf:
              show_pdf_preview_modal(uploaded_pdf, page_num)
        else:
          if part:
            st.markdown(part, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

# VIEW 2: ABOUT US SECTION
elif st.session_state.nav_tab == "📖 About Us":
  st.markdown("""
        <div class="about-card">
            <h2>📖 About DocuCite</h2>
            <p>Welcome to <strong>DocuCite</strong>—a highly precise, localized RAG (Retrieval-Augmented Generation) engine engineered to turn raw study documents and technical texts into interactive, context-grounded intelligence.</p>
            <p>Built using a lightweight frontend stack paired with advanced foundational language models, this engine processes data streams locally without compromising structural validation or system memory.</p>
            <h3>Core Capabilities:</h3>
            <ul>
                <li><strong>Zero Hallucinations:</strong> Strict engineering limits constrain the agent to respond using only verified ground-truth data.</li>
                <li><strong>Interactive Citations:</strong> On-demand source page buttons trigger overlay modals jump-linked to exact pages.</li>
                <li><strong>Lightweight Footprint:</strong> Native structural design optimized for low-latency calculations.</li>
                <li><strong>Seamless Persistence:</strong> Full anchor-linked workspace indexing panels to trace session continuity seamlessly.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

# VIEW 3: CONTACT ME SECTION
elif st.session_state.nav_tab == "✉️ Contact Me":
  st.markdown("""
        <div class="contact-card">
            <h2>✉️ Connect With Me</h2>
            <p>Have questions about the architectural code pipeline, implementation framework, or want to collaborate on future software developments? Let's connect!</p>
            <hr style="border-color: #2e303d;">
            <p><strong>💻 Developer:</strong> Anushka Yogendra Joshi</p>
            <p><strong>🎓 Institution:</strong> MIT-WPU, Pune</p>
            <p><strong>🛠️ Tech Stack Focus:</strong> Computer Science & Contextual Systems Design</p>
            <p><strong>📬 Email inquiries:</strong> <a class="contact-link" href="mailto:anushka.m.joshi@gmail.com">anushka.m.joshi@gmail.com</a></p>
        </div>
    """, unsafe_allow_html=True)

# --- STEP 7: UNIFIED CHAT INPUT & EXECUTION ENGINE ---
if st.session_state.nav_tab == "💬 Chat Workspace":
  user_input = st.chat_input("Ask a question about your document...")

  # Determine if input comes from chat field OR starter buttons
  active_query = None
  if user_input:
    active_query = user_input
  elif "pending_query" in st.session_state and st.session_state.pending_query:
    active_query = st.session_state.pending_query
    st.session_state.pending_query = None

  if active_query:
    st.session_state.chat_history.append(("user", active_query))

    if st.session_state.extracted_context:
      with st.spinner("Analyzing document metrics & preparing response..."):
        prompt_instructions = f"""
                You are a comprehensive, highly thorough academic FAQ assistant for DocuCite.
                Answer the user's question with DEEP, DETAILED, AND WELL-STRUCTURED EXPLANATIONS based strictly on the ground-truth document context provided below.

                RESPONSE STRUCTURE:
                1. Provide rich, detailed breakdowns with clear numbered/bulleted section headings (e.g., "### 3. Writing User-Defined Functions").
                2. Explain every section thoroughly with definitions, benefits, and code snippets where applicable. Do not shorten explanations.

                STRICT CITATION RULES (HEADER PLACEMENT ONLY):
                1. ONLY place a citation tag DIRECTLY AT THE END OF MAIN SECTION HEADINGS where that topic begins.
                   Example format: "### 3. Writing User-Defined Functions (Section 4.3) {{cite:4}}"
                2. DO NOT put citation tags after regular text lines, sentences, or bullet points.
                3. ALWAYS use the exact tag format {{cite:X}} where X is the single source page number where that topic starts.
                4. NEVER output plain text like "[Page 10]" or "(Page 10, 11)".
                5. If the answer cannot be derived from the context, say: "I cannot find the answer in the provided document."

                ---
                DOCUMENT CONTEXT:
                {st.session_state.extracted_context}
                ---

                USER QUESTION:
                {active_query}
                """

        client = genai.Client()

        try:
          response = client.models.generate_content(
              model="gemini-3.1-flash-lite", contents=prompt_instructions
          )
          ai_response = response.text
        except Exception as e:
          if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            st.toast("⚠️ Rate limit reached. Retrying shortly...", icon="⏱️")
            time.sleep(5)
            try:
              response = client.models.generate_content(
                  model="gemini-3.1-flash-lite", contents=prompt_instructions
              )
              ai_response = response.text
            except Exception:
              ai_response = (
                  "⚠️ The document context is too large for the rate limit"
                  " right now. Please try again in a minute."
              )
          else:
            ai_response = f"⚠️ An error occurred: {str(e)}"
    else:
      ai_response = (
          "⚠️ Please drop a PDF file into the 'Upload Context Document' zone"
          " above before continuing."
      )

    st.session_state.chat_history.append(("assistant", ai_response))
    st.rerun()