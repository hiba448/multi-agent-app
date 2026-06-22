import os
import json
import re
from typing import List, Dict, Optional

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session as DBSession

from db.models import engine, WeakTopic, QuizResult, TopicProgress

load_dotenv()

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL"),
    base_url=os.getenv("OLLAMA_BASE_URL"),
    temperature=0.5
)


# -------------------------------------------------------------------
# Prompts
# -------------------------------------------------------------------
QUIZ_PROMPT = ChatPromptTemplate.from_template("""
You are the Tutor Agent, responsible for generating practice questions
to reinforce student understanding of lecture content.

Generate {num_questions} questions based on the following lecture content.

Requested quiz focus:
{quiz_focus}

Requested quiz style:
{quiz_style}

Focus especially on these weak topics if provided:
{weak_topics}

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
<question text>
A) <option>
B) <option>
C) <option>
D) <option>
ANSWER: <correct letter>
EXPLANATION: <why this answer is correct>
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
""")


EXPLAIN_PROMPT = ChatPromptTemplate.from_template("""
You are the Tutor Agent. A student is struggling to understand a concept
and needs a clear, accessible explanation.

CONCEPT TO EXPLAIN:
{concept}

LECTURE CONTEXT:
{context}

STUDENT WEAK TOPICS FOR THIS SUBJECT:
{weak_topics}

Provide a clear explanation of the concept using:
- A simple definition
- A concrete real-world example
- A connection to what was covered in the lecture

Keep the explanation concise and adapted to a university student level.
""")


QUIZ_ANALYSIS_PROMPT = ChatPromptTemplate.from_template("""
You are the Tutor Agent analyzing a student's FULL quiz attempt.

Important rule:
Do NOT identify a weak topic from only one wrong answer.
Weak topics must be inferred from the overall quiz performance, repeated errors,
patterns of misunderstanding, and the concepts covered by the quiz.

QUIZ CONTEXT:
Subject: {subject_name}
Discussion: {discussion_title}
Quiz focus: {quiz_focus}
Final score: {score_percent}%

FULL QUIZ ATTEMPT:
{attempt_json}

Analyze the student's performance globally.

Return your answer as valid JSON only, with this exact structure:

{{
  "overall_summary": "short paragraph about the student's performance",
  "weak_topics": [
    {{
      "topic": "topic name",
      "evidence": "why this is considered a weakness based on the full quiz",
      "recommendation": "what the student should review or practice",
      "mastery_status": "needs_practice"
    }}
  ],
  "strong_topics": [
    {{
      "topic": "topic name",
      "evidence": "why this seems strong"
    }}
  ],
  "topic_progress": [
    {{
      "topic": "topic name",
      "score": 0.0,
      "correct_answers": 0,
      "total_questions": 0,
      "analysis": "topic-level analysis",
      "recommendation": "topic-level recommendation"
    }}
  ],
  "global_recommendation": "what the student should do next"
}}

Rules:
- score values must be between 0 and 1.
- weak_topics can be empty if the quiz does not provide enough evidence.
- topic_progress should summarize the main topics covered by the quiz.
- Return JSON only. No markdown. No explanation outside JSON.
""")


# -------------------------------------------------------------------
# Weak topic utilities
# -------------------------------------------------------------------
def get_student_weak_topics(
    student_id: int,
    subject_id: Optional[int] = None
) -> List[str]:
    """
    Retrieve weak topics for a student.
    If subject_id is provided, return only weak topics for that subject.
    """
    with DBSession(engine) as session:
        query = session.query(WeakTopic).filter(
            WeakTopic.student_id == student_id
        )

        if subject_id is not None:
            query = query.filter(
                WeakTopic.subject_id == subject_id
            )

        topics = query.order_by(
            WeakTopic.detected_at.desc()
        ).all()

        return [t.topic for t in topics]


