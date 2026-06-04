import re
from docx import Document


def parse_quiz_docx(file_path: str) -> tuple[str, list[dict]]:
    """
    Parse .docx file and return (quiz_title, questions)
    
    Expected format:
    # QUIZ: Quiz nomi
    
    Q1: Savol matni
    A) Javob 1
    B) Javob 2
    C) Javob 3
    D) Javob 4
    ANSWER: B
    
    Q2: ...
    """
    doc = Document(file_path)
    lines = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            lines.append(text)

    title = "Quiz"
    questions = []
    i = 0

    # Find title
    for line in lines:
        if line.upper().startswith("# QUIZ:"):
            title = line.split(":", 1)[1].strip()
            break

    # Parse questions
    current_q = None
    options = []
    answer = None

    for line in lines:
        # Skip title line
        if line.upper().startswith("# QUIZ:"):
            continue

        # New question
        q_match = re.match(r'^Q\d+[:.]\s*(.+)', line, re.IGNORECASE)
        if q_match:
            # Save previous question
            if current_q and options and answer:
                questions.append({
                    "question": current_q,
                    "options": options,
                    "answer": answer
                })
            current_q = q_match.group(1).strip()
            options = []
            answer = None
            continue

        # Option lines A) B) C) D)
        opt_match = re.match(r'^([A-D])[).]\s*(.+)', line, re.IGNORECASE)
        if opt_match and current_q:
            letter = opt_match.group(1).upper()
            text = opt_match.group(2).strip()
            options.append({"letter": letter, "text": text})
            continue

        # Answer line
        ans_match = re.match(r'^ANSWER:\s*([A-D])', line, re.IGNORECASE)
        if ans_match and current_q:
            answer = ans_match.group(1).upper()
            continue

    # Save last question
    if current_q and options and answer:
        questions.append({
            "question": current_q,
            "options": options,
            "answer": answer
        })

    return title, questions
