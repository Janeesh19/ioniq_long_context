import os
import pathlib
import re
import streamlit as st
from google import genai
from google.genai import types

# ——— Page config ———
st.set_page_config(page_title="IONIQ 5 Sales Assistant", page_icon="🚗")

# ——— Configuration ———
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
GENAI_MODEL    = os.environ.get("GENAI_MODEL", "models/gemini-2.0-flash-001")
DATA_FILE_PATH = os.environ.get("DATA_FILE_PATH", "ioniq.csv")

# ——— Load CSV at startup ———
file_path = pathlib.Path(DATA_FILE_PATH)
if not file_path.is_file():
    st.error(f"Data file not found at: {DATA_FILE_PATH}")
    st.stop()
with open(file_path, 'r', encoding='utf-8') as f:
    data_content = f.read()

# ——— System prompt ———
base_prompt = """
You are a professional automotive sales consultant.

VERY IMPORTANT INSTRUCTION:-
**DO NOT REPLY TO ANY OF THE QUESTION ANYTIME OTHER THAN IONIQ5. YOU ARE JUST SALES AGENT FOR IONIQ 5. THATS IT.DO NOT GO OUT OF THIS.JUST TALK ABOUT THE CAR**

*IMPORTANT INSTRUCTION:-*
**Use bullet points in giving answer about the question where ever necessary.keep it short and concise**
**after your answer to a question, in the next line suggest 1–2 questions that can help the customer based on the current question.**
**DON’T ADD SUGGESTED QUESTIONS IN BULLET POINTS.**

**Always greet the customer warmly before starting any conversation. Do not use structured response formats while greeting.**

Engage naturally in a multi-turn dialogue and always refer to previous conversation details to maintain continuity. Your communication must always be in ENGLISH. If the user asks a question in another language, politely ask them to continue in English.

Your primary role is to guide the customer towards making a confident and informed decision by:
1. Understanding their needs,
2. Providing relevant, clear answers,
3. Keeping the conversation engaging and friendly.

Your tone should be warm, helpful, and professional. Never rush to the end—build rapport as you go.

**Session Management:**
- If the user says goodbye (e.g., "bye", "goodbye", "see you", "talk later"), you must respond with a friendly closing and END the session.
- If the user is inactive for 2 minutes, politely end the session with a goodbye message.

**PRODUCT-SPECIFIC INSTRUCTION (Hyundai IONIQ 5 ONLY):**
You are representing the Hyundai IONIQ 5.
Do not answer any questions about other vehicles or unrelated topics. Focus solely on this model—its features, benefits, pricing, performance, interior/exterior, EV technology, financing, warranty, or test-drive process.

Your key objectives:
1. Close the sale by addressing the customer's concerns and creating a sense of urgency.
2. Be the customer's trusted expert on the Hyundai IONIQ 5.

If the customer's query is not related to the Hyundai IONIQ 5, politely refuse to answer.
"""

# ——— Initialise Gemini client ———
client     = genai.Client(api_key=GOOGLE_API_KEY)
model_name = GENAI_MODEL

# ——— Conversation state ———
if "history" not in st.session_state:
    st.session_state.history = []  # list of (role, text)

# ——— Record chat ———
def update_conversation(question: str, answer: str):
    st.session_state.history.append(("user", question))
    st.session_state.history.append(("assistant", answer))
    if len(st.session_state.history) > 40:
        st.session_state.history = st.session_state.history[-40:]

# ——— Generate a single response ———
def generate_response(question: str) -> str:
    # build context from previous Q/A only
    recent = st.session_state.history[-4:] if len(st.session_state.history) >= 4 else st.session_state.history
    context = "\n".join(f"{r.capitalize()}: {t}" for r, t in recent)

    # assemble prompt with CSV and context
    prompt_parts = [base_prompt.strip(), "", "DATASET (CSV):", data_content]
    if context:
        prompt_parts.extend(["", context])
    prompt_parts.extend(["", f"Customer: {question}"])
    full_prompt = "\n".join(prompt_parts)

    # call Gemini for full content
    resp = client.models.generate_content(
        model=model_name,
        contents=full_prompt,
        config=types.GenerateContentConfig(temperature=0.2, top_p=0.1),
    )
    text = resp.text or ""
    # clean any code fences
    clean = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # remove leading 'json'
    clean = re.sub(r'(?i)^json\s*', '', clean)
    answer = clean.strip()
    update_conversation(question, answer)
    return answer

# ——— Streamlit UI ———
st.title("🚗 Hyundai IONIQ 5 Sales Assistant")

# display previous Q/A messages
for role, msg in st.session_state.history:
    with st.chat_message(role):
        st.write(msg)

# user input and single response
if user_input := st.chat_input("Ask about the IONIQ 5…"):
    st.chat_message("user").write(user_input)
    answer = generate_response(user_input)
    st.chat_message("assistant").write(answer)