def upsert_weak_topic(
    student_id: int,
    subject_id: int,
    topic: str,
    evidence: Optional[str] = None,
    recommendation: Optional[str] = None,
    mastery_status: Optional[str] = "needs_practice"
) -> WeakTopic:
    """
    Create or update a weak topic.

    Weak topics are now saved from the full quiz analysis,
    not from one wrong answer.
    """
    clean_topic = topic.strip()

    with DBSession(engine) as session:
        existing = session.query(WeakTopic).filter(
            WeakTopic.student_id == student_id,
            WeakTopic.subject_id == subject_id,
            WeakTopic.topic == clean_topic
        ).first()

        if existing:
            existing.evidence = evidence
            existing.recommendation = recommendation
            existing.mastery_status = mastery_status
            session.commit()
            session.refresh(existing)
            return existing

        weak_topic = WeakTopic(
            student_id=student_id,
            subject_id=subject_id,
            topic=clean_topic,
            evidence=evidence,
            recommendation=recommendation,
            mastery_status=mastery_status
        )

        session.add(weak_topic)
        session.commit()
        session.refresh(weak_topic)

        return weak_topic


# -------------------------------------------------------------------
# Quiz result / topic progress utilities
# -------------------------------------------------------------------
def save_quiz_result(
    student_id: int,
    subject_id: int,
    question: str,
    student_answer: str,
    is_correct: bool,
    score: float,
    analysis_report: Optional[str] = None
) -> QuizResult:
    """
    Save one final quiz result.
    """
    with DBSession(engine) as session:
        result = QuizResult(
            student_id=student_id,
            subject_id=subject_id,
            question=question,
            student_answer=student_answer,
            is_correct=is_correct,
            score=score,
            analysis_report=analysis_report
        )

        session.add(result)
        session.commit()
        session.refresh(result)

        return result


def save_topic_progress(
    student_id: int,
    subject_id: int,
    topic: str,
    score: float,
    correct_answers: Optional[int] = None,
    total_questions: Optional[int] = None,
    weak_topic_id: Optional[int] = None,
    quiz_result_id: Optional[int] = None,
    attempt_type: str = "general_quiz",
    analysis: Optional[str] = None,
    recommendation: Optional[str] = None
) -> TopicProgress:
    """
    Save progress for one topic.
    """
    with DBSession(engine) as session:
        progress = TopicProgress(
            student_id=student_id,
            subject_id=subject_id,
            weak_topic_id=weak_topic_id,
            quiz_result_id=quiz_result_id,
            topic=topic,
            score=score,
            correct_answers=correct_answers,
            total_questions=total_questions,
            attempt_type=attempt_type,
            analysis=analysis,
            recommendation=recommendation
        )

        session.add(progress)
        session.commit()
        session.refresh(progress)

        return progress


# -------------------------------------------------------------------
# Parsing helpers
# -------------------------------------------------------------------
def parse_quiz_response(response_text: str) -> List[Dict]:
    """
    Parse the structured quiz response into a list of multiple-choice questions.
    """
    questions = []
    current = {}

    lines = response_text.strip().split("\n")

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.upper().startswith("QUESTION"):
            if current:
                questions.append(current)

            current = {
                "question": "",
                "options": {},
                "answer": "",
                "explanation": ""
            }

        elif current:
            if line.startswith("A)"):
                current["options"]["A"] = line[2:].strip()

            elif line.startswith("B)"):
                current["options"]["B"] = line[2:].strip()

            elif line.startswith("C)"):
                current["options"]["C"] = line[2:].strip()

            elif line.startswith("D)"):
                current["options"]["D"] = line[2:].strip()

            elif line.upper().startswith("ANSWER:"):
                current["answer"] = line.split(":", 1)[1].strip().upper()

            elif line.upper().startswith("EXPLANATION:"):
                current["explanation"] = line.split(":", 1)[1].strip()

            else:
                if current["question"] == "":
                    current["question"] = line
                else:
                    current["question"] += " " + line

    if current:
        questions.append(current)

    return questions


