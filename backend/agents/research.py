import os
from typing import Dict

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools import DuckDuckGoSearchRun

from db.vector_store import retrieve_similar_chunks

load_dotenv()

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL"),
    base_url=os.getenv("OLLAMA_BASE_URL"),
    temperature=0.3
)

search_tool = DuckDuckGoSearchRun()


# =============================================================================
# PROMPTS
# =============================================================================
RESEARCH_PROMPT = ChatPromptTemplate.from_template("""
You are the Research Agent.

Your role is to answer student questions and explain lecture concepts using the
uploaded lecture document as the main source.

Use the retrieved lecture excerpts below to construct your answer.
If the student asks for an explanation, explain the concept clearly and simply.
If the excerpts do not contain enough information to answer fully, explicitly
state that the lecture content is not sufficient.

Do not fabricate information.
Do not answer unrelated questions.

RETRIEVED LECTURE EXCERPTS:
{context}

STUDENT QUESTION:
{question}

Respond in the following format exactly:

ANSWER:
<your answer here>

SOURCES:
- Page <number>: <brief description of what was found on that page>

SUFFICIENT:
<YES or NO — whether the lecture content was sufficient to answer the question>
""")


ENRICHMENT_PROMPT = ChatPromptTemplate.from_template("""
You are the Research Agent.

The uploaded lecture content was not sufficient to fully answer the student's
question, so web search results were retrieved to enrich the answer.

Important:
- Clearly mention that the answer was enriched using web search.
- Keep the answer academic and helpful.
- Separate what comes from the lecture from what comes from the web when possible.
- Do not invent sources.
- If the web results are limited, say so.

WEB SEARCH RESULTS:
{web_results}

ORIGINAL QUESTION:
{question}

PARTIAL ANSWER FROM LECTURE:
{partial_answer}

Respond in the following format:

ANSWER:
<complete answer here, clearly mentioning web enrichment>
""")


OFF_TOPIC_PROMPT = ChatPromptTemplate.from_template("""
You are a strict relevance checker for an academic lecture companion.

A student has uploaded a lecture document and is asking a question.
Your job is to determine whether the question is related to the academic content
of the provided lecture excerpts.

LECTURE EXCERPTS:
{context}

STUDENT QUESTION:
{question}

Is this question related to the lecture content or to the same academic subject?
Answer with exactly one word: YES or NO.
""")


# =============================================================================
# PARSING HELPERS
# =============================================================================
def parse_research_response(response_text: str) -> Dict:
    """
    Parse the structured response from the Research Agent.
    """
    result = {
        "answer": "",
        "sources": [],
        "sufficient": True
    }

    current_section = None
    lines = response_text.strip().split("\n")

    for line in lines:
        line = line.strip()

        if not line:
            continue

        upper_line = line.upper()

        if upper_line.startswith("ANSWER:"):
            current_section = "answer"
            possible_answer = line.split(":", 1)[1].strip()
            if possible_answer:
                result["answer"] += possible_answer + " "

        elif upper_line.startswith("SOURCES:"):
            current_section = "sources"

        elif upper_line.startswith("SUFFICIENT:"):
            value = line.split(":", 1)[1].strip().upper()
            result["sufficient"] = value.startswith("YES")

        elif current_section == "answer":
            result["answer"] += line + " "

        elif current_section == "sources" and line.startswith("-"):
            result["sources"].append(line[1:].strip())

    result["answer"] = result["answer"].strip()

    return result


def parse_enriched_response(response_text: str) -> str:
    """
    Extract the answer from the web-enriched response.
    """
    clean_text = response_text.strip()

    if clean_text.upper().startswith("ANSWER:"):
        return clean_text.split(":", 1)[1].strip()

    return clean_text


