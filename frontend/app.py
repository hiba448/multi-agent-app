import streamlit as st
import httpx
import os

API_URL = os.getenv("API_URL", "http://backend:8000")

st.set_page_config(
    page_title="Lecture Companion",
    page_icon="📚",
    layout="wide"
)

# --- Session State Initialization ---

if "student_id" not in st.session_state:
    st.session_state.student_id = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "student_name" not in st.session_state:
    st.session_state.student_name = None
if "document_id" not in st.session_state:
    st.session_state.document_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None
if "quiz_index" not in st.session_state:
    st.session_state.quiz_index = 0


# --- Helper functions ---

def lookup_or_create_student(student_name: str):
    """
    FIX #2: Look up an existing student by name without creating a new session.
    Falls back to POST /session/ only to get/create the student record,
    then immediately returns — we do NOT treat the returned session_id as active.
    We use GET /session/student/{id} to let the user pick their session.
    """
    response = httpx.post(
        API_URL + "/session/",
        json={"student_name": student_name},
        timeout=10.0
    )
    return response.json()  # returns student_id, session_id, student_name


def upload_document(file, student_id: int, session_id: int):
    """
    FIX #1: Pass session_id as required by the backend upload endpoint.
    """
    response = httpx.post(
        API_URL + "/upload/",
        files={"file": (file.name, file.getvalue(), file.type)},
        data={
            "student_id": str(student_id),
            "session_id": str(session_id),   # <-- was missing before
        },
        timeout=60.0
    )
    return response.json()


def send_chat(request: str, extra: dict = None):
    payload = {
        "request": request,
        "document_id": st.session_state.document_id,
        "student_id": st.session_state.student_id,
        "session_id": st.session_state.session_id,
        "extra": extra
    }
    response = httpx.post(
        API_URL + "/chat/",
        json=payload,
        timeout=10000.0
    )
    return response.json()


def get_weak_topics():
    response = httpx.get(
        API_URL + "/student/" + str(st.session_state.student_id) + "/weak-topics",
        timeout=10.0
    )
    return response.json()


def get_quiz_results():
    response = httpx.get(
        API_URL + "/student/" + str(st.session_state.student_id) + "/quiz-results",
        timeout=10.0
    )
    return response.json()


def add_message(role: str, content: str, agent_label: str = None):
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "agent_label": agent_label
    })


def get_student_sessions(student_id: int):
    response = httpx.get(
        API_URL + "/session/student/" + str(student_id),
        timeout=10.0
    )
    return response.json()


def create_new_session(student_id: int):
    response = httpx.post(
        API_URL + "/session/student/" + str(student_id) + "/new",
        timeout=10.0
    )
    return response.json()


def load_session_history(session_id: int):
    response = httpx.get(
        API_URL + "/session/" + str(session_id) + "/history",
        timeout=10.0
    )
    return response.json()


def delete_session(session_id: int):
    """FIX #4: Delete a session via the backend."""
    response = httpx.delete(
        API_URL + "/session/" + str(session_id),
        timeout=10.0
    )
    return response.status_code == 200


# --- Login Page ---

def render_login():
    st.title("📚 Lecture Companion")
    st.write("Your intelligent multi-agent study assistant.")
    st.divider()

    with st.form("login_form"):
        name = st.text_input("Enter your name")
        submitted = st.form_submit_button("Continue")

        if submitted and name.strip():
            with st.spinner("Loading..."):
                # FIX #2: We call the endpoint to find/create the student record,
                # but we do NOT activate the session_id it returns. The user will
                # pick (or create) a session on the next screen.
                data = lookup_or_create_student(name.strip())
                st.session_state.student_id = data["student_id"]
                st.session_state.student_name = data["student_name"]
                # Deliberately do NOT set st.session_state.session_id here.
                # That auto-created session will appear in the selector as
                # "Empty session" and the user can choose to use or ignore it.
            st.rerun()


# --- Session Selector Page ---

