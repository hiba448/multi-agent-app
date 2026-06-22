import os
import re
from typing import Dict, Optional

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from backend.agents.scribe import run_scribe_agent
from backend.agents.research import run_research_agent
from backend.agents.tutor import (
    run_quiz_generation,
    run_answer_evaluation,
    run_explanation
)
from db.vector_store import retrieve_similar_chunks

load_dotenv()

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL"),
    base_url=os.getenv("OLLAMA_BASE_URL"),
    temperature=0.0
)


# -------------------------------------------------------------------
# Intent classification
# -------------------------------------------------------------------
INTENT_PROMPT = ChatPromptTemplate.from_template("""
You are the Orchestrator Agent. Your only job is to classify the student's
request into exactly one of the following intents:

- SUMMARIZE : the student wants a summary or overview of the lecture
- QUESTION  : the student is asking a question about the lecture content
- QUIZ      : the student wants to be tested with practice questions
- EVALUATE  : the student is submitting an answer to a quiz question
- EXPLAIN   : the student wants a concept explained in simpler terms

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
    Classify student request into an intent.
    Automatically forces EVALUATE if quiz answer fields exist.
    """
    extra = extra or {}

    if (
        extra.get("question") and
        extra.get("correct_answer") and
        extra.get("student_answer")
    ):
        return "EVALUATE"

    prompt = INTENT_PROMPT.format_messages(request=request)
    response = llm.invoke(prompt)

    intent = response.content.strip().upper()

    if intent not in VALID_INTENTS:
        return "QUESTION"

    return intent


# -------------------------------------------------------------------
# Quiz planning
# -------------------------------------------------------------------
QUIZ_PLANNER_PROMPT = ChatPromptTemplate.from_template("""
You are a quiz planning assistant for a local academic tutoring app.

Analyze the student's quiz request and decide:
1. quiz_focus: the topic or scope of the quiz
2. quiz_style: quick, standard, long, full_coverage, weak_topics, exam_preparation
3. num_questions: suitable number of questions
4. retrieval_query: the best query to retrieve relevant course chunks

Rules:
- If the user asks for "quick", use 3 questions.
- If the user asks for "short", use 3 to 5 questions.
- If the user asks for a standard quiz, use 5 questions.
- If the user asks for "all key points", "full coverage", "complete revision", use 10 to 12 questions.
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
    Extract a simple JSON object from LLM output.
    This avoids crashing if the model adds extra text.
    """
    import json

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
    Detect explicit question count from requests like:
    - give me 10 questions
    - create 7 quiz questions
    """
    match = re.search(r"\b(\d{1,2})\s+(questions|question|quiz questions)\b", request.lower())

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
    Decide quiz focus, style, length, and retrieval query.
    Uses a hybrid approach:
    - rule-based safeguards
    - LLM planner
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
            num_questions = int(plan.get("num_questions", fallback_plan["num_questions"]))
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


# -------------------------------------------------------------------
# Main orchestrator
# -------------------------------------------------------------------
def run_orchestrator(
    request: str,
    document_id: int,
    student_id: int,
    subject_id: int,
    extra: Optional[Dict] = None
) -> Dict:
    """
    Main orchestrator entry point.

    Routes the request to:
    - Scribe Agent
    - Research Agent
    - Tutor Agent

    subject_id is passed to Tutor so weak topics and quiz results
    are saved per subject.
    """
    extra = extra or {}
    intent = classify_intent(request, extra)

    # ------------------------------------------------------------
    # SUMMARIZE
    # ------------------------------------------------------------
    if intent == "SUMMARIZE":
        chunks = retrieve_similar_chunks(
            query="lecture summary overview key concepts definitions",
            document_id=document_id,
            top_k=10
        )

        result = run_scribe_agent(chunks)

    # ------------------------------------------------------------
    # QUESTION
    # ------------------------------------------------------------
    elif intent == "QUESTION":
        result = run_research_agent(
            question=request,
            document_id=document_id
        )

    # ------------------------------------------------------------
    # QUIZ — adaptive planning
    # ------------------------------------------------------------
    elif intent == "QUIZ":
        quiz_plan = plan_quiz_request(request)

        chunks = retrieve_similar_chunks(
            query=quiz_plan["retrieval_query"],
            document_id=document_id,
            top_k=12
        )

        result = run_quiz_generation(
            chunks=chunks,
            student_id=student_id,
            subject_id=subject_id,
            num_questions=quiz_plan["num_questions"],
            quiz_focus=quiz_plan["quiz_focus"],
            quiz_style=quiz_plan["quiz_style"]
        )

        result["quiz_plan"] = quiz_plan

    # ------------------------------------------------------------
    # EVALUATE
    # ------------------------------------------------------------
    elif intent == "EVALUATE":
        result = run_answer_evaluation(
            question=extra.get("question", ""),
            correct_answer=extra.get("correct_answer", ""),
            student_answer=extra.get("student_answer", ""),
            student_id=student_id,
            subject_id=subject_id
        )

    # ------------------------------------------------------------
    # EXPLAIN
    # ------------------------------------------------------------
    elif intent == "EXPLAIN":
        chunks = retrieve_similar_chunks(
            query=request,
            document_id=document_id,
            top_k=5
        )

        result = run_explanation(
            concept=request,
            chunks=chunks,
            student_id=student_id,
            subject_id=subject_id
        )

    # ------------------------------------------------------------
    # FALLBACK
    # ------------------------------------------------------------
    else:
        result = {
            "agent": "orchestrator",
            "answer": "I could not understand your request."
        }

    result["intent"] = intent
    result["student_id"] = student_id
    result["subject_id"] = subject_id
    result["document_id"] = document_id

    return result