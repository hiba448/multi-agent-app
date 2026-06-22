import os
import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://backend:8000")

st.set_page_config(
    page_title="Lecture Companion",
    page_icon="📚",
    layout="wide"
)


# -------------------------------------------------------------------
# Session state initialization
# -------------------------------------------------------------------
DEFAULT_STATE = {
    "student_id": None,
    "student_name": None,
    "username": None,
    "email": None,

    "subject_id": None,
    "subject_name": None,

    "session_id": None,
    "discussion_title": None,
    "document_id": None,

    "messages": [],

    "current_quiz": None,
    "quiz_index": 0,
    "quiz_answers": [],
    "quiz_saved": False,
    "quiz_focus": "general lecture content",
    "quiz_attempt_type": "general_quiz",
    "last_quiz_analysis": None,
}


for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# -------------------------------------------------------------------
# Generic API helpers
# -------------------------------------------------------------------
def api_get(path: str, timeout: float = 30.0):
    response = httpx.get(
        API_URL + path,
        timeout=httpx.Timeout(timeout, connect=30.0)
    )
    return response


def api_post(path: str, json=None, data=None, files=None, timeout: float = 60.0):
    response = httpx.post(
        API_URL + path,
        json=json,
        data=data,
        files=files,
        timeout=httpx.Timeout(timeout, connect=30.0)
    )
    return response


def api_delete(path: str, timeout: float = 30.0):
    response = httpx.delete(
        API_URL + path,
        timeout=httpx.Timeout(timeout, connect=30.0)
    )
    return response


# -------------------------------------------------------------------
# Auth helpers
# -------------------------------------------------------------------
def login_user(username_or_email: str, password: str):
    response = api_post(
        "/auth/login",
        json={
            "username_or_email": username_or_email,
            "password": password
        },
        timeout=60.0
    )
    return response


def register_user(name: str, username: str, email: str, password: str):
    response = api_post(
        "/auth/register",
        json={
            "name": name,
            "username": username,
            "email": email,
            "password": password
        },
        timeout=60.0
    )
    return response


def set_logged_in_user(data: dict):
    st.session_state.student_id = data["student_id"]
    st.session_state.student_name = data["name"]
    st.session_state.username = data.get("username")
    st.session_state.email = data.get("email")


def logout():
    for key, value in DEFAULT_STATE.items():
        st.session_state[key] = value
    st.rerun()


# -------------------------------------------------------------------
# Subject helpers
# -------------------------------------------------------------------
def get_subjects():
    response = api_get(
        f"/subject/student/{st.session_state.student_id}",
        timeout=30.0
    )
    return response


def create_subject(name: str, description: str = ""):
    response = api_post(
        "/subject/",
        json={
            "student_id": st.session_state.student_id,
            "name": name,
            "description": description
        },
        timeout=60.0
    )
    return response


def delete_subject(subject_id: int):
    response = api_delete(
        f"/subject/{subject_id}",
        timeout=60.0
    )
    return response


def reset_current_workspace():
    st.session_state.session_id = None
    st.session_state.discussion_title = None
    st.session_state.document_id = None
    st.session_state.messages = []

    st.session_state.current_quiz = None
    st.session_state.quiz_index = 0
    st.session_state.quiz_answers = []
    st.session_state.quiz_saved = False
    st.session_state.quiz_focus = "general lecture content"
    st.session_state.quiz_attempt_type = "general_quiz"
    st.session_state.last_quiz_analysis = None


def open_subject(subject: dict):
    st.session_state.subject_id = subject["id"]
    st.session_state.subject_name = subject["name"]

    reset_current_workspace()

    st.rerun()


def back_to_subjects():
    st.session_state.subject_id = None
    st.session_state.subject_name = None

    reset_current_workspace()

    st.rerun()


# -------------------------------------------------------------------
# Discussion/session helpers
# -------------------------------------------------------------------
def get_subject_sessions():
    response = api_get(
        f"/session/subject/{st.session_state.subject_id}",
        timeout=30.0
    )
    return response


def create_discussion(title: str = ""):
    response = api_post(
        "/session/",
        json={
            "student_id": st.session_state.student_id,
            "subject_id": st.session_state.subject_id,
            "title": title if title else None
        },
        timeout=60.0
    )
    return response


def delete_discussion(session_id: int):
    response = api_delete(
        f"/session/{session_id}",
        timeout=60.0
    )
    return response


def load_session_history(session_id: int):
    response = api_get(
        f"/session/{session_id}/history",
        timeout=30.0
    )
    return response