def parse_evaluation_response(response_text: str) -> Dict:
    """
    Parse a single answer evaluation response.
    This no longer saves weak topics.
    """
    result = {
        "correct": False,
        "score": 0.0,
        "feedback": ""
    }

    for line in response_text.strip().split("\n"):
        line = line.strip()

        if line.upper().startswith("CORRECT:"):
            value = line.split(":", 1)[1].strip().upper()
            result["correct"] = value.startswith("YES") or value.startswith("TRUE")

        elif line.upper().startswith("SCORE:"):
            value = line.split(":", 1)[1].strip()

            try:
                result["score"] = float(value)
            except ValueError:
                result["score"] = 1.0 if result["correct"] else 0.0

        elif line.upper().startswith("FEEDBACK:"):
            result["feedback"] = line.split(":", 1)[1].strip()

    return result


def extract_json_from_response(text: str) -> Dict:
    """
    Safely extract JSON from an LLM response.
    """
    clean_text = text.strip()

    try:
        return json.loads(clean_text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", clean_text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return {
        "overall_summary": "The quiz attempt was completed, but the analysis could not be parsed.",
        "weak_topics": [],
        "strong_topics": [],
        "topic_progress": [],
        "global_recommendation": "Review the quiz answers and retry the difficult concepts."
    }


# -------------------------------------------------------------------
# Main Tutor Agent functions
# -------------------------------------------------------------------
def run_quiz_generation(
    chunks: List[Dict],
    student_id: int,
    subject_id: Optional[int] = None,
    num_questions: int = 3,
    quiz_focus: str = "general lecture content",
    quiz_style: str = "standard"
) -> Dict:
    """
    Generate a quiz based on lecture content.

    Later, the orchestrator will pass dynamic num_questions, quiz_focus,
    and quiz_style based on the user's request.
    """
    weak_topics = get_student_weak_topics(
        student_id=student_id,
        subject_id=subject_id
    )

    weak_topics_str = ", ".join(weak_topics) if weak_topics else "None identified yet"

    content = "\n\n".join([
        "Page " + str(c["page"]) + ":\n" + c["content"]
        for c in chunks
    ])

    if len(content) > 8000:
        content = content[:8000] + "\n...[content truncated]"

    prompt = QUIZ_PROMPT.format_messages(
        num_questions=num_questions,
        quiz_focus=quiz_focus,
        quiz_style=quiz_style,
        weak_topics=weak_topics_str,
        content=content
    )

    response = llm.invoke(prompt)
    questions = parse_quiz_response(response.content)

    return {
        "agent": "tutor",
        "action": "quiz",
        "questions": questions,
        "num_questions": len(questions),
        "weak_topics_used": weak_topics,
        "quiz_focus": quiz_focus,
        "quiz_style": quiz_style
    }


def run_answer_evaluation(
    question: str,
    correct_answer: str,
    student_answer: str,
    student_id: int,
    subject_id: Optional[int] = None
) -> Dict:
    """
    Evaluate one answer.

    Important:
    This function does NOT save weak topics anymore.
    Weak topics are detected only after analyzing the full quiz attempt.
    """
    prompt = EVALUATE_PROMPT.format_messages(
        question=question,
        correct_answer=correct_answer,
        student_answer=student_answer
    )

    response = llm.invoke(prompt)
    evaluation = parse_evaluation_response(response.content)

    return {
        "agent": "tutor",
        "action": "evaluate",
        "correct": evaluation["correct"],
        "score": evaluation["score"],
        "feedback": evaluation["feedback"]
    }


def run_explanation(
    concept: str,
    chunks: List[Dict],
    student_id: int,
    subject_id: Optional[int] = None
) -> Dict:
    """
    Explain a concept adapted to the student's subject-specific weak topics.
    """
    weak_topics = get_student_weak_topics(
        student_id=student_id,
        subject_id=subject_id
    )

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
        "explanation": response.content,
        "weak_topics_used": weak_topics
    }


