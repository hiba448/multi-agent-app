import os
import re
import json
from typing import Dict, Optional, TypedDict, Any

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

from backend.agents.scribe import run_scribe_agent
from backend.agents.research import run_research_agent
from backend.agents.tutor import (
    run_quiz_generation,
    run_answer_evaluation
)
from db.vector_store import retrieve_similar_chunks

load_dotenv()

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL"),
    base_url=os.getenv("OLLAMA_BASE_URL"),
    temperature=0.0
)


# =============================================================================
# STATE DEFINITION
# =============================================================================
class AgentState(TypedDict, total=False):
    request: str
    document_id: int
    student_id: int
    subject_id: int
    extra: Optional[Dict[str, Any]]

    intent: str
    quiz_plan: Dict[str, Any]
    result: Dict[str, Any]


# =============================================================================
# INTENT CLASSIFICATION
# =============================================================================
INTENT_PROMPT = ChatPromptTemplate.from_template("""
You are the Orchestrator Agent. Your job is to classify the student's request
into exactly one of the following intents:

- SUMMARIZE : the student wants a summary or overview of the lecture
- QUESTION  : the student is asking a factual or conceptual question about the lecture
- QUIZ      : the student wants to be tested with practice questions
- EVALUATE  : the student is submitting an answer to a quiz question
- EXPLAIN   : the student wants a concept explained in simpler terms

Important routing rule:
- QUESTION and EXPLAIN are handled by the Research Agent.
- QUIZ and EVALUATE are handled by the Tutor Agent.
- SUMMARIZE is handled by the Scribe Agent.

STUDENT REQUEST:
{request}

Respond with exactly one word from the list above. Nothing else.
""")

VALID_INTENTS = {
    "SUMMARIZE",
    "QUESTION",
    "QUIZ",
    "EVALUATE",
    "EXPLAIN"
}


def classify_intent(request: str, extra: Optional[Dict] = None) -> str:
    """
    Classify the student request.
    If evaluation fields are present, force EVALUATE directly.
    """
    extra = extra or {}

    if (
        extra.get("question")
        and extra.get("correct_answer")
        and extra.get("student_answer")
    ):
        return "EVALUATE"

    prompt = INTENT_PROMPT.format_messages(request=request)
    response = llm.invoke(prompt)

    intent = response.content.strip().upper()

    if intent not in VALID_INTENTS:
        return "QUESTION"

    return intent


# =============================================================================
# QUIZ PLANNER
# =============================================================================
QUIZ_PLANNER_PROMPT = ChatPromptTemplate.from_template("""
You are a quiz planning assistant for an academic tutoring application.

Analyze the student's quiz request and decide:
1. quiz_focus: the topic or scope of the quiz
2. quiz_style: quick, standard, long, full_coverage, weak_topics, exam_preparation
3. num_questions: suitable number of questions
4. retrieval_query: best query to retrieve relevant lecture chunks

Rules:
- If the user asks for "quick", use 3 questions.
- If the user asks for "short", use 3 to 5 questions.
- If the user asks for a standard quiz, use 5 questions.
- If the user asks for "all key points", "full coverage", or "complete revision", use 8 to 12 questions.
- If the user asks for exam preparation, use 8 to 10 questions.
- If the user explicitly asks for a number, respect it, but keep it between 3 and 15.
- If the user asks about weak topics, set quiz_style to weak_topics.
- The quiz must stay based on the uploaded course material.

STUDENT REQUEST:
{request}

Return valid JSON only with this exact structure:
{{
  "quiz_focus": "string",
  "quiz_style": "string",
  "num_questions": 5,
  "retrieval_query": "string"
}}
""")