def render_session_selector():
    st.title("📚 Welcome back, " + st.session_state.student_name)
    st.divider()

    data = get_student_sessions(st.session_state.student_id)
    sessions = data.get("sessions", [])

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Your previous sessions")

        if sessions:
            for s in sessions:
                label = s["created_at"][:16] + " — " + s["preview"]
                btn_col, del_col = st.columns([5, 1])

                with btn_col:
                    if st.button(label, key="session_" + str(s["session_id"])):
                        # FIX #3: Load session and its message history
                        st.session_state.session_id = s["session_id"]
                        history = load_session_history(s["session_id"])
                        st.session_state.messages = [
                            {
                                "role": m["role"],
                                "content": m["content"],
                                "agent_label": m.get("agent_label")
                            }
                            for m in history
                        ]
                        # Restore the document linked to this session
                        doc_response = httpx.get(
                            API_URL + "/session/" + str(s["session_id"]) + "/document",
                            timeout=10.0
                        )
                        doc_data = doc_response.json()
                        st.session_state.document_id = doc_data.get("document_id")
                        st.rerun()

                # FIX #4: Delete button per session
                with del_col:
                    if st.button("🗑️", key="delete_" + str(s["session_id"]),
                                 help="Delete this session"):
                        if delete_session(s["session_id"]):
                            st.success("Session deleted.")
                        else:
                            st.error("Could not delete session.")
                        st.rerun()
        else:
            st.info("No previous sessions found.")

    with col2:
        st.subheader("Start fresh")
        if st.button("New Session", use_container_width=True):
            result = create_new_session(st.session_state.student_id)
            st.session_state.session_id = result["session_id"]
            st.session_state.document_id = None
            st.session_state.messages = []
            st.session_state.current_quiz = None
            st.rerun()

    if st.button("Not you? Logout"):
        st.session_state.clear()
        st.rerun()


# --- Upload Page ---

def render_upload():
    st.header("Upload your lecture")
    st.write("Upload a PDF or PowerPoint file to get started.")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "pptx", "ppt"]
    )

    if uploaded_file:
        if st.button("Process Document"):
            with st.spinner("Parsing and indexing your lecture... this may take a moment."):
                # FIX #1: Pass session_id so the backend can link the document
                result = upload_document(
                    uploaded_file,
                    st.session_state.student_id,
                    st.session_state.session_id,
                )

                if "document_id" in result:
                    st.session_state.document_id = result["document_id"]
                    st.success(
                        "Document processed successfully. " +
                        str(result["chunks_stored"]) + " chunks indexed."
                    )
                    st.rerun()
                else:
                    st.error("Upload failed: " + str(result.get("detail", result)))


# --- Chat Page ---

def render_chat():
    st.header("Chat with your lecture")

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            label = msg.get("agent_label", "agent")
            with st.chat_message("assistant"):
                st.caption("🤖 " + (label.capitalize() + " Agent" if label else "Agent"))
                st.write(msg["content"])

    user_input = st.chat_input("Ask a question, request a summary, or ask for a quiz...")

    if user_input:
        add_message("user", user_input)

        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = send_chat(user_input)

            intent = result.get("intent", "")
            agent = result.get("agent", "agent")

            st.caption("🤖 " + agent.capitalize() + " Agent")

            if intent == "SUMMARIZE":
                render_summary_result(result)
            elif intent == "QUESTION":
                render_question_result(result)
            elif intent == "QUIZ":
                render_quiz_result(result)
            elif intent == "EVALUATE":
                render_evaluate_result(result)
            elif intent == "EXPLAIN":
                render_explain_result(result)
            else:
                st.write(str(result))

            add_message(
                "agent",
                str(result.get("summary") or result.get("answer") or result.get("explanation") or ""),
                agent
            )


def render_summary_result(result: dict):
    st.subheader("Lecture Summary")
    st.write(result.get("summary", ""))

    if result.get("key_concepts"):
        st.subheader("Key Concepts")
        for concept in result["key_concepts"]:
            st.markdown("- " + concept)

    if result.get("definitions"):
        st.subheader("Definitions")
        for term, definition in result["definitions"].items():
            st.markdown("**" + term + "**: " + definition)


def render_question_result(result: dict):
    st.write(result.get("answer", ""))

    if result.get("sources"):
        with st.expander("Sources"):
            for source in result["sources"]:
                st.markdown("- " + source)

    if result.get("web_enriched"):
        st.caption("ℹ️ This answer was enriched with web search results.")


