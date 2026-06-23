import os
import html
import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://backend:8000")
ENSIAS_LOGO_PATH = os.getenv("ENSIAS_LOGO_PATH", "assets/ensias_logo.png")

st.set_page_config(
    page_title="Lecture Companion",
    layout="wide"
)


# -------------------------------------------------------------------
# UI / UX skin only
# -------------------------------------------------------------------
def inject_custom_css():
    """
    Presentation-only styling.
    This function does not change app logic, API calls, session state,
    backend behavior, quiz behavior, upload behavior, or workflows.
    """
    st.markdown(
        """
        <style>
        :root {
            --ensias-red: #C8102E;
            --ensias-red-dark: #9F0D24;
            --ensias-red-soft: #FFF0F3;
            --bg-main: #FFFFFF;
            --bg-soft: #F5F5F5;
            --bg-card: #FFFFFF;
            --text-main: #222222;
            --text-muted: #555555;
            --border-soft: #E6E6E6;
            --success-bg: #F0FFF4;
            --success-border: #B7E4C7;
            --warning-bg: #FFF7E6;
            --warning-border: #FFE1A6;
            --danger-bg: #FFF0F3;
            --danger-border: rgba(200, 16, 46, 0.25);
            --info-bg: #F2F7FF;
            --info-border: #CFE1FF;
            --shadow-soft: 0 10px 30px rgba(0, 0, 0, 0.06);
            --shadow-hover: 0 16px 40px rgba(200, 16, 46, 0.12);
            --radius-lg: 22px;
            --radius-md: 16px;
            --radius-sm: 10px;
        }

        html, body, [class*="css"] {
            font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: var(--text-main);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(200, 16, 46, 0.08), transparent 32%),
                linear-gradient(180deg, #FFFFFF 0%, #FAFAFA 100%);
        }

        section[data-testid="stSidebar"] {
            background: #FFFFFF;
            border-right: 1px solid var(--border-soft);
            box-shadow: 8px 0 30px rgba(0,0,0,0.03);
        }

        section[data-testid="stSidebar"] * {
            color: var(--text-main) !important;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1320px;
        }

        h1, h2, h3, h4 {
            color: var(--text-main);
            letter-spacing: -0.03em;
        }

        p, span, div {
            color: var(--text-main);
        }

        .lc-hero {
            background: linear-gradient(135deg, #FFFFFF 0%, #FFF4F6 100%);
            border: 1px solid var(--border-soft);
            border-radius: 28px;
            padding: 2rem;
            box-shadow: var(--shadow-soft);
            margin-bottom: 1.5rem;
        }

        .lc-hero-title {
            font-size: 2.4rem;
            line-height: 1.05;
            font-weight: 850;
            color: var(--text-main);
            margin-bottom: 0.6rem;
        }

        .lc-hero-subtitle {
            font-size: 1.05rem;
            color: var(--text-muted);
            max-width: 760px;
            line-height: 1.6;
        }

        .lc-brand-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.2rem;
        }

        .lc-logo-mark {
            width: 44px;
            height: 44px;
            border-radius: 14px;
            background: linear-gradient(135deg, var(--ensias-red), var(--ensias-red-dark));
            color: #FFFFFF;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            box-shadow: 0 10px 24px rgba(200, 16, 46, 0.22);
        }

        .lc-brand-text {
            font-weight: 800;
            color: var(--text-main);
        }

        .lc-brand-subtext {
            font-size: 0.82rem;
            color: var(--text-muted);
            margin-top: -0.2rem;
        }

        .lc-card {
            background: var(--bg-card);
            border: 1px solid var(--border-soft);
            border-radius: var(--radius-lg);
            padding: 1.25rem;
            box-shadow: var(--shadow-soft);
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }

        .lc-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-hover);
            border-color: rgba(200, 16, 46, 0.35);
        }

        .lc-card-static {
            background: var(--bg-card);
            border: 1px solid var(--border-soft);
            border-radius: var(--radius-lg);
            padding: 1.25rem;
            box-shadow: var(--shadow-soft);
        }

        .lc-section-header {
            margin: 0.6rem 0 1rem 0;
        }

        .lc-section-kicker {
            color: var(--ensias-red);
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 800;
            margin-bottom: 0.3rem;
        }

        .lc-section-title {
            font-size: 1.65rem;
            font-weight: 850;
            color: var(--text-main);
            margin-bottom: 0.25rem;
            letter-spacing: -0.03em;
        }

        .lc-section-subtitle {
            color: var(--text-muted);
            font-size: 0.98rem;
            line-height: 1.6;
        }

        .lc-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.3rem 0.65rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            background: var(--ensias-red-soft);
            color: var(--ensias-red);
            border: 1px solid rgba(200, 16, 46, 0.18);
        }

        .lc-badge-gray {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.3rem 0.65rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            background: #F3F4F6;
            color: #333333;
            border: 1px solid #E5E7EB;
        }

        .lc-metric-card {
            background: #FFFFFF;
            border: 1px solid var(--border-soft);
            border-radius: 20px;
            padding: 1rem 1.1rem;
            box-shadow: var(--shadow-soft);
        }

        .lc-metric-label {
            font-size: 0.8rem;
            color: var(--text-muted);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .lc-metric-value {
            font-size: 1.55rem;
            font-weight: 850;
            color: var(--text-main);
            margin-top: 0.25rem;
        }

        .lc-metric-caption {
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 0.15rem;
        }

        .lc-empty {
            background: #FFFFFF;
            border: 1px dashed #DADADA;
            border-radius: 22px;
            padding: 2rem;
            text-align: center;
        }

        .lc-empty-title {
            font-size: 1.2rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .lc-empty-text {
            color: var(--text-muted);
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .lc-upload-card {
            background: linear-gradient(180deg, #FFFFFF, #FFF7F8);
            border: 2px dashed rgba(200, 16, 46, 0.35);
            border-radius: 26px;
            padding: 1.5rem;
            box-shadow: var(--shadow-soft);
        }

        .lc-chat-shell {
            background: #FFFFFF;
            border: 1px solid var(--border-soft);
            border-radius: 24px;
            padding: 1rem;
            box-shadow: var(--shadow-soft);
        }

        .lc-assistant-note {
            background: #FFF4F6;
            border: 1px solid rgba(200, 16, 46, 0.18);
            border-radius: 18px;
            padding: 1rem;
            color: var(--text-main);
        }

        .lc-info-card {
            background: var(--info-bg);
            border: 1px solid var(--info-border);
            border-radius: 18px;
            padding: 1rem;
            color: var(--text-main);
        }

        .lc-quiz-card {
            background: #FFFFFF;
            border: 1px solid var(--border-soft);
            border-radius: 24px;
            padding: 1.25rem;
            box-shadow: var(--shadow-soft);
        }

        .lc-score-card {
            background: linear-gradient(135deg, #FFFFFF 0%, #FFF0F3 100%);
            border: 1px solid rgba(200, 16, 46, 0.2);
            border-radius: 26px;
            padding: 1.5rem;
            box-shadow: var(--shadow-soft);
        }

        .lc-warning-card {
            background: var(--warning-bg);
            border: 1px solid var(--warning-border);
            border-radius: 20px;
            padding: 1rem;
        }

        .lc-success-card {
            background: var(--success-bg);
            border: 1px solid var(--success-border);
            border-radius: 20px;
            padding: 1rem;
        }

        .lc-danger-card {
            background: var(--danger-bg);
            border: 1px solid var(--danger-border);
            border-radius: 20px;
            padding: 1rem;
        }

        .stButton > button {
            border-radius: 999px !important;
            font-weight: 800 !important;
            border: 1px solid rgba(200, 16, 46, 0.25) !important;
            transition: all 0.16s ease !important;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 18px rgba(200, 16, 46, 0.18);
        }

        .stButton > button[kind="primary"] {
            background: var(--ensias-red) !important;
            color: #FFFFFF !important;
            border-color: var(--ensias-red) !important;
        }

        div[data-baseweb="tab-list"] {
            gap: 0.35rem;
            background: #FFFFFF;
            border: 1px solid var(--border-soft);
            padding: 0.35rem;
            border-radius: 18px;
            box-shadow: var(--shadow-soft);
        }

        button[data-baseweb="tab"] {
            border-radius: 14px !important;
            padding: 0.6rem 1rem !important;
            color: var(--text-main) !important;
            font-weight: 750 !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: var(--ensias-red-soft) !important;
            color: var(--ensias-red) !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] {
            border-radius: 14px !important;
        }

        .stProgress > div > div > div > div {
            background-color: var(--ensias-red) !important;
        }

        .lc-divider {
            height: 1px;
            background: var(--border-soft);
            margin: 1.2rem 0;
        }

        @media (max-width: 900px) {
            .lc-hero-title {
                font-size: 1.8rem;
            }

            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


inject_custom_css()


# -------------------------------------------------------------------
# Pure UI helper components
# -------------------------------------------------------------------
def escape_html(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def ensias_brand_block(compact: bool = False):
    """
    Visual-only ENSIAS branding block.
    Does not affect logic.
    """
    subtitle = "ENSIAS AI Learning Platform" if compact else "ENSIAS - Mohammed V University"

    st.markdown(
        f"""
        <div class="lc-brand-row">
            <div class="lc-logo-mark">E</div>
            <div>
                <div class="lc-brand-text">Lecture Companion</div>
                <div class="lc-brand-subtext">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def section_header(title: str, subtitle: str = "", kicker: str = ""):
    """
    Visual-only section heading.
    """
    kicker_html = f'<div class="lc-section-kicker">{escape_html(kicker)}</div>' if kicker else ""
    subtitle_html = f'<div class="lc-section-subtitle">{escape_html(subtitle)}</div>' if subtitle else ""

    st.markdown(
        f"""
        <div class="lc-section-header">
            {kicker_html}
            <div class="lc-section-title">{escape_html(title)}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def hero_block(title: str, subtitle: str):
    """
    Visual-only hero block.
    """
    st.markdown(
        f"""
        <div class="lc-hero">
            <div class="lc-brand-row">
                <div class="lc-logo-mark">E</div>
                <div>
                    <div class="lc-brand-text">Lecture Companion</div>
                    <div class="lc-brand-subtext">ENSIAS AI Study Assistant</div>
                </div>
            </div>
            <div class="lc-hero-title">{escape_html(title)}</div>
            <div class="lc-hero-subtitle">{escape_html(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def metric_card(title: str, value: str, caption: str = ""):
    """
    Visual-only metric card.
    """
    caption_html = f'<div class="lc-metric-caption">{escape_html(caption)}</div>' if caption else ""

    st.markdown(
        f"""
        <div class="lc-metric-card">
            <div class="lc-metric-label">{escape_html(title)}</div>
            <div class="lc-metric-value">{escape_html(value)}</div>
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def empty_state(title: str, message: str):
    """
    Visual-only empty state component.
    """
    st.markdown(
        f"""
        <div class="lc-empty">
            <div class="lc-empty-title">{escape_html(title)}</div>
            <div class="lc-empty-text">{escape_html(message)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def badge(text: str, variant: str = "red"):
    """
    Visual-only badge component.
    """
    class_name = "lc-badge" if variant == "red" else "lc-badge-gray"

    st.markdown(
        f"""
        <span class="{class_name}">{escape_html(text)}</span>
        """,
        unsafe_allow_html=True
    )


def soft_divider():
    """
    Visual-only divider.
    """
    st.markdown('<div class="lc-divider"></div>', unsafe_allow_html=True)


def display_web_search_notice():
    """
    Show a student-friendly notice when a response was enriched using web search.
    """
    st.markdown(
        """
        <div class="lc-info-card" style="margin: 0.75rem 0;">
            <div style="font-weight:850;margin-bottom:.25rem;">
                Web search was used
            </div>
            <div style="color:#555555;line-height:1.6;">
                The uploaded lecture did not contain enough information to answer fully,
                so the response was enriched with information found through web search.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def display_sources(sources):
    """
    Display sources in a readable way without exposing raw technical structures.
    """
    if not sources:
        return

    with st.expander("Sources used"):
        for source in sources:
            st.write(str(source))


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
def api_get(path: str, timeout=None):
    response = httpx.get(
        API_URL + path,
        timeout=None
    )
    return response


def api_post(path: str, json=None, data=None, files=None, timeout=None):
    response = httpx.post(
        API_URL + path,
        json=json,
        data=data,
        files=files,
        timeout=None
    )
    return response


def api_delete(path: str, timeout=None):
    response = httpx.delete(
        API_URL + path,
        timeout=None
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
        st.session_state.discussion_title = "Untitled discussion"

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
        }
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
        }
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
        }
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
    col_left, col_right = st.columns([1.15, 0.85], gap="large")

    with col_left:
        hero_block(
            "Your AI-powered academic companion.",
            "Upload lecture materials, chat with your course, generate adaptive quizzes, "
            "track weak topics, and improve topic by topic, locally and privately."
        )

        stat_col1, stat_col2, stat_col3 = st.columns(3)

        with stat_col1:
            metric_card("Learning", "AI-guided", "Personalized support")

        with stat_col2:
            metric_card("Privacy", "Local", "No external cloud")

        with stat_col3:
            metric_card("Progress", "Tracked", "Topic-level insights")

        st.markdown(
            """
            <div class="lc-card-static" style="margin-top: 1rem;">
                <div class="lc-section-kicker">ENSIAS Academic Platform</div>
                <div style="font-size:1.15rem;font-weight:800;margin-bottom:.4rem;">
                    Designed for structured student learning
                </div>
                <div style="color:#555555;line-height:1.65;">
                    Lecture Companion combines document understanding, multi-agent orchestration,
                    adaptive quizzes, weak-topic analytics, and progress tracking in one modern study workspace.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_right:
        st.markdown(
            """
            <div class="lc-card-static">
                <div class="lc-section-kicker">Secure Access</div>
                <div style="font-size:1.5rem;font-weight:850;margin-bottom:.3rem;">
                    Welcome back
                </div>
                <div style="color:#555555;margin-bottom:1rem;">
                    Sign in or create your ENSIAS learning account.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        tab_login, tab_register = st.tabs(["Login", "Register"])

        with tab_login:
            st.markdown("#### Login to your workspace")

            username_or_email = st.text_input(
                "Username or email",
                key="login_username_or_email",
                placeholder="example@ensias.ma"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
                placeholder="Enter your password"
            )

            if st.button("Login", type="primary", use_container_width=True):
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
            st.markdown("#### Create your account")

            name = st.text_input(
                "Full name",
                key="register_name",
                placeholder="Your full name"
            )

            username = st.text_input(
                "Username",
                key="register_username",
                placeholder="Choose a username"
            )

            email = st.text_input(
                "Email",
                key="register_email",
                placeholder="example@ensias.ma"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="register_password",
                placeholder="Create a password"
            )

            if st.button("Register", type="primary", use_container_width=True):
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
        ensias_brand_block(compact=True)

        st.markdown(
            """
            <div class="lc-card-static" style="padding:1rem;margin-bottom:1rem;">
                <div style="font-size:.78rem;color:#555555;font-weight:800;text-transform:uppercase;letter-spacing:.06em;">
                    Current workspace
                </div>
            """,
            unsafe_allow_html=True
        )

        if st.session_state.student_name:
            st.markdown(f"**Student:** {escape_html(st.session_state.student_name)}")

        if st.session_state.subject_name:
            st.markdown(f"**Subject:** {escape_html(st.session_state.subject_name)}")

        if st.session_state.session_id and st.session_state.discussion_title:
            st.markdown(f"**Discussion:** {escape_html(st.session_state.discussion_title)}")

        if st.session_state.document_id:
            st.markdown("**Document:** Available")

        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.subject_id:
            if st.button("Back to subjects", use_container_width=True):
                back_to_subjects()

        if st.button("Logout", use_container_width=True):
            logout()


# -------------------------------------------------------------------
# Render subjects dashboard
# -------------------------------------------------------------------
def render_subjects_dashboard():
    render_sidebar()

    hero_block(
        "Subjects Dashboard",
        "Create subjects, organize your learning, and access discussions, documents, quizzes, and progress analytics."
    )

    response = get_subjects()

    if response.status_code != 200:
        st.error("Could not load subjects.")
        return

    subjects = response.json()

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        metric_card("Subjects", str(len(subjects)), "Active study areas")

    with col_b:
        metric_card("Mode", "Local AI", "Ollama-powered")

    with col_c:
        metric_card("Workspace", "ENSIAS", "Academic assistant")

    soft_divider()

    with st.expander("Add new subject", expanded=False):
        st.markdown(
            """
            <div class="lc-card-static">
                <div style="font-size:1.15rem;font-weight:850;margin-bottom:.25rem;">
                    Create a new subject
                </div>
                <div style="color:#555555;margin-bottom:1rem;">
                    Group documents, discussions, quizzes, and progress by academic subject.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        subject_name = st.text_input(
            "Subject name",
            placeholder="Example: Machine Learning"
        )

        subject_description = st.text_area(
            "Description",
            height=80,
            placeholder="Optional: describe the course scope or chapters."
        )

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

    section_header(
        title="Your subjects",
        subtitle="Open a subject to access its discussions, documents, quizzes, and progress.",
        kicker="Study spaces"
    )

    if not subjects:
        empty_state(
            "No subjects yet",
            "Create your first subject to begin organizing your learning workspace."
        )
        return

    for idx in range(0, len(subjects), 3):
        row_subjects = subjects[idx:idx + 3]
        cols = st.columns(3)

        for col, subject in zip(cols, row_subjects):
            with col:
                safe_name = escape_html(subject.get("name", "Untitled subject"))
                safe_description = escape_html(
                    subject.get("description") or "No description provided."
                )
                safe_created_at = escape_html(subject.get("created_at", ""))

                st.markdown(
                    f"""
                    <div class="lc-card" style="min-height:210px;">
                        <div class="lc-badge">Subject</div>
                        <div style="font-size:1.35rem;font-weight:850;margin-top:1rem;margin-bottom:.35rem;">
                            {safe_name}
                        </div>
                        <div style="color:#555555;min-height:48px;">
                            {safe_description}
                        </div>
                        <div style="font-size:.8rem;color:#666666;margin-top:1rem;">
                            Created at: {safe_created_at}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                col_open, col_delete = st.columns(2)

                with col_open:
                    if st.button(
                        "Open",
                        key=f"open_subject_{subject['id']}",
                        type="primary",
                        use_container_width=True
                    ):
                        open_subject(subject)

                with col_delete:
                    if st.button(
                        "Delete",
                        key=f"delete_subject_{subject['id']}",
                        use_container_width=True
                    ):
                        delete_response = delete_subject(subject["id"])

                        if delete_response.status_code == 200:
                            st.success("Subject deleted.")
                            st.rerun()
                        else:
                            try:
                                detail = delete_response.json().get(
                                    "detail",
                                    "Could not delete subject."
                                )
                            except Exception:
                                detail = "Could not delete subject."
                            st.error(detail)


# -------------------------------------------------------------------
# Render discussions tab
# -------------------------------------------------------------------
def render_discussions_tab():
    section_header(
        title="Discussions",
        subtitle="Create or open a discussion inside this subject. Each discussion keeps its own document and chat history.",
        kicker="Learning threads"
    )

    with st.expander("Create new discussion", expanded=False):
        st.markdown(
            """
            <div class="lc-card-static">
                <div style="font-weight:850;font-size:1.1rem;">Start a new discussion</div>
                <div style="color:#555555;margin-top:.25rem;">
                    Use a clear title such as Chapter 1, Regression, Neural Networks, or Exam Revision.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

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
        empty_state(
            "No discussions yet",
            "Create your first discussion to upload a document and start chatting."
        )
        return

    for discussion in sessions:
        title = discussion.get("title") or "Untitled discussion"
        document_label = (
            "Document available"
            if discussion.get("document_id")
            else "No document uploaded yet"
        )

        safe_title = escape_html(title)
        safe_preview = escape_html(discussion.get("preview", "Empty discussion"))
        safe_document_label = escape_html(document_label)
        safe_created_at = escape_html(discussion.get("created_at", ""))

        st.markdown(
            f"""
            <div class="lc-card-static" style="margin-bottom:.8rem;">
                <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
                    <div>
                        <div class="lc-badge-gray">Discussion</div>
                        <div style="font-size:1.25rem;font-weight:850;margin-top:.65rem;">
                            {safe_title}
                        </div>
                        <div style="color:#555555;margin-top:.35rem;">
                            {safe_preview}
                        </div>
                        <div style="font-size:.82rem;color:#666666;margin-top:.6rem;">
                            {safe_document_label} - Created at: {safe_created_at}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_open, col_delete, _ = st.columns([1, 1, 4])

        with col_open:
            if st.button(
                "Open",
                key=f"open_discussion_{discussion['session_id']}",
                type="primary",
                use_container_width=True
            ):
                open_discussion(discussion)

        with col_delete:
            if st.button(
                "Delete",
                key=f"delete_discussion_{discussion['session_id']}",
                use_container_width=True
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
    section_header(
        title="Upload lecture document",
        subtitle="Upload a PDF or PowerPoint file. The system will validate whether it belongs to this subject before indexing it.",
        kicker="Document intelligence"
    )

    if not st.session_state.session_id:
        empty_state(
            "Open a discussion first",
            "You need to create or open a discussion before uploading a document."
        )
        return

    if st.session_state.discussion_title:
        badge(f"Current discussion: {st.session_state.discussion_title}", variant="gray")

    st.markdown(
        """
        <div class="lc-upload-card" style="margin-top:1rem;">
            <div style="font-size:1.25rem;font-weight:850;margin-bottom:.35rem;">
                Upload your lecture material
            </div>
            <div style="color:#555555;line-height:1.6;">
                Supported formats: PDF, PPTX, PPT. The document will be parsed,
                validated against the current subject, indexed, and linked to this discussion.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Choose a PDF or PowerPoint file",
        type=["pdf", "pptx", "ppt"]
    )

    if uploaded_file:
        st.markdown(
            f"""
            <div class="lc-card-static" style="margin-top:1rem;">
                <div class="lc-badge-gray">Selected file</div>
                <div style="font-size:1.1rem;font-weight:800;margin-top:.6rem;">
                    {escape_html(uploaded_file.name)}
                </div>
                <div style="color:#555555;font-size:.9rem;margin-top:.2rem;">
                    Ready for subject validation and processing.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if uploaded_file and st.button("Upload and process", type="primary"):
        with st.spinner("Uploading, validating subject relevance, and processing document..."):
            response = upload_document(uploaded_file)

        if response.status_code == 200:
            data = response.json()
            st.session_state.document_id = data["document_id"]

            st.markdown(
                """
                <div class="lc-success-card">
                    <div style="font-weight:850;font-size:1.05rem;">File uploaded successfully</div>
                    <div style="color:#355E3B;margin-top:.25rem;">
                        The document is now linked to this discussion and ready for chat, summaries, and quizzes.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            validation = data.get("subject_validation")
            if validation:
                with st.expander("Subject validation result"):
                    st.write(f"Relevant: **{validation.get('relevant')}**")
                    st.write(f"Confidence: **{validation.get('confidence')}**")
                    st.write(validation.get("reason", ""))

        else:
            try:
                detail = response.json().get("detail", "Upload failed.")
            except Exception:
                detail = "Upload failed."

            if isinstance(detail, dict):
                st.markdown(
                    """
                    <div class="lc-danger-card">
                        <div style="font-weight:850;font-size:1.05rem;">Document rejected</div>
                        <div style="color:#555555;margin-top:.25rem;">
                            The uploaded document does not appear to match the current subject.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

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
        st.markdown(
            """
            <div class="lc-assistant-note">
                <div style="font-size:1.15rem;font-weight:850;margin-bottom:.4rem;">
                    Lecture Summary
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write(result.get("summary", ""))

        concepts = result.get("key_concepts", [])
        if concepts:
            st.markdown("#### Key Concepts")
            for concept in concepts:
                st.write(f"- {concept}")

        definitions = result.get("definitions", {})
        if definitions:
            st.markdown("#### Definitions")
            for term, definition in definitions.items():
                st.write(f"**{term}:** {definition}")

    elif intent == "QUESTION":
        st.markdown(
            """
            <div class="lc-assistant-note">
                <div style="font-weight:850;">Answer</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if result.get("web_enriched"):
            display_web_search_notice()

        st.write(result.get("answer", ""))

        sources = result.get("sources", [])
        display_sources(sources)

    elif intent == "EXPLAIN":
        st.markdown(
            """
            <div class="lc-assistant-note">
                <div style="font-weight:850;">Explanation</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if result.get("web_enriched"):
            display_web_search_notice()

        explanation = result.get("explanation") or result.get("answer", "")
        st.write(explanation)

        sources = result.get("sources", [])
        display_sources(sources)

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

        st.markdown(
            f"""
            <div class="lc-success-card">
                <div style="font-size:1.08rem;font-weight:850;">Quiz generated</div>
                <div style="color:#355E3B;margin-top:.25rem;">
                    {len(questions)} questions were generated. Open the Quiz tab to start.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    elif intent == "EVALUATE":
        if result.get("correct"):
            st.success("Correct answer.")
        else:
            st.error("Incorrect answer.")

        st.write(result.get("feedback", ""))

    else:
        message = (
            result.get("answer")
            or result.get("explanation")
            or result.get("summary")
            or "The assistant returned a response."
        )
        st.write(message)


def build_display_text(result: dict) -> str:
    intent = result.get("intent")

    if intent == "SUMMARIZE":
        return result.get("summary", "")

    if intent == "QUESTION":
        return result.get("answer", "")

    if intent == "EXPLAIN":
        return result.get("explanation") or result.get("answer", "")

    if intent == "QUIZ":
        questions = result.get("questions", [])
        return f"{len(questions)} questions generated."

    if intent == "EVALUATE":
        return result.get("feedback", "")

    return (
        result.get("answer")
        or result.get("explanation")
        or result.get("summary")
        or "The assistant returned a response."
    )


# -------------------------------------------------------------------
# Render chat tab
# -------------------------------------------------------------------
def render_chat_tab():
    if st.session_state.discussion_title:
        section_header(
            title=f"Chat - {st.session_state.discussion_title}",
            subtitle="Ask questions, request summaries, generate quizzes, or ask for clearer explanations.",
            kicker="AI assistant"
        )
    else:
        section_header(
            title="Chat with your lecture",
            subtitle="Open a discussion and upload a document before starting.",
            kicker="AI assistant"
        )

    if not st.session_state.session_id:
        empty_state(
            "No discussion selected",
            "Create or open a discussion before chatting."
        )
        return

    if not st.session_state.document_id:
        empty_state(
            "No document uploaded",
            "Upload a lecture document before using the chat assistant."
        )
        return

    st.markdown(
        """
        <div class="lc-chat-shell">
            <div style="font-weight:850;font-size:1.05rem;margin-bottom:.25rem;">
                Lecture Companion AI
            </div>
            <div style="color:#555555;font-size:.92rem;">
                Responses are based on the document linked to the active discussion.
                If the lecture content is not sufficient, the assistant may use web search and will mention it clearly.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    suggested_col1, suggested_col2, suggested_col3 = st.columns(3)

    with suggested_col1:
        st.caption("Try: Give me a summary")

    with suggested_col2:
        st.caption("Try: Explain this concept simply")

    with suggested_col3:
        st.caption("Try: Generate a quiz")

    soft_divider()

    for message in st.session_state.messages:
        role = message.get("role", "agent")

        if role == "user":
            with st.chat_message("user"):
                st.write(message.get("content", ""))
        else:
            with st.chat_message("assistant"):
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
    section_header(
        title="Quiz Studio",
        subtitle="Generate adaptive quizzes, complete all questions, then receive a global performance analysis.",
        kicker="Practice mode"
    )

    if st.session_state.discussion_title:
        badge(f"Current discussion: {st.session_state.discussion_title}", variant="gray")

    if st.session_state.quiz_attempt_type == "weak_topic_quiz":
        st.markdown(
            f"""
            <div class="lc-warning-card" style="margin-top:1rem;">
                <div style="font-weight:850;">Weak-topic practice mode</div>
                <div style="color:#555555;margin-top:.25rem;">
                    Practice mode is active for: <strong>{escape_html(st.session_state.quiz_focus)}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if not st.session_state.session_id:
        empty_state(
            "Open a discussion first",
            "A quiz needs an active discussion and document."
        )
        return

    if not st.session_state.document_id:
        empty_state(
            "Upload a document first",
            "The quiz generator uses the document linked to the active discussion."
        )
        return

    st.markdown(
        """
        <div class="lc-quiz-card" style="margin-top:1rem;">
            <div style="font-size:1.2rem;font-weight:850;margin-bottom:.35rem;">
                Generate a quiz
            </div>
            <div style="color:#555555;line-height:1.55;">
                Choose a focus and style. The system will generate questions using the active document context.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

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
        empty_state(
            "No quiz generated yet",
            "Choose a quiz focus and click Generate quiz to begin."
        )
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

        st.markdown(
            f"""
            <div class="lc-score-card">
                <div class="lc-section-kicker">Quiz completed</div>
                <div style="font-size:2rem;font-weight:900;margin-bottom:.25rem;">
                    Final score: {correct_count}/{total_questions}
                </div>
                <div style="color:#555555;">
                    Percentage: {round(final_score * 100, 2)}%
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.progress(final_score)

        soft_divider()

        section_header(
            title="Answers review",
            subtitle="Review each answer before the full analysis is displayed."
        )

        for i, answer in enumerate(st.session_state.quiz_answers, start=1):
            if answer["is_correct"]:
                card_class = "lc-success-card"
                status = "Correct"
            else:
                card_class = "lc-danger-card"
                status = "Incorrect"

            st.markdown(
                f"""
                <div class="{card_class}" style="margin-bottom:.8rem;">
                    <div style="font-weight:850;">Question {i}: {status}</div>
                    <div style="margin-top:.5rem;"><strong>Question:</strong> {escape_html(answer["question"])}</div>
                    <div style="margin-top:.3rem;"><strong>Your answer:</strong> {escape_html(answer["student_answer"])}</div>
                    <div style="margin-top:.3rem;"><strong>Correct answer:</strong> {escape_html(answer["correct_answer"])}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if answer.get("explanation"):
                with st.expander(f"Explanation for Question {i}"):
                    st.write(answer["explanation"])

        # ------------------------------------------------------------
        # Analyze whole quiz attempt once
        # ------------------------------------------------------------
        if not st.session_state.quiz_saved:
            soft_divider()

            section_header(
                title="Global quiz analysis",
                subtitle="The full quiz attempt is analysed to identify weak topics and topic-level progress.",
                kicker="Performance report"
            )

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

                st.markdown(
                    """
                    <div class="lc-success-card">
                        <div style="font-weight:850;">Analysis saved successfully</div>
                        <div style="color:#355E3B;margin-top:.25rem;">
                            Weak topics, strong topics, quiz results, and topic progress were updated.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                try:
                    detail = analysis_response.json().get("detail", "Analysis failed.")
                except Exception:
                    detail = "Analysis failed."
                st.warning(detail)

        analysis = st.session_state.last_quiz_analysis

        if analysis:
            soft_divider()

            section_header(
                title="Learning analysis",
                subtitle="A global learning report based on the completed quiz attempt.",
                kicker="Insights"
            )

            overall_summary = analysis.get("overall_summary")
            if overall_summary:
                st.markdown(
                    f"""
                    <div class="lc-card-static">
                        <div style="font-weight:850;font-size:1.1rem;margin-bottom:.35rem;">
                            Overall summary
                        </div>
                        <div style="color:#555555;line-height:1.65;">
                            {escape_html(overall_summary)}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            weak_topics = analysis.get("weak_topics", [])
            if weak_topics:
                st.markdown("#### Weak topics detected")

                for topic in weak_topics:
                    topic_name = escape_html(topic.get("topic", "Unknown topic"))

                    st.markdown(
                        f"""
                        <div class="lc-warning-card" style="margin-bottom:.8rem;">
                            <div style="font-weight:850;font-size:1.05rem;">
                                {topic_name}
                            </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if topic.get("evidence"):
                        st.write("**Evidence:**")
                        st.write(topic.get("evidence"))

                    if topic.get("recommendation"):
                        st.write("**Recommendation:**")
                        st.write(topic.get("recommendation"))

                    if topic.get("mastery_status"):
                        st.caption(f"Status: {topic.get('mastery_status')}")

                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("No weak topics were detected from this full quiz attempt.")

            strong_topics = analysis.get("strong_topics", [])
            if strong_topics:
                st.markdown("#### Strong topics")

                for topic in strong_topics:
                    topic_name = escape_html(topic.get("topic", ""))

                    st.markdown(
                        f"""
                        <div class="lc-success-card" style="margin-bottom:.8rem;">
                            <div style="font-weight:850;font-size:1.05rem;">
                                {topic_name}
                            </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if topic.get("evidence"):
                        st.write(topic.get("evidence"))

                    st.markdown("</div>", unsafe_allow_html=True)

            topic_progress = analysis.get("topic_progress", [])
            if topic_progress:
                st.markdown("#### Topic progress saved")

                for item in topic_progress:
                    score = item.get("score", 0)

                    try:
                        score_float = float(score)
                    except Exception:
                        score_float = 0.0

                    topic_name = escape_html(item.get("topic", "Unknown topic"))

                    st.markdown(
                        f"""
                        <div class="lc-card-static" style="margin-bottom:.8rem;">
                            <div style="font-weight:850;font-size:1.05rem;">
                                {topic_name}
                            </div>
                            <div style="color:#555555;margin-top:.25rem;">
                                Score: {round(score_float * 100, 2)}%
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.progress(score_float)

                    if item.get("analysis"):
                        st.write("**Analysis:**")
                        st.write(item.get("analysis"))

                    if item.get("recommendation"):
                        st.write("**Recommendation:**")
                        st.write(item.get("recommendation"))

            if analysis.get("global_recommendation"):
                st.markdown("#### Global recommendation")
                st.markdown(
                    f"""
                    <div class="lc-assistant-note">
                        {escape_html(analysis.get("global_recommendation"))}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        if st.button("Start new quiz", use_container_width=True):
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

    progress_value = (index + 1) / total_questions if total_questions else 0

    st.markdown(
        f"""
        <div class="lc-quiz-card" style="margin-top:1rem;">
            <div class="lc-section-kicker">Question {index + 1} of {total_questions}</div>
            <div style="font-size:1.35rem;font-weight:850;margin-top:.35rem;">
                {escape_html(question.get("question", ""))}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.progress(progress_value)

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

    if st.button("Submit answer", type="primary", use_container_width=True):
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
# Small display helpers
# -------------------------------------------------------------------
def format_attempt_type(attempt_type: str) -> str:
    if attempt_type == "weak_topic_quiz":
        return "Weak-topic practice"
    if attempt_type == "general_quiz":
        return "General quiz"
    if not attempt_type:
        return ""
    return attempt_type.replace("_", " ").title()


# -------------------------------------------------------------------
# Render weak topics practice tab
# -------------------------------------------------------------------
def render_weak_topics_tab():
    section_header(
        title="Weak Topics Practice",
        subtitle="Review weaknesses detected from full quiz analysis and launch targeted practice quizzes.",
        kicker="Targeted improvement"
    )

    response = get_subject_weak_topics()

    if response.status_code != 200:
        st.error("Could not load weak topics.")
        return

    topics = response.json()

    if not topics:
        empty_state(
            "No weak topics detected yet",
            "Complete a quiz first so the system can analyse your performance."
        )
        return

    st.markdown("### Detected weak topics")

    for topic in topics:
        topic_name = topic.get("topic", "Unknown topic")
        safe_topic_name = escape_html(topic_name)

        st.markdown(
            f"""
            <div class="lc-warning-card" style="margin-bottom:.9rem;">
                <div class="lc-badge-gray">Weak topic</div>
                <div style="font-size:1.25rem;font-weight:850;margin-top:.65rem;">
                    {safe_topic_name}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

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
            type="primary",
            use_container_width=True
        ):
            start_weak_topic_practice(topic_name)
            st.info("Now go to the Quiz tab and click Generate quiz.")

        soft_divider()

    section_header(
        title="Topic progress history",
        subtitle="Track how your performance evolves across general quizzes and weak-topic practice attempts."
    )

    progress_response = get_subject_topic_progress()

    if progress_response.status_code != 200:
        st.error("Could not load topic progress.")
        return

    records = progress_response.json()

    if not records:
        empty_state(
            "No topic progress recorded yet",
            "Topic progress will appear after completing analysed quizzes."
        )
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

                st.markdown(
                    f"""
                    <div class="lc-card-static" style="margin-bottom:.8rem;">
                        <div style="font-weight:850;">Attempt score</div>
                        <div style="font-size:1.3rem;font-weight:900;color:#222222;">
                            {round(score_float * 100, 2)}%
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.progress(score_float)

                if (
                    record.get("correct_answers") is not None
                    and record.get("total_questions") is not None
                ):
                    st.caption(
                        f"{record.get('correct_answers')}/{record.get('total_questions')} correct"
                    )

                readable_attempt_type = format_attempt_type(record.get("attempt_type"))
                if readable_attempt_type:
                    st.caption(f"Attempt type: {readable_attempt_type}")

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
    section_header(
        title="Progress Dashboard",
        subtitle="Monitor weak topics, quiz results, topic progress, and uploaded documents.",
        kicker="Learning analytics"
    )

    weak_response = get_subject_weak_topics()
    quiz_response = get_subject_quiz_results()
    progress_response = get_subject_topic_progress()
    docs_response = get_subject_documents()

    weak_topics_count = 0
    quiz_count = 0
    progress_count = 0
    docs_count = 0

    if weak_response.status_code == 200:
        weak_topics_count = len(weak_response.json())

    if quiz_response.status_code == 200:
        quiz_count = len(quiz_response.json())

    if progress_response.status_code == 200:
        progress_count = len(progress_response.json())

    if docs_response.status_code == 200:
        docs_count = len(docs_response.json())

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        metric_card("Weak Topics", str(weak_topics_count), "Detected by analysis")

    with metric_col2:
        metric_card("Quizzes", str(quiz_count), "Completed attempts")

    with metric_col3:
        metric_card("Topic Records", str(progress_count), "Progress entries")

    with metric_col4:
        metric_card("Documents", str(docs_count), "Uploaded materials")

    soft_divider()

    col_left, col_right = st.columns(2)

    with col_left:
        section_header(
            title="Weak topics",
            subtitle="Concepts that need attention."
        )

        if weak_response.status_code == 200:
            topics = weak_response.json()

            if topics:
                for topic in topics:
                    topic_name = escape_html(topic.get("topic", "Unknown topic"))

                    st.markdown(
                        f"""
                        <div class="lc-warning-card" style="margin-bottom:.8rem;">
                            <div style="font-weight:850;">{topic_name}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

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

                    detected_at = topic.get("detected_at")
                    if detected_at:
                        st.caption(f"Detected at: {detected_at}")
            else:
                empty_state(
                    "No weak topics yet",
                    "Finish a quiz to let the system detect learning gaps."
                )
        else:
            st.error("Could not load weak topics.")

    with col_right:
        section_header(
            title="Quiz results",
            subtitle="Final scores saved after full quiz analysis."
        )

        if quiz_response.status_code == 200:
            results = quiz_response.json()

            if results:
                for result in results:
                    score = result.get("score")
                    percent = round(score * 100, 2) if score is not None else 0

                    title = result.get("question") or "Completed quiz"
                    safe_title = escape_html(title)

                    st.markdown(
                        f"""
                        <div class="lc-card-static" style="margin-bottom:.8rem;">
                            <div class="lc-badge">Quiz result</div>
                            <div style="font-size:1.35rem;font-weight:900;margin-top:.6rem;">
                                {percent}%
                            </div>
                            <div style="color:#555555;margin-top:.25rem;">
                                {safe_title}
                            </div>
                            <div style="font-size:.82rem;color:#666666;margin-top:.4rem;">
                                {escape_html(result.get("timestamp", ""))}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    student_answer = result.get("student_answer")
                    if student_answer:
                        with st.expander("Attempt details"):
                            st.write(student_answer)

                    if result.get("analysis_report"):
                        with st.expander("Analysis report"):
                            st.write(result.get("analysis_report"))
            else:
                empty_state(
                    "No quiz results yet",
                    "Complete a quiz to see your score history."
                )
        else:
            st.error("Could not load quiz results.")

    soft_divider()

    section_header(
        title="Topic progress",
        subtitle="Topic-level progress from general quizzes and weak-topic practice."
    )

    if progress_response.status_code == 200:
        records = progress_response.json()

        if records:
            for record in records:
                score = record.get("score", 0)

                try:
                    score_float = float(score)
                except Exception:
                    score_float = 0.0

                topic_name = escape_html(record.get("topic", "Unknown topic"))

                st.markdown(
                    f"""
                    <div class="lc-card-static" style="margin-bottom:.8rem;">
                        <div style="font-weight:850;font-size:1.1rem;">{topic_name}</div>
                        <div style="color:#555555;margin-top:.25rem;">
                            Score: {round(score_float * 100, 2)}%
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.progress(score_float)

                if (
                    record.get("correct_answers") is not None
                    and record.get("total_questions") is not None
                ):
                    st.caption(
                        f"{record.get('correct_answers')}/{record.get('total_questions')} correct"
                    )

                readable_attempt_type = format_attempt_type(record.get("attempt_type"))
                if readable_attempt_type:
                    st.caption(f"Attempt type: {readable_attempt_type}")

                if record.get("analysis"):
                    st.write(record.get("analysis"))

                if record.get("recommendation"):
                    st.write("**Recommendation:**")
                    st.write(record.get("recommendation"))

                if record.get("created_at"):
                    st.caption(f"Created at: {record.get('created_at')}")
        else:
            empty_state(
                "No topic progress yet",
                "Topic progress will appear after analysed quiz attempts."
            )
    else:
        st.error("Could not load topic progress.")

    soft_divider()

    section_header(
        title="Uploaded documents",
        subtitle="Documents accepted and linked to this subject."
    )

    if docs_response.status_code == 200:
        documents = docs_response.json()

        if documents:
            for document in documents:
                filename = escape_html(document.get("filename", "Uploaded document"))
                uploaded_at = escape_html(document.get("uploaded_at", ""))

                st.markdown(
                    f"""
                    <div class="lc-card-static" style="margin-bottom:.6rem;">
                        <div style="font-weight:850;">{filename}</div>
                        <div style="font-size:.85rem;color:#666666;">
                            Uploaded at: {uploaded_at}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            empty_state(
                "No documents uploaded",
                "Upload a document inside a discussion to begin learning."
            )
    else:
        st.error("Could not load documents.")


# -------------------------------------------------------------------
# Render subject workspace
# -------------------------------------------------------------------
def render_subject_workspace():
    render_sidebar()

    subject_name = escape_html(st.session_state.subject_name or "Subject")

    st.markdown(
        f"""
        <div class="lc-hero">
            <div class="lc-section-kicker">Subject workspace</div>
            <div class="lc-hero-title">{subject_name}</div>
            <div class="lc-hero-subtitle">
                Manage discussions, upload lecture materials, chat with the assistant,
                generate quizzes, practise weak topics, and track progress.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.session_id:
        if st.session_state.discussion_title:
            badge(f"Active discussion: {st.session_state.discussion_title}", variant="red")
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