def extract_json_like(text: str) -> Dict:
    """
    Extract a JSON object from LLM output.
    This protects the app if the model adds extra text.
    """
    clean = text.strip()

    try:
        return json.loads(clean)
    except Exception:
        pass

    match = re.search(r"\{.*\}", clean, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return {}


def detect_explicit_question_count(request: str) -> Optional[int]:
    """
    Detect explicit question count from requests such as:
    - give me 10 questions
    - create 7 quiz questions
    """
    match = re.search(
        r"\b(\d{1,2})\s+(questions|question|quiz questions)\b",
        request.lower()
    )

    if not match:
        return None

    value = int(match.group(1))

    if value < 3:
        return 3

    if value > 15:
        return 15

    return value


def plan_quiz_request(request: str) -> Dict:
    """
    Plan quiz focus, style, length, and retrieval query.

    This belongs to the Orchestrator because it interprets the student's request.
    The Tutor Agent receives the final quiz configuration and generates questions.
    """
    explicit_count = detect_explicit_question_count(request)

    fallback_plan = {
        "quiz_focus": request,
        "quiz_style": "standard",
        "num_questions": explicit_count or 5,
        "retrieval_query": request
    }

    try:
        prompt = QUIZ_PLANNER_PROMPT.format_messages(request=request)
        response = llm.invoke(prompt)

        plan = extract_json_like(response.content)

        if not plan:
            return fallback_plan

        quiz_focus = str(plan.get("quiz_focus") or request).strip()
        quiz_style = str(plan.get("quiz_style") or "standard").strip()
        retrieval_query = str(plan.get("retrieval_query") or quiz_focus).strip()

        try:
            num_questions = int(
                plan.get(
                    "num_questions",
                    fallback_plan["num_questions"]
                )
            )
        except Exception:
            num_questions = fallback_plan["num_questions"]

        if explicit_count is not None:
            num_questions = explicit_count

        if num_questions < 3:
            num_questions = 3

        if num_questions > 15:
            num_questions = 15

        return {
            "quiz_focus": quiz_focus,
            "quiz_style": quiz_style,
            "num_questions": num_questions,
            "retrieval_query": retrieval_query
        }

    except Exception:
        return fallback_plan


# =============================================================================
# LANGGRAPH NODES
# =============================================================================
def classify_node(state: AgentState) -> AgentState:
    intent = classify_intent(
        request=state["request"],
        extra=state.get("extra")
    )

    state["intent"] = intent
    return state


def summarize_node(state: AgentState) -> AgentState:
    """
    SUMMARIZE requests are handled by the Scribe Agent.
    """
    chunks = retrieve_similar_chunks(
        query="lecture summary overview key concepts definitions",
        document_id=state["document_id"],
        top_k=10
    )

    result = run_scribe_agent(chunks)

    state["result"] = result
    return state


def question_node(state: AgentState) -> AgentState:
    """
    QUESTION requests are handled by the Research Agent.

    The Research Agent is responsible for:
    - answering lecture-related questions
    - grounding answers in the uploaded document
    - using web search if the lecture material is insufficient
    - mentioning web enrichment when it is used
    """
    result = run_research_agent(
        question=state["request"],
        document_id=state["document_id"]
    )

    state["result"] = result
    return state


def explain_node(state: AgentState) -> AgentState:
    """
    EXPLAIN requests are also handled by the Research Agent.

    Explanation is still a form of answering a student's question about lecture
    content, so it belongs to the Research Agent, not the Tutor Agent.
    """
    result = run_research_agent(
        question=state["request"],
        document_id=state["document_id"]
    )

    # Compatibility with the frontend:
    # if the frontend receives intent EXPLAIN, it expects an "explanation" field.
    if "answer" in result and "explanation" not in result:
        result["explanation"] = result["answer"]

    state["result"] = result
    return state


def quiz_node(state: AgentState) -> AgentState:
    """
    QUIZ requests are handled by the Tutor Agent.

    The Orchestrator plans the quiz first, then the Tutor Agent generates
    questions using the retrieved lecture chunks.
    """
    quiz_plan = plan_quiz_request(state["request"])
    state["quiz_plan"] = quiz_plan

    chunks = retrieve_similar_chunks(
        query=quiz_plan["retrieval_query"],
        document_id=state["document_id"],
        top_k=12
    )

    result = run_quiz_generation(
        chunks=chunks,
        student_id=state["student_id"],
        subject_id=state["subject_id"],
        num_questions=quiz_plan["num_questions"],
        quiz_focus=quiz_plan["quiz_focus"],
        quiz_style=quiz_plan["quiz_style"]
    )

    result["quiz_plan"] = quiz_plan

    state["result"] = result
    return state


def evaluate_node(state: AgentState) -> AgentState:
    """
    EVALUATE requests are handled by the Tutor Agent.

    This is used for quiz-answer feedback only.
    Weak-topic detection is handled by full quiz analysis, not by one wrong answer.
    """
    extra = state.get("extra") or {}

    result = run_answer_evaluation(
        question=extra.get("question", ""),
        correct_answer=extra.get("correct_answer", ""),
        student_answer=extra.get("student_answer", ""),
        student_id=state["student_id"],
        subject_id=state["subject_id"]
    )

    state["result"] = result
    return state


def compile_response_node(state: AgentState) -> AgentState:
    """
    Final node that enriches the response with metadata expected by the frontend.
    """
    result = state.get("result", {})

    result["intent"] = state.get("intent")
    result["student_id"] = state.get("student_id")
    result["subject_id"] = state.get("subject_id")
    result["document_id"] = state.get("document_id")

    if state.get("quiz_plan"):
        result["quiz_plan"] = state["quiz_plan"]

    state["result"] = result
    return state


# =============================================================================
# CONDITIONAL ROUTING
# =============================================================================
def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "QUESTION")

    if intent == "SUMMARIZE":
        return "summarize"

    if intent == "QUESTION":
        return "question"

    if intent == "QUIZ":
        return "quiz"

    if intent == "EVALUATE":
        return "evaluate"

    if intent == "EXPLAIN":
        return "explain"

    return "question"


# =============================================================================
# LANGGRAPH GRAPH BUILDING
# =============================================================================
def build_orchestrator_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify", classify_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("question", question_node)
    graph.add_node("quiz", quiz_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("explain", explain_node)
    graph.add_node("compile", compile_response_node)

    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "summarize": "summarize",
            "question": "question",
            "quiz": "quiz",
            "evaluate": "evaluate",
            "explain": "explain"
        }
    )

    graph.add_edge("summarize", "compile")
    graph.add_edge("question", "compile")
    graph.add_edge("quiz", "compile")
    graph.add_edge("evaluate", "compile")
    graph.add_edge("explain", "compile")

    graph.add_edge("compile", END)

    return graph.compile()


orchestrator_graph = build_orchestrator_graph()


# =============================================================================
# PUBLIC ENTRY POINT
# =============================================================================
def run_orchestrator(
    request: str,
    document_id: int,
    student_id: int,
    subject_id: int,
    extra: Optional[Dict] = None
) -> Dict:
    """
    Main orchestrator entry point used by the /chat endpoint.

    The external function signature stays unchanged, so no frontend or API
    change is required. Internally, the request is routed through LangGraph.
    """
    initial_state: AgentState = {
        "request": request,
        "document_id": document_id,
        "student_id": student_id,
        "subject_id": subject_id,
        "extra": extra or {}
    }

    final_state = orchestrator_graph.invoke(initial_state)

    return final_state["result"]