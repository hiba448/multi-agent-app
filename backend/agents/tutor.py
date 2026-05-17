import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session as DBSession

from db.models import engine, WeakTopic, QuizResult, Student

load_dotenv()

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL"),
    base_url=os.getenv("OLLAMA_BASE_URL"),
    temperature=0.5
)

QUIZ_PROMPT = ChatPromptTemplate.from_template("""
You are the Tutor Agent, responsible for generating practice questions 
to reinforce student understanding of lecture content.

Generate {num_questions} questions based on the following lecture content.
Focus especially on these weak topics if provided: {weak_topics}

LECTURE CONTENT:
{content}

Respond in the following format exactly, repeating for each question:

QUESTION 1:
<question text>
A) <option>
B) <option>
C) <option>
D) <option>
ANSWER: <correct letter>
EXPLANATION: <why this answer is correct>

QUESTION 2:
...
""")

EVALUATE_PROMPT = ChatPromptTemplate.from_template("""
You are the Tutor Agent evaluating a student's answer to a practice question.

QUESTION:
{question}

CORRECT ANSWER:
{correct_answer}

STUDENT ANSWER:
{student_answer}

Evaluate the student's answer and respond in the following format exactly:

CORRECT: <YES or NO>
SCORE: <a number between 0 and 1>
FEEDBACK: <constructive feedback explaining what was right or wrong>
WEAK TOPIC: <the specific topic or concept the student struggles with, or NONE if the answer was correct>
""")

EXPLAIN_PROMPT = ChatPromptTemplate.from_template("""
You are the Tutor Agent. A student is struggling to understand a concept 
and needs a clear, accessible explanation.

CONCEPT TO EXPLAIN:
{concept}

LECTURE CONTEXT:
{context}

STUDENT WEAK TOPICS (for personalization):
{weak_topics}

Provide a clear explanation of the concept using:
- A simple definition
- A concrete real-world example
- A connection to what was covered in the lecture

Keep the explanation concise and adapted to a university student level.
""")


def get_student_weak_topics(student_id: int) -> List[str]:
    """Retrieve the list of weak topics for a student."""
    with DBSession(engine) as session:
        topics = session.query(WeakTopic).filter(
            WeakTopic.student_id == student_id
        ).all()
        return [t.topic for t in topics]


def save_weak_topic(student_id: int, topic: str):
    """Save a newly detected weak topic for a student."""
    with DBSession(engine) as session:
        # avoid duplicates
        existing = session.query(WeakTopic).filter(
            WeakTopic.student_id == student_id,
            WeakTopic.topic == topic
        ).first()

        if not existing:
            session.add(WeakTopic(
                student_id=student_id,
                topic=topic
            ))
            session.commit()


def save_quiz_result(
    student_id: int,
    question: str,
    student_answer: str,
    is_correct: bool,
    score: float
):
    """Persist a quiz result to the database."""
    with DBSession(engine) as session:
        session.add(QuizResult(
            student_id=student_id,
            question=question,
            student_answer=student_answer,
            is_correct=is_correct,
            score=score
        ))
        session.commit()


def parse_quiz_response(response_text: str) -> List[Dict]:
    """Parse the structured quiz response into a list of questions."""
    questions = []
    current = {}
    lines = response_text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("QUESTION"):
            if current:
                questions.append(current)
            current = {"question": "", "options": {}, "answer": "", "explanation": ""}
        elif current:
            if line.startswith("A)"):
                current["options"]["A"] = line[2:].strip()
            elif line.startswith("B)"):
                current["options"]["B"] = line[2:].strip()
            elif line.startswith("C)"):
                current["options"]["C"] = line[2:].strip()
            elif line.startswith("D)"):
                current["options"]["D"] = line[2:].strip()
            elif line.startswith("ANSWER:"):
                current["answer"] = line.replace("ANSWER:", "").strip()
            elif line.startswith("EXPLANATION:"):
                current["explanation"] = line.replace("EXPLANATION:", "").strip()
            elif not any(line.startswith(k) for k in ["A)", "B)", "C)", "D)"]):
                if current["question"] == "":
                    current["question"] = line

    if current:
        questions.append(current)

    return questions


def parse_evaluation_response(response_text: str) -> Dict:
    """Parse the evaluation response from the Tutor Agent."""
    result = {
        "correct": False,
        "score": 0.0,
        "feedback": "",
        "weak_topic": None
    }

    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("CORRECT:"):
            result["correct"] = "YES" in line.upper()
        elif line.startswith("SCORE:"):
            try:
                result["score"] = float(line.replace("SCORE:", "").strip())
            except ValueError:
                result["score"] = 1.0 if result["correct"] else 0.0
        elif line.startswith("FEEDBACK:"):
            result["feedback"] = line.replace("FEEDBACK:", "").strip()
        elif line.startswith("WEAK TOPIC:"):
            topic = line.replace("WEAK TOPIC:", "").strip()
            result["weak_topic"] = None if topic == "NONE" else topic

    return result


def run_quiz_generation(
    chunks: List[Dict],
    student_id: int,
    num_questions: int = 3
) -> Dict:
    """Generate a quiz based on lecture content."""
    weak_topics = get_student_weak_topics(student_id)
    weak_topics_str = ", ".join(weak_topics) if weak_topics else "None identified yet"

    content = "\n\n".join([
        "Page " + str(c["page"]) + ":\n" + c["content"]
        for c in chunks
    ])

    if len(content) > 6000:
        content = content[:6000] + "\n...[content truncated]"

    prompt = QUIZ_PROMPT.format_messages(
        num_questions=num_questions,
        weak_topics=weak_topics_str,
        content=content
    )

    response = llm.invoke(prompt)
    questions = parse_quiz_response(response.content)

    return {
        "agent": "tutor",
        "action": "quiz",
        "questions": questions,
        "num_questions": len(questions)
    }


def run_answer_evaluation(
    question: str,
    correct_answer: str,
    student_answer: str,
    student_id: int
) -> Dict:
    """Evaluate a student answer and update weak topics."""
    prompt = EVALUATE_PROMPT.format_messages(
        question=question,
        correct_answer=correct_answer,
        student_answer=student_answer
    )

    response = llm.invoke(prompt)
    evaluation = parse_evaluation_response(response.content)

    # persist result
    save_quiz_result(
        student_id=student_id,
        question=question,
        student_answer=student_answer,
        is_correct=evaluation["correct"],
        score=evaluation["score"]
    )

    # update weak topics if answer was wrong
    if not evaluation["correct"] and evaluation["weak_topic"]:
        save_weak_topic(student_id, evaluation["weak_topic"])

    return {
        "agent": "tutor",
        "action": "evaluate",
        "correct": evaluation["correct"],
        "score": evaluation["score"],
        "feedback": evaluation["feedback"],
        "weak_topic_detected": evaluation["weak_topic"]
    }


def run_explanation(
    concept: str,
    chunks: List[Dict],
    student_id: int
) -> Dict:
    """Explain a concept adapted to the student's weak topics."""
    weak_topics = get_student_weak_topics(student_id)
    weak_topics_str = ", ".join(weak_topics) if weak_topics else "None identified yet"

    context = "\n\n".join([
        "Page " + str(c["page"]) + ":\n" + c["content"]
        for c in chunks[:3]
    ])

    prompt = EXPLAIN_PROMPT.format_messages(
        concept=concept,
        context=context,
        weak_topics=weak_topics_str
    )

    response = llm.invoke(prompt)

    return {
        "agent": "tutor",
        "action": "explain",
        "concept": concept,
        "explanation": response.content
    }