def get_session_document(session_id: int):
    response = api_get(
        f"/session/{session_id}/document",
        timeout=30.0
    )
    return response


def open_discussion(session_data: dict):
    st.session_state.session_id = session_data["session_id"]
    st.session_state.document_id = session_data.get("document_id")

    title = session_data.get("title")
    if title:
        st.session_state.discussion_title = title
    else:
        st.session_state.discussion_title = f"Discussion #{session_data['session_id']}"

    history_response = load_session_history(st.session_state.session_id)

    if history_response.status_code == 200:
        st.session_state.messages = history_response.json()
    else:
        st.session_state.messages = []

    if not st.session_state.document_id:
        doc_response = get_session_document(st.session_state.session_id)
        if doc_response.status_code == 200:
            st.session_state.document_id = doc_response.json().get("document_id")

    st.session_state.current_quiz = None
    st.session_state.quiz_index = 0
    st.session_state.quiz_answers = []
    st.session_state.quiz_saved = False
    st.session_state.quiz_focus = "general lecture content"
    st.session_state.quiz_attempt_type = "general_quiz"
    st.session_state.last_quiz_analysis = None

    st.rerun()


# -------------------------------------------------------------------
# Upload/chat/progress helpers
# -------------------------------------------------------------------
def upload_document(file):
    response = api_post(
        "/upload/",
        files={
            "file": (
                file.name,
                file.getvalue(),
                file.type
            )
        },
        data={
            "student_id": str(st.session_state.student_id),
            "subject_id": str(st.session_state.subject_id),
            "session_id": str(st.session_state.session_id)
        },
        timeout=300.0
    )
    return response


def send_chat(request: str, extra: dict = None):
    response = api_post(
        "/chat/",
        json={
            "request": request,
            "document_id": st.session_state.document_id,
            "student_id": st.session_state.student_id,
            "subject_id": st.session_state.subject_id,
            "session_id": st.session_state.session_id,
            "extra": extra
        },
        timeout=900.0
    )
    return response


def get_subject_weak_topics():
    response = api_get(
        f"/student/{st.session_state.student_id}/subject/{st.session_state.subject_id}/weak-topics",
        timeout=30.0
    )
    return response


def get_subject_quiz_results():
    response = api_get(
        f"/student/{st.session_state.student_id}/subject/{st.session_state.subject_id}/quiz-results",
        timeout=30.0
    )
    return response


def analyze_full_quiz_attempt(
    discussion_title: str,
    quiz_focus: str,
    correct_count: int,
    total_questions: int,
    answers: list,
    attempt_type: str = "general_quiz"
):
    response = api_post(
        f"/student/{st.session_state.student_id}/subject/{st.session_state.subject_id}/quiz-attempt/analyze",
        json={
            "discussion_title": discussion_title,
            "quiz_focus": quiz_focus,
            "attempt_type": attempt_type,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "answers": answers
        },
        timeout=900.0
    )
    return response


def get_subject_topic_progress():
    response = api_get(
        f"/student/{st.session_state.student_id}/subject/{st.session_state.subject_id}/topic-progress",
        timeout=30.0
    )
    return response


def get_subject_documents():
    response = api_get(
        f"/student/{st.session_state.student_id}/subject/{st.session_state.subject_id}/documents",
        timeout=30.0
    )
    return response


def add_local_message(role: str, content: str, agent_label: str = None):
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "agent_label": agent_label
    })


def start_weak_topic_practice(topic: str):
    """
    Prepare a targeted quiz for one weak topic.
    The actual quiz generation happens in the Quiz tab.
    """
    st.session_state.quiz_focus = topic
    st.session_state.quiz_attempt_type = "weak_topic_quiz"

    st.session_state.current_quiz = None
    st.session_state.quiz_index = 0
    st.session_state.quiz_answers = []
    st.session_state.quiz_saved = False
    st.session_state.last_quiz_analysis = None

    st.success(
        f"Practice mode prepared for: {topic}. "
        "Go to the Quiz tab and click Generate quiz."
    )


