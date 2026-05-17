import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL"),
    base_url=os.getenv("OLLAMA_BASE_URL"),
    temperature=0.3
)

SCRIBE_PROMPT = ChatPromptTemplate.from_template("""
You are the Scribe Agent, responsible for analyzing academic lecture content 
and producing structured study material.

Given the following lecture content, extract and organize:
1. A concise summary of the lecture (3-5 sentences)
2. The key concepts covered (as a list)
3. Important definitions (term: definition format)

Be precise and academic. Do not add information not present in the content.

LECTURE CONTENT:
{content}

Respond in the following format exactly:

SUMMARY:
<your summary here>

KEY CONCEPTS:
- <concept 1>
- <concept 2>
- <concept 3>

DEFINITIONS:
- <term 1>: <definition>
- <term 2>: <definition>
""")


def parse_scribe_response(response_text: str) -> Dict:
    """Parse the structured response from the Scribe Agent."""
    result = {
        "summary": "",
        "key_concepts": [],
        "definitions": {}
    }

    current_section = None
    lines = response_text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("SUMMARY:"):
            current_section = "summary"
        elif line.startswith("KEY CONCEPTS:"):
            current_section = "key_concepts"
        elif line.startswith("DEFINITIONS:"):
            current_section = "definitions"
        elif current_section == "summary":
            result["summary"] += line + " "
        elif current_section == "key_concepts" and line.startswith("-"):
            result["key_concepts"].append(line[1:].strip())
        elif current_section == "definitions" and line.startswith("-"):
            if ":" in line:
                term, definition = line[1:].split(":", 1)
                result["definitions"][term.strip()] = definition.strip()

    result["summary"] = result["summary"].strip()
    return result


def run_scribe_agent(chunks: List[Dict]) -> Dict:
    """
    Main entry point for the Scribe Agent.
    Takes parsed document chunks and returns structured study material.
    """
    # Combine all chunks into one content block
    full_content = "\n\n".join([
        f"[Page {chunk['page']}]\n{chunk['content']}"
        for chunk in chunks
    ])

    # Truncate if too long for the model context window
    if len(full_content) > 6000:
        full_content = full_content[:6000] + "\n...[content truncated]"

    prompt = SCRIBE_PROMPT.format_messages(content=full_content)
    response = llm.invoke(prompt)
    parsed = parse_scribe_response(response.content)

    return {
        "agent": "scribe",
        "summary": parsed["summary"],
        "key_concepts": parsed["key_concepts"],
        "definitions": parsed["definitions"],
        "raw": response.content
    }