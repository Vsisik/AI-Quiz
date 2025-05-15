# streamlit_full_app.py
import json
import requests
import streamlit as st

# URL of your FastAPI backend
BASE_URL = "http://localhost:8000"

if 'quiz' not in st.session_state:
    st.session_state['quiz'] = []
if 'parsed_text' not in st.session_state:
    st.session_state['parsed_text'] = ""

st.set_page_config(page_title="Document AI Quiz", layout="wide")
st.title("📄 Document AI Quiz Generator")

# 1. Upload document
uploaded_file = st.file_uploader(
    "Upload Document (PDF/DOCX/TXT/HTML)",
    type=["pdf", "docx", "txt", "html", "htm"]
)

if uploaded_file:
    with st.spinner("Parsing document..."):
        # Read raw bytes
        data = uploaded_file.read()
        # Send to your parse_document endpoint
        files = {"file": (uploaded_file.name, data)}
        resp = requests.post(f"{BASE_URL}/parse_document", files=files)
    if resp.status_code == 200:
        st.session_state['parsed_text'] = resp.json().get("text", "")
    else:
        st.error(f"❌ Error parsing document: {resp.text}")

# 2. Show extracted text
if st.session_state['parsed_text']:
    st.subheader("Extracted Text")
    st.text_area("", st.session_state['parsed_text'], height=200)

    # 3. Parameters & Generate button
    st.markdown("---")
    st.subheader("Quiz Generation Settings")
    col1, col2, col3 = st.columns(3)
    with col1:
        model = st.text_input("Model", value="gpt-4o-mini")
    with col2:
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.05)
    with col3:
        max_tokens = st.number_input("Max Tokens", min_value=100, max_value=3000, value=1500, step=100)

    if st.button("🧠 Generate Quiz"):
        with st.spinner("Calling AI..."):
            payload = {
                "text": st.session_state['parsed_text'],
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            gen = requests.post(f"{BASE_URL}/generate_quiz", json=payload)
            print(gen)
        if gen.status_code == 200:
            data = gen.json()
            quiz_data = data # data.get("quiz", [])
            print(quiz_data)

            # If the backend returned a string, try parsing it
            if isinstance(quiz_data, str):
                try:
                    quiz = json.loads(quiz_data)
                except json.JSONDecodeError:
                    st.error("❌ Received invalid JSON from AI")
                    st.session_state['quiz'] = []
                else:
                    st.session_state['quiz'] = quiz
            elif isinstance(quiz_data, list):
                st.session_state['quiz'] = quiz_data
            else:
                st.error("❌ Unexpected quiz format from API")
                st.session_state['quiz'] = []
        else:
            st.error(f"❌ Error generating quiz: {gen.text}")

# 4. Render quiz & check answers
if st.session_state['quiz']:
    st.markdown("---")
    st.subheader("📝 Your Quiz")
    answers = {}
    for i, q in enumerate(st.session_state['quiz']):
        st.markdown(f"**{i+1}. {q['question']}**")
        options = [f"{k}: {v}" for k, v in q["choices"].items()]
        answers[i] = st.radio(
            label="Select an answer",
            options=options,
            key=f"q{i}",
            label_visibility="collapsed"
        )
        st.write("")  # spacer

    if st.button("✅ Check Answers"):
        correct_count = 0
        for i, q in enumerate(st.session_state['quiz']):
            selected = answers[i].split(":", 1)[0]
            if selected == q["correct"]:
                st.success(f"Question {i+1}: Correct! ({selected})")
                correct_count += 1
            else:
                st.error(f"Question {i+1}: ❌ You chose {selected}, correct is {q['correct']}.")
        st.markdown(f"### You scored **{correct_count}/{len(st.session_state['quiz'])}**")


# Run Streamlit app when invoked directly
if __name__ == "__main__":
    import subprocess, sys, os

    # Build the command to launch a clean Streamlit process
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        os.path.abspath(__file__),
        "--server.port", "8501",
        "--server.headless", "true"
    ]
    # This will not try to re-instantiate Streamlit in this process
    subprocess.run(cmd)