# -------------------------------------------------------------------
# Render auth page
# -------------------------------------------------------------------
def render_auth_page():
    st.title("📚 Lecture Companion")
    st.write("Your intelligent multi-agent study assistant.")
    st.divider()

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        st.subheader("Login")

        username_or_email = st.text_input(
            "Username or email",
            key="login_username_or_email"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button("Login", type="primary"):
            if not username_or_email or not password:
                st.warning("Please enter your username/email and password.")
                return

            with st.spinner("Logging in..."):
                response = login_user(username_or_email, password)

            if response.status_code == 200:
                set_logged_in_user(response.json())
                st.success("Logged in successfully.")
                st.rerun()
            else:
                try:
                    detail = response.json().get("detail", "Login failed.")
                except Exception:
                    detail = "Login failed."
                st.error(detail)

    with tab_register:
        st.subheader("Create account")

        name = st.text_input("Full name", key="register_name")
        username = st.text_input("Username", key="register_username")
        email = st.text_input("Email", key="register_email")
        password = st.text_input(
            "Password",
            type="password",
            key="register_password"
        )

        if st.button("Register", type="primary"):
            if not name or not username or not email or not password:
                st.warning("Please fill in all fields.")
                return

            with st.spinner("Creating account..."):
                response = register_user(name, username, email, password)

            if response.status_code == 200:
                set_logged_in_user(response.json())
                st.success("Account created successfully.")
                st.rerun()
            else:
                try:
                    detail = response.json().get("detail", "Registration failed.")
                except Exception:
                    detail = "Registration failed."
                st.error(detail)


# -------------------------------------------------------------------
# Render sidebar
# -------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.title("📚 Lecture Companion")

        if st.session_state.student_name:
            st.write(f"👤 **{st.session_state.student_name}**")

        if st.session_state.subject_name:
            st.write(f"📘 Subject: **{st.session_state.subject_name}**")

        if st.session_state.session_id:
            if st.session_state.discussion_title:
                st.write(f"💬 Discussion: **{st.session_state.discussion_title}**")
            else:
                st.write(f"💬 Discussion ID: `{st.session_state.session_id}`")

        if st.session_state.document_id:
            st.write(f"📄 Document ID: `{st.session_state.document_id}`")

        st.divider()

        if st.session_state.subject_id:
            if st.button("⬅ Back to subjects"):
                back_to_subjects()

        if st.button("Logout"):
            logout()


# -------------------------------------------------------------------
# Render subjects dashboard
# -------------------------------------------------------------------
def render_subjects_dashboard():
    render_sidebar()

    st.title("Subjects Dashboard")
    st.write("Create or open a subject to start studying.")

    st.divider()

    with st.expander("➕ Add new subject", expanded=False):
        subject_name = st.text_input("Subject name")
        subject_description = st.text_area("Description", height=80)

        if st.button("Create subject", type="primary"):
            if not subject_name.strip():
                st.warning("Subject name cannot be empty.")
            else:
                with st.spinner("Creating subject..."):
                    response = create_subject(
                        subject_name.strip(),
                        subject_description.strip()
                    )

                if response.status_code == 200:
                    st.success("Subject created.")
                    st.rerun()
                else:
                    try:
                        detail = response.json().get("detail", "Could not create subject.")
                    except Exception:
                        detail = "Could not create subject."
                    st.error(detail)

    response = get_subjects()

    if response.status_code != 200:
        st.error("Could not load subjects.")
        return

    subjects = response.json()

    if not subjects:
        st.info("No subjects yet. Create your first subject above.")
        return

    st.subheader("Your subjects")

    for subject in subjects:
        with st.container(border=True):
            col1, col2, col3 = st.columns([5, 2, 2])

            with col1:
                st.markdown(f"### 📘 {subject['name']}")
                if subject.get("description"):
                    st.write(subject["description"])
                st.caption(f"Created at: {subject['created_at']}")

            with col2:
                if st.button(
                    "Open",
                    key=f"open_subject_{subject['id']}",
                    type="primary"
                ):
                    open_subject(subject)

            with col3:
                if st.button(
                    "Delete",
                    key=f"delete_subject_{subject['id']}"
                ):
                    delete_response = delete_subject(subject["id"])

                    if delete_response.status_code == 200:
                        st.success("Subject deleted.")
                        st.rerun()
                    else:
                        try:
                            detail = delete_response.json().get("detail", "Could not delete subject.")
                        except Exception:
                            detail = "Could not delete subject."
                        st.error(detail)


# -------------------------------------------------------------------
# Render discussions tab
# -------------------------------------------------------------------
def render_discussions_tab():
    st.subheader("Discussions")
    st.write("Create or open a discussion inside this subject.")

    with st.expander("➕ Create new discussion", expanded=False):
        title = st.text_input(
            "Discussion title",
            placeholder="Example: Chapter 1"
        )

        if st.button("Create discussion", type="primary"):
            clean_title = title.strip()

            if not clean_title:
                st.warning("Please enter a discussion title.")
                return

            response = create_discussion(clean_title)

            if response.status_code == 200:
                data = response.json()
                st.success("Discussion created.")

                open_discussion({
                    "session_id": data["session_id"],
                    "document_id": data.get("document_id"),
                    "title": data.get("title") or clean_title
                })
            else:
                try:
                    detail = response.json().get("detail", "Could not create discussion.")
                except Exception:
                    detail = "Could not create discussion."
                st.error(detail)

    response = get_subject_sessions()

    if response.status_code != 200:
        st.error("Could not load discussions.")
        return

    sessions = response.json().get("sessions", [])

    if not sessions:
        st.info("No discussions yet. Create one above.")
        return

    for discussion in sessions:
        with st.container(border=True):
            col1, col2, col3 = st.columns([5, 2, 2])

            with col1:
                title = discussion.get("title") or f"Discussion #{discussion['session_id']}"
                st.markdown(f"### 💬 {title}")
                st.write(discussion.get("preview", "Empty discussion"))
                st.caption(f"Created at: {discussion['created_at']}")

                if discussion.get("document_id"):
                    st.caption(f"Document ID: {discussion['document_id']}")
                else:
                    st.caption("No document uploaded yet.")

            with col2:
                if st.button(
                    "Open",
                    key=f"open_discussion_{discussion['session_id']}",
                    type="primary"
                ):
                    open_discussion(discussion)

            with col3:
                if st.button(
                    "Delete",
                    key=f"delete_discussion_{discussion['session_id']}"
                ):
                    delete_response = delete_discussion(discussion["session_id"])

                    if delete_response.status_code == 200:
                        st.success("Discussion deleted.")
                        st.rerun()
                    else:
                        try:
                            detail = delete_response.json().get(
                                "detail",
                                "Could not delete discussion."
                            )
                        except Exception:
                            detail = "Could not delete discussion."
                        st.error(detail)


# -------------------------------------------------------------------
# Render upload tab
# -------------------------------------------------------------------
def render_upload_tab():
    st.subheader("Upload lecture document")

    if not st.session_state.session_id:
        st.info("Please create or open a discussion first.")
        return

    if st.session_state.discussion_title:
        st.caption(f"Current discussion: {st.session_state.discussion_title}")

    st.write("Upload a PDF or PowerPoint file for this discussion.")

    uploaded_file = st.file_uploader(
        "Choose a PDF or PowerPoint file",
        type=["pdf", "pptx", "ppt"]
    )

    if uploaded_file and st.button("Upload and process", type="primary"):
        with st.spinner("Uploading, validating subject relevance, and processing document..."):
            response = upload_document(uploaded_file)

        if response.status_code == 200:
            data = response.json()
            st.session_state.document_id = data["document_id"]

            st.success("File uploaded and processed successfully.")

            validation = data.get("subject_validation")
            if validation:
                with st.expander("Subject validation result"):
                    st.write(f"Relevant: **{validation.get('relevant')}**")
                    st.write(f"Confidence: **{validation.get('confidence')}**")
                    st.write(validation.get("reason", ""))

            st.json(data)

        else:
            try:
                detail = response.json().get("detail", "Upload failed.")
            except Exception:
                detail = "Upload failed."

            if isinstance(detail, dict):
                st.error(detail.get("message", "Upload failed."))

                validation = detail.get("validation")
                if validation:
                    with st.expander("Why was this document rejected?"):
                        st.write(f"Relevant: **{validation.get('relevant')}**")
                        st.write(f"Confidence: **{validation.get('confidence')}**")
                        st.write(validation.get("reason", ""))
            else:
                st.error(detail)


# -------------------------------------------------------------------
# Result renderers
# -------------------------------------------------------------------
def render_agent_result(result: dict):
    intent = result.get("intent")

    if intent == "SUMMARIZE":
        st.subheader("Lecture Summary")
        st.write(result.get("summary", ""))

        concepts = result.get("key_concepts", [])
        if concepts:
            st.subheader("Key Concepts")
            for concept in concepts:
                st.write(f"- {concept}")

        definitions = result.get("definitions", {})
        if definitions:
            st.subheader("Definitions")
            st.write(definitions)

    elif intent == "QUESTION":
        st.write(result.get("answer", ""))

        sources = result.get("sources", [])
        if sources:
            with st.expander("Sources"):
                st.write(sources)

    elif intent == "QUIZ":
        questions = result.get("questions", [])

        if not questions:
            st.warning("No quiz questions could be generated.")
            return

        st.session_state.current_quiz = questions
        st.session_state.quiz_index = 0
        st.session_state.quiz_answers = []
        st.session_state.quiz_saved = False
        st.session_state.last_quiz_analysis = None

        quiz_plan = result.get("quiz_plan")
        if quiz_plan:
            st.session_state.quiz_focus = quiz_plan.get(
                "quiz_focus",
                st.session_state.quiz_focus
            )

        st.success(f"{len(questions)} quiz questions generated. Go to the Quiz tab.")

    elif intent == "EVALUATE":
        if result.get("correct"):
            st.success("Correct!")
        else:
            st.error("Incorrect.")

        st.write(result.get("feedback", ""))

    elif intent == "EXPLAIN":
        st.write(result.get("explanation", ""))

    else:
        st.write(result)


def build_display_text(result: dict) -> str:
    intent = result.get("intent")

    if intent == "SUMMARIZE":
        return result.get("summary", "")

    if intent == "QUESTION":
        return result.get("answer", "")

    if intent == "QUIZ":
        questions = result.get("questions", [])
        return f"{len(questions)} questions generated."

    if intent == "EVALUATE":
        return result.get("feedback", "")

    if intent == "EXPLAIN":
        return result.get("explanation", "")

    return str(result)


# -------------------------------------------------------------------
# Render chat tab
# -------------------------------------------------------------------
def render_chat_tab():
    if st.session_state.discussion_title:
        st.subheader(f"Chat — {st.session_state.discussion_title}")
    else:
        st.subheader("Chat with your lecture")

    if not st.session_state.session_id:
        st.info("Please create or open a discussion first.")
        return

    if not st.session_state.document_id:
        st.info("Please upload a document before chatting.")
        return

    for message in st.session_state.messages:
        role = message.get("role", "agent")

        if role == "user":
            with st.chat_message("user"):
                st.write(message.get("content", ""))
        else:
            with st.chat_message("assistant"):
                agent_label = message.get("agent_label")
                if agent_label:
                    st.caption(f"Agent: {agent_label}")
                st.write(message.get("content", ""))

    user_input = st.chat_input(
        "Ask a question, request a summary, or ask for a quiz..."
    )

    if user_input:
        add_local_message("user", user_input)

        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = send_chat(user_input)

            if response.status_code == 200:
                result = response.json()
                render_agent_result(result)

                display_text = build_display_text(result)
                add_local_message(
                    "agent",
                    display_text,
                    result.get("agent", "orchestrator")
                )
            else:
                try:
                    detail = response.json().get("detail", "Chat failed.")
                except Exception:
                    detail = "Chat failed."
                st.error(detail)


# -------------------------------------------------------------------
# Render quiz tab
# -------------------------------------------------------------------
def render_quiz_tab():
    st.subheader("Quiz")

    if st.session_state.discussion_title:
        st.caption(f"Current discussion: {st.session_state.discussion_title}")

    if st.session_state.quiz_attempt_type == "weak_topic_quiz":
        st.info(
            f"Practice mode is active for weak topic: "
            f"**{st.session_state.quiz_focus}**"
        )

    if not st.session_state.session_id:
        st.info("Please create or open a discussion first.")
        return

    if not st.session_state.document_id:
        st.info("Please upload a document before generating a quiz.")
        return

    st.markdown("### Generate a quiz")

    quiz_focus = st.text_input(
        "Quiz focus",
        value=st.session_state.quiz_focus,
        placeholder="Examples: all key points, gradient descent, weak topics, chapter 1..."
    )

    default_style_index = 3 if st.session_state.quiz_attempt_type == "weak_topic_quiz" else 0

    quiz_style = st.selectbox(
        "Quiz style",
        [
            "standard",
            "quick",
            "long / full coverage",
            "practice weak topics",
            "exam preparation"
        ],
        index=default_style_index
    )

    if st.button("Generate quiz", type="primary"):
        clean_focus = quiz_focus.strip() if quiz_focus else "general lecture content"
        st.session_state.quiz_focus = clean_focus

        if st.session_state.quiz_attempt_type == "weak_topic_quiz":
            prompt = (
                f"Generate a focused practice quiz about the weak topic: {clean_focus}. "
                f"The quiz should help the student improve specifically on this topic."
            )
        else:
            prompt = f"Generate a {quiz_style} quiz about {clean_focus}."

        with st.spinner("Generating quiz... This may take some time with the local model."):
            response = send_chat(prompt)

        if response.status_code == 200:
            result = response.json()
            questions = result.get("questions", [])

            if questions:
                st.session_state.current_quiz = questions
                st.session_state.quiz_index = 0
                st.session_state.quiz_answers = []
                st.session_state.quiz_saved = False
                st.session_state.last_quiz_analysis = None

                st.success(f"{len(questions)} questions generated.")
                st.rerun()
            else:
                st.warning("No questions could be generated.")
        else:
            try:
                detail = response.json().get("detail", "Quiz generation failed.")
            except Exception:
                detail = "Quiz generation failed."
            st.error(detail)

    quiz = st.session_state.current_quiz

    if not quiz:
        st.info("No quiz generated yet.")
        return

    total_questions = len(quiz)
    index = st.session_state.quiz_index

    # ------------------------------------------------------------
    # Final result after all questions
    # ------------------------------------------------------------
    if index >= total_questions:
        correct_count = sum(
            1 for answer in st.session_state.quiz_answers
            if answer["is_correct"]
        )

        final_score = correct_count / total_questions if total_questions else 0

        st.success("Quiz completed.")
        st.markdown(f"### Final score: {correct_count}/{total_questions}")
        st.progress(final_score)
        st.write(f"Percentage: **{round(final_score * 100, 2)}%**")

        st.divider()
        st.markdown("### Answers review")

        for i, answer in enumerate(st.session_state.quiz_answers, start=1):
            with st.container(border=True):
                if answer["is_correct"]:
                    st.success(f"Question {i}: Correct")
                else:
                    st.error(f"Question {i}: Incorrect")

                st.write("**Question:**")
                st.write(answer["question"])

                st.write("**Your answer:**")
                st.write(answer["student_answer"])

                st.write("**Correct answer:**")
                st.write(answer["correct_answer"])

                if answer.get("explanation"):
                    st.write("**Explanation:**")
                    st.write(answer["explanation"])
# ------------------------------------------------------------
        # Analyze whole quiz attempt once
        # ------------------------------------------------------------
        if not st.session_state.quiz_saved:
            st.divider()
            st.markdown("### Global quiz analysis")

            with st.spinner("Analyzing your full quiz attempt... This may take some time."):
                analysis_response = analyze_full_quiz_attempt(
                    discussion_title=st.session_state.discussion_title or "current discussion",
                    quiz_focus=st.session_state.quiz_focus,
                    correct_count=correct_count,
                    total_questions=total_questions,
                    answers=st.session_state.quiz_answers,
                    attempt_type=st.session_state.quiz_attempt_type
                )

            if analysis_response.status_code == 200:
                analysis = analysis_response.json()
                st.session_state.last_quiz_analysis = analysis
                st.session_state.quiz_saved = True
                st.success("Quiz analysis saved.")
            else:
                try:
                    detail = analysis_response.json().get("detail", "Analysis failed.")
                except Exception:
                    detail = "Analysis failed."
                st.warning(detail)

        analysis = st.session_state.last_quiz_analysis

        if analysis:
            st.divider()
            st.markdown("### Agent analysis")

            overall_summary = analysis.get("overall_summary")
            if overall_summary:
                st.write(overall_summary)

            weak_topics = analysis.get("weak_topics", [])
            if weak_topics:
                st.markdown("#### Weak topics detected")
                for topic in weak_topics:
                    with st.container(border=True):
                        st.write(f"**{topic.get('topic')}**")

                        if topic.get("evidence"):
                            st.write("**Evidence:**")
                            st.write(topic.get("evidence"))

                        if topic.get("recommendation"):
                            st.write("**Recommendation:**")
                            st.write(topic.get("recommendation"))

                        if topic.get("mastery_status"):
                            st.caption(f"Status: {topic.get('mastery_status')}")
            else:
                st.info("No weak topics were detected from this full quiz attempt.")

            strong_topics = analysis.get("strong_topics", [])
            if strong_topics:
                st.markdown("#### Strong topics")
                for topic in strong_topics:
                    with st.container(border=True):
                        st.write(f"**{topic.get('topic')}**")
                        if topic.get("evidence"):
                            st.write(topic.get("evidence"))

            topic_progress = analysis.get("topic_progress", [])
            if topic_progress:
                st.markdown("#### Topic progress saved")
                for item in topic_progress:
                    with st.container(border=True):
                        score = item.get("score", 0)

                        try:
                            score_float = float(score)
                        except Exception:
                            score_float = 0.0

                        st.write(f"**{item.get('topic')}**")
                        st.progress(score_float)
                        st.write(f"Score: **{round(score_float * 100, 2)}%**")

                        if item.get("analysis"):
                            st.write("**Analysis:**")
                            st.write(item.get("analysis"))

                        if item.get("recommendation"):
                            st.write("**Recommendation:**")
                            st.write(item.get("recommendation"))

            if analysis.get("global_recommendation"):
                st.markdown("#### Global recommendation")
                st.write(analysis.get("global_recommendation"))

        if st.button("Start new quiz"):
            st.session_state.current_quiz = None
            st.session_state.quiz_index = 0
            st.session_state.quiz_answers = []
            st.session_state.quiz_saved = False
            st.session_state.quiz_focus = "general lecture content"
            st.session_state.quiz_attempt_type = "general_quiz"
            st.session_state.last_quiz_analysis = None
            st.rerun()

        return

    # ------------------------------------------------------------
    # Current question
    # ------------------------------------------------------------
    question = quiz[index]

    st.markdown(f"### Question {index + 1} / {total_questions}")
    st.write(question.get("question", ""))

    options = question.get("options", {})
    selected_answer = None

    if options:
        selected_answer = st.radio(
            "Choose your answer",
            options=list(options.keys()),
            format_func=lambda key: f"{key}) {options[key]}",
            key=f"quiz_answer_{index}"
        )
    else:
        selected_answer = st.text_area(
            "Your answer",
            key=f"quiz_text_answer_{index}"
        )

    if st.button("Submit answer", type="primary"):
        if not selected_answer:
            st.warning("Please provide an answer.")
            return

        correct_answer = str(question.get("answer", "")).strip().upper()
        student_answer = str(selected_answer).strip().upper()

        is_correct = student_answer == correct_answer

        st.session_state.quiz_answers.append({
            "question": question.get("question", ""),
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": question.get("explanation", "")
        })

        st.session_state.quiz_index += 1
        st.rerun()


# -------------------------------------------------------------------
# Render weak topics practice tab
# -------------------------------------------------------------------
def render_weak_topics_tab():
    st.subheader("Weak Topics Practice")

    st.write(
        "Here you can view your weak topics detected from full quiz analysis "
        "and practice each topic with a targeted quiz."
    )

    response = get_subject_weak_topics()

    if response.status_code != 200:
        st.error("Could not load weak topics.")
        return

    topics = response.json()

    if not topics:
        st.info(
            "No weak topics detected yet. Complete a quiz first so the agent "
            "can analyze your global performance."
        )
        return

    st.markdown("### Detected weak topics")

    for topic in topics:
        with st.container(border=True):
            topic_name = topic.get("topic", "Unknown topic")

            st.markdown(f"### 🎯 {topic_name}")

            mastery_status = topic.get("mastery_status")
            if mastery_status:
                st.caption(f"Status: {mastery_status}")

            evidence = topic.get("evidence")
            if evidence:
                st.write("**Why this is considered a weak topic:**")
                st.write(evidence)

            recommendation = topic.get("recommendation")
            if recommendation:
                st.write("**Recommendation:**")
                st.write(recommendation)

            detected_at = topic.get("detected_at")
            if detected_at:
                st.caption(f"Detected at: {detected_at}")

            if st.button(
                "Practice this topic",
                key=f"practice_topic_{topic.get('id')}",
                type="primary"
            ):
                start_weak_topic_practice(topic_name)
                st.info("Now go to the Quiz tab and click Generate quiz.")

    st.divider()
    st.markdown("### Topic progress history")

    progress_response = get_subject_topic_progress()

    if progress_response.status_code != 200:
        st.error("Could not load topic progress.")
        return

    records = progress_response.json()

    if not records:
        st.info("No topic progress recorded yet.")
        return

    grouped = {}

    for record in records:
        topic_name = record.get("topic", "Unknown topic")
        grouped.setdefault(topic_name, []).append(record)

    for topic_name, topic_records in grouped.items():
        with st.expander(topic_name):
            for record in topic_records:
                score = record.get("score", 0)

                try:
                    score_float = float(score)
                except Exception:
                    score_float = 0.0

                with st.container(border=True):
                    st.progress(score_float)
                    st.write(f"Score: **{round(score_float * 100, 2)}%**")

                    if (
                        record.get("correct_answers") is not None
                        and record.get("total_questions") is not None
                    ):
                        st.caption(
                            f"{record.get('correct_answers')}/{record.get('total_questions')} correct"
                        )

                    if record.get("attempt_type"):
                        st.caption(f"Attempt type: {record.get('attempt_type')}")

                    if record.get("analysis"):
                        st.write("**Analysis:**")
                        st.write(record.get("analysis"))

                    if record.get("recommendation"):
                        st.write("**Recommendation:**")
                        st.write(record.get("recommendation"))

                    if record.get("created_at"):
                        st.caption(f"Created at: {record.get('created_at')}")


# -------------------------------------------------------------------
# Render progress tab
# -------------------------------------------------------------------
def render_progress_tab():
    st.subheader("Subject Progress")

    st.markdown("### Weak topics")

    weak_response = get_subject_weak_topics()

    if weak_response.status_code == 200:
        topics = weak_response.json()

        if topics:
            for topic in topics:
                with st.container(border=True):
                    st.write(f"**{topic['topic']}**")

                    mastery_status = topic.get("mastery_status")
                    if mastery_status:
                        st.caption(f"Status: {mastery_status}")

                    evidence = topic.get("evidence")
                    if evidence:
                        st.write("**Evidence:**")
                        st.write(evidence)

                    recommendation = topic.get("recommendation")
                    if recommendation:
                        st.write("**Recommendation:**")
                        st.write(recommendation)

                    st.caption(f"Detected at: {topic.get('detected_at')}")
        else:
            st.info("No weak topics detected yet.")
    else:
        st.error("Could not load weak topics.")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Quiz results")

        response = get_subject_quiz_results()

        if response.status_code == 200:
            results = response.json()

            if results:
                for result in results:
                    score = result.get("score")
                    percent = round(score * 100, 2) if score is not None else 0

                    with st.container(border=True):
                        st.write(f"Score: **{percent}%**")
                        st.caption(result["timestamp"])
                        st.write(result["question"])

                        with st.expander("Attempt details"):
                            st.write(result.get("student_answer", ""))

                        if result.get("analysis_report"):
                            with st.expander("Analysis report"):
                                st.write(result.get("analysis_report"))
            else:
                st.info("No quiz results yet.")
        else:
            st.error("Could not load quiz results.")

    with col2:
        st.markdown("### Topic progress")

        progress_response = get_subject_topic_progress()

        if progress_response.status_code == 200:
            records = progress_response.json()

            if records:
                for record in records:
                    with st.container(border=True):
                        score = record.get("score", 0)

                        try:
                            score_float = float(score)
                        except Exception:
                            score_float = 0.0

                        st.write(f"**{record.get('topic')}**")
                        st.progress(score_float)
                        st.write(f"Score: **{round(score_float * 100, 2)}%**")

                        if (
                            record.get("correct_answers") is not None
                            and record.get("total_questions") is not None
                        ):
                            st.caption(
                                f"{record.get('correct_answers')}/{record.get('total_questions')} correct"
                            )

                        if record.get("attempt_type"):
                            st.caption(f"Attempt type: {record.get('attempt_type')}")

                        if record.get("analysis"):
                            st.write(record.get("analysis"))

                        if record.get("recommendation"):
                            st.write("**Recommendation:**")
                            st.write(record.get("recommendation"))

                        st.caption(f"Created at: {record.get('created_at')}")
            else:
                st.info("No topic progress recorded yet.")
        else:
            st.error("Could not load topic progress.")

    st.divider()
    st.markdown("### Uploaded documents")

    docs_response = get_subject_documents()

    if docs_response.status_code == 200:
        documents = docs_response.json()

        if documents:
            for document in documents:
                st.write(f"- {document['filename']}")
                st.caption(f"Uploaded at: {document['uploaded_at']}")
        else:
            st.info("No documents uploaded for this subject yet.")
    else:
        st.error("Could not load documents.")


# -------------------------------------------------------------------
# Render subject workspace
# -------------------------------------------------------------------
def render_subject_workspace():
    render_sidebar()

    st.title(f"📘 {st.session_state.subject_name}")

    if st.session_state.session_id:
        if st.session_state.discussion_title:
            st.subheader(f"💬 {st.session_state.discussion_title}")
        st.caption(f"Discussion ID: {st.session_state.session_id}")
    else:
        st.info("Open or create a discussion to start.")

    tabs = st.tabs([
        "Discussions",
        "Upload",
        "Chat",
        "Quiz",
        "Weak Topics",
        "Progress"
    ])

    with tabs[0]:
        render_discussions_tab()

    with tabs[1]:
        render_upload_tab()

    with tabs[2]:
        render_chat_tab()

    with tabs[3]:
        render_quiz_tab()

    with tabs[4]:
        render_weak_topics_tab()

    with tabs[5]:
        render_progress_tab()


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
def main():
    if not st.session_state.student_id:
        render_auth_page()
        return

    if not st.session_state.subject_id:
        render_subjects_dashboard()
        return

    render_subject_workspace()


if __name__ == "__main__":
    main()