def render_quiz_result(result: dict):
    questions = result.get("questions", [])
    if not questions:
        st.write("No questions could be generated from this lecture.")
        return

    st.session_state.current_quiz = questions
    st.session_state.quiz_index = 0
    st.success(str(len(questions)) + " questions generated. Go to the Quiz tab to answer them.")


def render_evaluate_result(result: dict):
    if result.get("correct"):
        st.success("Correct!")
    else:
        st.error("Incorrect.")

    st.write(result.get("feedback", ""))

    if result.get("weak_topic_detected"):
        st.warning("Weak topic detected: " + result["weak_topic_detected"])


def render_explain_result(result: dict):
    st.write(result.get("explanation", ""))


# --- Quiz Page ---

def render_quiz():
    st.header("Quiz")

    if not st.session_state.current_quiz:
        st.info("No active quiz. Go to the Chat tab and ask for a quiz first.")
        return

    questions = st.session_state.current_quiz
    index = st.session_state.quiz_index

    if index >= len(questions):
        st.success("Quiz completed! Check your progress in the My Progress tab.")
        if st.button("Start over"):
            st.session_state.quiz_index = 0
        return

    question = questions[index]

    st.write("**Question " + str(index + 1) + " of " + str(len(questions)) + "**")
    st.write(question.get("question", ""))
    st.divider()

    options = question.get("options", {})
    choice = st.radio(
        "Select your answer:",
        options=list(options.keys()),
        format_func=lambda k: k + ") " + options[k]
    )

    if st.button("Submit Answer"):
        with st.spinner("Evaluating..."):
            result = send_chat(
                request="Evaluating quiz answer",
                extra={
                    "question": question.get("question", ""),
                    "correct_answer": question.get("answer", "") + ") " + options.get(question.get("answer", ""), ""),
                    "student_answer": choice + ") " + options.get(choice, "")
                }
            )

        if result.get("correct"):
            st.success("Correct!")
        else:
            st.error(
                "Incorrect. The correct answer was: " +
                question.get("answer", "") + ") " +
                options.get(question.get("answer", ""), "")
            )

        st.write(result.get("feedback", ""))

        if result.get("weak_topic_detected"):
            st.warning("Weak topic detected: " + result["weak_topic_detected"])

        st.session_state.quiz_index += 1

        if st.button("Next Question"):
            st.rerun()


# --- Progress Page ---

def render_progress():
    st.header("My Progress")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Weak Topics")
        topics = get_weak_topics()
        if topics:
            for topic in topics:
                st.markdown("- " + topic["topic"])
        else:
            st.info("No weak topics detected yet.")

    with col2:
        st.subheader("Quiz History")
        results = get_quiz_results()
        if results:
            total = len(results)
            correct = sum(1 for r in results if r["is_correct"])
            st.metric("Total Answered", total)
            st.metric("Correct", correct)
            st.metric("Score", str(round((correct / total) * 100)) + "%")

            with st.expander("See all results"):
                for r in results:
                    icon = "✅" if r["is_correct"] else "❌"
                    st.markdown(icon + " " + r["question"][:80])
        else:
            st.info("No quiz results yet.")


# --- Main App ---

def main():
    if not st.session_state.student_id:
        render_login()
        return

    if not st.session_state.session_id:
        render_session_selector()
        return

    if not st.session_state.document_id:
        st.sidebar.write("👤 " + st.session_state.student_name)
        if st.sidebar.button("Back to sessions"):
            st.session_state.session_id = None
            st.session_state.messages = []
            st.rerun()
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()
        render_upload()
        return

    st.sidebar.write("👤 " + st.session_state.student_name)
    st.sidebar.write("📄 Document loaded")
    if st.sidebar.button("Back to sessions"):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.rerun()
    if st.sidebar.button("Upload new document"):
        st.session_state.document_id = None
        st.session_state.messages = []
        st.session_state.current_quiz = None
        st.rerun()
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📝 Quiz", "📊 My Progress"])

    with tab1:
        render_chat()
    with tab2:
        render_quiz()
    with tab3:
        render_progress()


if __name__ == "__main__":
    main()