def is_question_on_topic(question: str, context: str) -> bool:
    """
    Check whether the student question is related to the lecture content
    or at least to the same academic subject.
    """
    prompt = OFF_TOPIC_PROMPT.format_messages(
        context=context,
        question=question
    )

    response = llm.invoke(prompt)
    answer = response.content.strip().upper()

    return answer.startswith("YES")


# =============================================================================
# CONFIG
# =============================================================================
DISTANCE_THRESHOLD = 0.5


# =============================================================================
# MAIN RESEARCH AGENT
# =============================================================================
def run_research_agent(
    question: str,
    document_id: int,
    top_k: int = 5
) -> Dict:
    """
    Research Agent.

    Responsibilities:
    - answer student questions
    - explain lecture concepts
    - ground answers in the uploaded document
    - use web search when the lecture content is insufficient
    - clearly mention when web search was used

    The Tutor Agent should not answer normal student questions.
    """

    chunks = retrieve_similar_chunks(
        query=question,
        document_id=document_id,
        top_k=top_k
    )

    if not chunks:
        return {
            "agent": "research",
            "answer": "No relevant content was found in the uploaded lecture.",
            "explanation": "No relevant content was found in the uploaded lecture.",
            "sources": [],
            "web_enriched": False,
            "web_results_used": None,
            "off_topic": False,
            "chunks_used": 0
        }

    context = "\n\n".join([
        "Page " + str(chunk["page"]) + ":\n" + chunk["content"]
        for chunk in chunks
    ])

    # ------------------------------------------------------------
    # Off-topic check
    # ------------------------------------------------------------
    if not is_question_on_topic(question, context):
        answer = (
            "Your question does not appear to be related to the lecture you uploaded. "
            "This assistant is focused on the content of your current document and "
            "its academic subject. If you would like to discuss a different topic, "
            "please create or open a more appropriate subject and upload a relevant document."
        )

        return {
            "agent": "research",
            "answer": answer,
            "explanation": answer,
            "sources": [],
            "web_enriched": False,
            "web_results_used": None,
            "off_topic": True,
            "chunks_used": len(chunks)
        }

    # ------------------------------------------------------------
    # Lecture-grounded answer
    # ------------------------------------------------------------
    prompt = RESEARCH_PROMPT.format_messages(
        context=context,
        question=question
    )

    response = llm.invoke(prompt)
    parsed = parse_research_response(response.content)

    best_distance = chunks[0].get("distance", 0.0)

    try:
        best_distance = float(best_distance)
    except Exception:
        best_distance = 0.0

    web_enriched = False
    web_results_used = None

    lecture_insufficient = not parsed.get("sufficient", True)
    semantically_distant = best_distance > DISTANCE_THRESHOLD

    # ------------------------------------------------------------
    # Web enrichment when lecture content is insufficient
    # ------------------------------------------------------------
    if lecture_insufficient or semantically_distant:
        try:
            web_results = search_tool.run(question)
            web_results_used = web_results

            enrich_prompt = ENRICHMENT_PROMPT.format_messages(
                web_results=web_results,
                question=question,
                partial_answer=parsed["answer"]
            )

            enriched_response = llm.invoke(enrich_prompt)
            enriched_answer = parse_enriched_response(enriched_response.content)

            if "web" not in enriched_answer.lower():
                enriched_answer = (
                    "Note: This answer was enriched using web search because the "
                    "uploaded lecture content was not sufficient to answer fully.\n\n"
                    + enriched_answer
                )

            parsed["answer"] = enriched_answer
            web_enriched = True

        except Exception as e:
            parsed["answer"] += (
                "\n\nThe lecture content was not sufficient for a complete answer, "
                "and web enrichment was attempted but failed: " + str(e)
            )

    return {
        "agent": "research",
        "answer": parsed["answer"],
        "explanation": parsed["answer"],
        "sources": parsed["sources"],
        "web_enriched": web_enriched,
        "web_results_used": web_results_used,
        "best_chunk_distance": best_distance,
        "chunks_used": len(chunks),
        "off_topic": False
    }