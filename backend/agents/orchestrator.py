import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from typing import TypedDict

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


# LangGraph state definition
class AgentState(TypedDict):
    request: str
    intent: str
    document_id: int
    student_id: int
    extra: Dict        # carries evaluate-specific fields
    result: Dict       # final output


# --- Node functions ---

def classify_intent(state: AgentState) -> AgentState:
    """Classify the student request into one of the defined intents."""
    prompt = INTENT_PROMPT.format_messages(request=state["request"])
    response = llm.invoke(prompt)
    intent = response.content.strip().upper()

    valid_intents = {"SUMMARIZE", "QUESTION", "QUIZ", "EVALUATE", "EXPLAIN"}
    if intent not in valid_intents:
        intent = "QUESTION"  # safe fallback

    state["intent"] = intent
    return state


def route(state: AgentState) -> str:
    """Route to the correct agent node based on classified intent."""
    return state["intent"]


def run_scribe(state: AgentState) -> AgentState:
    """Fetch chunks and run the Scribe Agent."""
    chunks = retrieve_similar_chunks(
        query="lecture summary overview",
        document_id=state["document_id"],
        top_k=10
    )
    state["result"] = run_scribe_agent(chunks)
    return state


def run_research(state: AgentState) -> AgentState:
    """Run the Research Agent on the student question."""
    state["result"] = run_research_agent(
        question=state["request"],
        document_id=state["document_id"]
    )
    return state


def run_quiz(state: AgentState) -> AgentState:
    """Fetch chunks and run quiz generation."""
    chunks = retrieve_similar_chunks(
        query="key concepts definitions important topics",
        document_id=state["document_id"],
        top_k=10
    )
    state["result"] = run_quiz_generation(
        chunks=chunks,
        student_id=state["student_id"]
    )
    return state


def run_evaluate(state: AgentState) -> AgentState:
    """Run answer evaluation with fields from extra."""
    state["result"] = run_answer_evaluation(
        question=state["extra"].get("question", ""),
        correct_answer=state["extra"].get("correct_answer", ""),
        student_answer=state["extra"].get("student_answer", ""),
        student_id=state["student_id"]
    )
    return state


def run_explain(state: AgentState) -> AgentState:
    """Fetch chunks and run concept explanation."""
    chunks = retrieve_similar_chunks(
        query=state["request"],
        document_id=state["document_id"],
        top_k=5
    )
    state["result"] = run_explanation(
        concept=state["request"],
        chunks=chunks,
        student_id=state["student_id"]
    )
    return state


def compile_response(state: AgentState) -> AgentState:
    """Attach metadata to the final result."""
    state["result"]["intent"] = state["intent"]
    state["result"]["student_id"] = state["student_id"]
    state["result"]["document_id"] = state["document_id"]
    return state


# --- Build the LangGraph ---

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # add nodes
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("compile_response", compile_response)
    graph.add_node("SUMMARIZE", run_scribe)
    graph.add_node("QUESTION", run_research)
    graph.add_node("QUIZ", run_quiz)
    graph.add_node("EVALUATE", run_evaluate)
    graph.add_node("EXPLAIN", run_explain)

    # entry point
    graph.set_entry_point("classify_intent")

    # conditional routing after classification
    graph.add_conditional_edges(
        "classify_intent",
        route,
        {
            "SUMMARIZE": "SUMMARIZE",
            "QUESTION":  "QUESTION",
            "QUIZ":      "QUIZ",
            "EVALUATE":  "EVALUATE",
            "EXPLAIN":   "EXPLAIN"
        }
    )

    # all agent nodes lead to compile_response then END
    for node in ["SUMMARIZE", "QUESTION", "QUIZ", "EVALUATE", "EXPLAIN"]:
        graph.add_edge(node, "compile_response")

    graph.add_edge("compile_response", END)

    return graph.compile()


# compile once at import time
orchestrator = build_graph()


def run_orchestrator(
    request: str,
    document_id: int,
    student_id: int,
    extra: Optional[Dict] = None
) -> Dict:
    # if evaluation fields are present, skip classification
    extra = extra or {}
    forced_intent = None

    if all(k in extra for k in ["question", "correct_answer", "student_answer"]):
        forced_intent = "EVALUATE"

    initial_state: AgentState = {
        "request": request,
        "intent": forced_intent or "",
        "document_id": document_id,
        "student_id": student_id,
        "extra": extra,
        "result": {}
    }

    # if intent is forced, skip the classify_intent node
    if forced_intent:
        state = initial_state
        state = run_evaluate(state)
        state = compile_response(state)
        return state["result"]

    final_state = orchestrator.invoke(initial_state)
    return final_state["result"]