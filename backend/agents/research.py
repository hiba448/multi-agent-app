import os
from typing import List, Dict
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

RESEARCH_PROMPT = ChatPromptTemplate.from_template("""
You are the Research Agent, responsible for answering student questions 
accurately and exclusively based on the provided lecture content.

Use the retrieved lecture excerpts below to construct your answer.
If the excerpts do not contain sufficient information to answer the question,
explicitly state that the answer is not covered in the lecture.
Do not fabricate or assume information.

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
You are the Research Agent. The lecture content was insufficient to fully 
answer the student's question. You have retrieved the following supplementary 
information from the web.

WEB SEARCH RESULTS:
{web_results}

ORIGINAL QUESTION:
{question}

PARTIAL ANSWER FROM LECTURE:
{partial_answer}

Provide a complete, academic answer that combines the lecture content 
with the web results. Clearly indicate which parts come from the web.

ANSWER:
<your complete answer here>
""")
OFF_TOPIC_PROMPT = ChatPromptTemplate.from_template("""
You are a strict relevance checker for an academic lecture companion.

A student has uploaded a lecture document and is asking a question.
Your job is to determine whether the question is related to the 
academic content of the provided lecture excerpts.

LECTURE EXCERPTS:
{context}

STUDENT QUESTION:
{question}

Is this question related to the lecture content?
Answer with exactly one word: YES or NO.
""")





def parse_research_response(response_text: str) -> Dict:
    """Parse the structured response from the Research Agent."""
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

        if line.startswith("ANSWER:"):
            current_section = "answer"
        elif line.startswith("SOURCES:"):
            current_section = "sources"
        elif line.startswith("SUFFICIENT:"):
            value = line.replace("SUFFICIENT:", "").strip().upper()
            result["sufficient"] = value == "YES"
        elif current_section == "answer":
            result["answer"] += line + " "
        elif current_section == "sources" and line.startswith("-"):
            result["sources"].append(line[1:].strip())

    result["answer"] = result["answer"].strip()
    return result

def is_question_on_topic(question: str, context: str) -> bool:
    """Check whether the student question is related to the lecture content."""
    prompt = OFF_TOPIC_PROMPT.format_messages(
        context=context,
        question=question
    )
    response = llm.invoke(prompt)
    answer = response.content.strip().upper()
    return "YES" in answer


DISTANCE_THRESHOLD = 0.5  # below this = lecture content is sufficient

def run_research_agent(
    question: str,
    document_id: int,
    top_k: int = 5
) -> Dict:

    chunks = retrieve_similar_chunks(
        query=question,
        document_id=document_id,
        top_k=top_k
    )

    if not chunks:
        return {
            "agent": "research",
            "answer": "No relevant content was found in the uploaded lecture.",
            "sources": [],
            "web_enriched": False,
            "off_topic": False
        }

    context = "\n\n".join([
        "Page " + str(chunk["page"]) + ":\n" + chunk["content"]
        for chunk in chunks
    ])

    # off-topic check before doing anything else
    if not is_question_on_topic(question, context):
        return {
            "agent": "research",
            "answer": (
                "Your question does not appear to be related to the lecture you uploaded. "
                "This assistant is focused exclusively on the content of your current document. "
                "If you would like to discuss a different topic, please start a new session "
                "and upload a relevant document."
            ),
            "sources": [],
            "web_enriched": False,
            "off_topic": True
        }

    # continue with normal flow
    prompt = RESEARCH_PROMPT.format_messages(
        context=context,
        question=question
    )
    response = llm.invoke(prompt)
    parsed = parse_research_response(response.content)

    best_distance = chunks[0]["distance"]
    web_enriched = False

    if best_distance > DISTANCE_THRESHOLD:
        try:
            web_results = search_tool.run(question)
            enrich_prompt = ENRICHMENT_PROMPT.format_messages(
                web_results=web_results,
                question=question,
                partial_answer=parsed["answer"]
            )
            enriched_response = llm.invoke(enrich_prompt)
            parsed["answer"] = enriched_response.content
            web_enriched = True
        except Exception as e:
            parsed["answer"] += " (Web enrichment failed: " + str(e) + ")"

    return {
        "agent": "research",
        "answer": parsed["answer"],
        "sources": parsed["sources"],
        "web_enriched": web_enriched,
        "best_chunk_distance": best_distance,
        "chunks_used": len(chunks),
        "off_topic": False
    }