def analyze_full_quiz_attempt(
    student_id: int,
    subject_id: int,
    subject_name: str,
    discussion_title: str,
    quiz_focus: str,
    quiz_answers: List[Dict],
    correct_count: int,
    total_questions: int,
    attempt_type: str = "general_quiz"
) -> Dict:
    """
    Analyze a full quiz attempt.

    This is the new weak-topic logic:
    - analyze all answers together
    - identify weak topics from global patterns
    - save final quiz result
    - save weak topics
    - save topic progress
    """
    final_score = correct_count / total_questions if total_questions else 0.0
    score_percent = round(final_score * 100, 2)

    attempt_payload = {
        "correct_count": correct_count,
        "total_questions": total_questions,
        "score": final_score,
        "answers": quiz_answers
    }

    attempt_json = json.dumps(
        attempt_payload,
        ensure_ascii=False,
        indent=2
    )

    prompt = QUIZ_ANALYSIS_PROMPT.format_messages(
        subject_name=subject_name,
        discussion_title=discussion_title,
        quiz_focus=quiz_focus,
        score_percent=score_percent,
        attempt_json=attempt_json
    )

    response = llm.invoke(prompt)
    analysis = extract_json_from_response(response.content)

    analysis_report = json.dumps(
        analysis,
        ensure_ascii=False,
        indent=2
    )

    question_summary = (
        f"Quiz result for {discussion_title or 'current discussion'} "
        f"({correct_count}/{total_questions})"
    )

    student_answer_summary = "\n".join([
        f"Q{i + 1}: "
        f"{'Correct' if answer.get('is_correct') else 'Incorrect'} | "
        f"Student answer: {answer.get('student_answer')} | "
        f"Correct answer: {answer.get('correct_answer')}"
        for i, answer in enumerate(quiz_answers)
    ])

    quiz_result = save_quiz_result(
        student_id=student_id,
        subject_id=subject_id,
        question=question_summary,
        student_answer=student_answer_summary,
        is_correct=final_score >= 0.5,
        score=final_score,
        analysis_report=analysis_report
    )

    saved_weak_topics = []

    for weak in analysis.get("weak_topics", []):
        topic = str(weak.get("topic", "")).strip()

        if not topic:
            continue

        weak_topic = upsert_weak_topic(
            student_id=student_id,
            subject_id=subject_id,
            topic=topic,
            evidence=weak.get("evidence"),
            recommendation=weak.get("recommendation"),
            mastery_status=weak.get("mastery_status", "needs_practice")
        )

        saved_weak_topics.append({
            "id": weak_topic.id,
            "topic": weak_topic.topic,
            "evidence": weak_topic.evidence,
            "recommendation": weak_topic.recommendation,
            "mastery_status": weak_topic.mastery_status
        })

    saved_topic_progress = []

    for progress in analysis.get("topic_progress", []):
        topic = str(progress.get("topic", "")).strip()

        if not topic:
            continue

        score = progress.get("score", 0.0)

        try:
            score = float(score)
        except Exception:
            score = 0.0

        if score < 0:
            score = 0.0

        if score > 1:
            score = 1.0

        matching_weak_topic = None

        for weak_topic in saved_weak_topics:
            if weak_topic["topic"].lower() == topic.lower():
                matching_weak_topic = weak_topic
                break

        record = save_topic_progress(
            student_id=student_id,
            subject_id=subject_id,
            weak_topic_id=matching_weak_topic["id"] if matching_weak_topic else None,
            quiz_result_id=quiz_result.id,
            topic=topic,
            score=score,
            correct_answers=progress.get("correct_answers"),
            total_questions=progress.get("total_questions"),
            attempt_type=attempt_type,
            analysis=progress.get("analysis"),
            recommendation=progress.get("recommendation")
        )

        saved_topic_progress.append({
            "id": record.id,
            "topic": record.topic,
            "score": record.score,
            "correct_answers": record.correct_answers,
            "total_questions": record.total_questions,
            "analysis": record.analysis,
            "recommendation": record.recommendation
        })

    return {
        "agent": "tutor",
        "action": "full_quiz_analysis",
        "quiz_result_id": quiz_result.id,
        "score": final_score,
        "score_percent": score_percent,
        "correct_count": correct_count,
        "total_questions": total_questions,
        "overall_summary": analysis.get("overall_summary", ""),
        "weak_topics": saved_weak_topics,
        "strong_topics": analysis.get("strong_topics", []),
        "topic_progress": saved_topic_progress,
        "global_recommendation": analysis.get("global_recommendation", ""),
        "analysis_report": analysis
    }