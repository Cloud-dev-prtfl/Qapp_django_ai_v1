import json
import time
import re
from openai import OpenAI
from django.conf import settings
# NEW: Import model to update status
from .models import ExamSession 

# Initialize OpenAI client with Gemini Base URL
client = OpenAI(
    api_key=settings.GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def clean_json_string(json_string):
    """
    Sanitizes the string to handle common LLM JSON formatting errors.
    """
    if not json_string:
        return ""

    # 1. Remove Markdown code blocks
    json_string = re.sub(r'^```json\s*', '', json_string)
    json_string = re.sub(r'^```\s*', '', json_string)
    json_string = re.sub(r'\s*```$', '', json_string)
    
    # 2. Strip whitespace
    json_string = json_string.strip()

    return json_string

def generate_questions_agent(exam_session, feedback_history=None):
    """
    Agent 1: Generates questions using 'gemini-2.0-flash-exp'.
    """
    topic = exam_session.coding_languages if not exam_session.general_topic else "General Programming & Computer Science"
    
    # Base instructions
    base_prompt = f"""
    You are an expert Technical Interviewer and Exam Setter.
    
    **YOUR OBJECTIVE:**
    Generate a high-quality technical exam JSON strictly following the configuration below.
    
    **CONFIGURATION:**
    - **Difficulty:** {exam_session.difficulty_level}
    - **Experience:** {exam_session.experience_level}
    - **Topic:** {topic}
    - **Count:** {exam_session.num_questions}
    - **Format:** {'MCQ' if exam_session.mcq_format else 'Subjective'}
    - **Instructions:** {exam_session.specific_instructions or "None"}
    
    **CRITICAL JSON FORMATTING RULES:**
    1. Output **ONLY** valid JSON. No introductory text, no markdown, no explanations.
    2. **ESCAPE ALL SPECIAL CHARACTERS** inside strings. 
       - Use `\\n` for newlines.
       - Use `\\t` for tabs.
       - Use `\\"` for quotes inside strings.
    3. Do NOT include real (unescaped) newlines or control characters within string values.
    
    **REQUIRED JSON STRUCTURE:**
    {{
        "exam_title": "String",
        "summary": "String",
        "questions": [
            {{
                "id": 1,
                "type": "{'MCQ' if exam_session.mcq_format else 'Subjective'}",
                "question_text": "String (Escape quotes and newlines properly)",
                "options": ["A", "B", "C", "D"], (If MCQ)
                "correct_answer": "String",
                "explanation": "String"
            }}
        ]
    }}
    """

    if feedback_history:
        base_prompt += f"\n\n**PREVIOUS ATTEMPT FEEDBACK (FIX THESE ISSUES):**\n{feedback_history}"

    try:
        response = client.chat.completions.create(
            model="gemini-2.5-flash", 
            messages=[
                {"role": "system", "content": "You are a strict JSON generator. You output only valid JSON."},
                {"role": "user", "content": base_prompt}
            ],
            temperature=0.7 if not feedback_history else 0.8,
            # Enforce JSON mode to reduce formatting errors
            response_format={ "type": "json_object" } 
        )
        
        raw_content = response.choices[0].message.content
        cleaned_content = clean_json_string(raw_content)
        
        return json.loads(cleaned_content, strict=False)

    except json.JSONDecodeError as je:
        print(f"Agent 1 JSON Decode Error: {je}")
        return None
    except Exception as e:
        print(f"Agent 1 General Error: {e}")
        return None

def evaluate_agent(questions_data, exam_session):
    """
    Agent 2 (Part A): Evaluator.
    Uses 'gemini-2.5-pro' for superior reasoning on quality checks.
    """
    if not questions_data:
        return 0, "No data generated."

    system_prompt = f"""
    You are a Strict Quality Assurance AI.
    Evaluate the provided Exam JSON against these requirements:
    - Topic: {exam_session.coding_languages or "General"}
    - Difficulty: {exam_session.difficulty_level}
    - Question Count: {exam_session.num_questions}
    
    Output strictly valid JSON:
    {{
        "score": (Integer 0-100),
        "approved": (Boolean, true if score > 85),
        "feedback": "Short specific string describing what is wrong. If perfect, write 'Looks good'."
    }}
    
    Exam Data to Evaluate:
    {json.dumps(questions_data)}
    """

    try:
        response = client.chat.completions.create(
            model="gemini-2.5-pro", 
            messages=[
                {"role": "system", "content": "You are a JSON scoring bot. Output only JSON."},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.3,
            response_format={ "type": "json_object" }
        )
        
        raw_content = response.choices[0].message.content
        cleaned_content = clean_json_string(raw_content)
        
        result = json.loads(cleaned_content, strict=False)
        return result.get("score", 0), result.get("feedback", "No feedback")

    except Exception as e:
        print(f"Evaluator Error: {e}")
        return 50, "Evaluation failed."

def format_html_agent(questions_data):
    """
    Agent 2 (Part B): HTML Formatter.
    Uses 'gemini-2.5-pro' to ensure complex HTML structures are generated correctly.
    """
    json_input = json.dumps(questions_data)
    system_prompt = f"""
    Convert this Exam JSON into a clean HTML structure.
    
    **Styling Classes (Mandatory):**
    - Wrapper: `exam-preview-wrapper`
    - Header: `exam-title` (h2), `exam-summary` (p)
    - Card: `question-card`
    - Text: `question-text`
    - MCQ Grid: `options-grid` -> `option-item`
    - Correct Answer: Add class `correct-answer` to the correct `option-item`.
    - Explanation: `explanation-box`

    Input: {json_input}
    Output: Raw HTML string only. No Markdown.
    """

    try:
        response = client.chat.completions.create(
            model="gemini-2.5-pro", 
            messages=[{"role": "user", "content": system_prompt}],
            temperature=0.3,
        )
        
        content = response.choices[0].message.content.strip()
        # Clean markdown if present
        content = re.sub(r'^```html\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        return content
    except Exception as e:
        return f"<p>Error formatting HTML: {e}</p>"

def orchestrated_exam_flow(exam_session_id):
    """
    Coordinator Function:
    Manages the loop: Generate -> Evaluate -> (Retry if needed) -> Format.
    Enforces strict 20-second timeout and handles CANCELLATION.
    """
    try:
        # Fetch fresh object from DB using ID
        session = ExamSession.objects.get(id=exam_session_id)
        session.status = 'PROCESSING'
        session.save()

        start_time = time.time()
        max_loop_duration = 16  
        
        best_draft = None
        best_score = -1
        feedback = None
        attempt = 1

        print(f"--- Starting Async AI Flow for Session {exam_session_id} ---")

        while (time.time() - start_time) < max_loop_duration:
            # --- CHECK CANCELLATION ---
            session.refresh_from_db()
            if session.status == 'CANCELLED':
                print(f"Session {exam_session_id} CANCELLED by user.")
                return 

            print(f"[Attempt {attempt}] Generating... (Time elapsed: {time.time() - start_time:.2f}s)")
            
            # 1. Generate (Agent 1)
            # Pass the session object (agent needs config data from it)
            draft = generate_questions_agent(session, feedback)
            
            if not draft:
                print(f"[Attempt {attempt}] Failed to generate valid JSON.")
                attempt += 1
                continue

            # 2. Evaluate (Agent 2a)
            score, current_feedback = evaluate_agent(draft, session)
            print(f"[Attempt {attempt}] Score: {score}/100 | Feedback: {current_feedback}")

            # Keep track of the best draft so far
            if score > best_score:
                best_score = score
                best_draft = draft

            # 3. Decision
            if score >= 85:
                print("✅ Quality Satisfied (Score >= 85). Finalizing.")
                break 
            
            # If not satisfied, set feedback for next loop
            feedback = current_feedback
            attempt += 1

        # Final check for cancellation before saving result
        session.refresh_from_db()
        if session.status == 'CANCELLED':
            return

        # 4. Finalize
        if best_draft:
            formatted_html = format_html_agent(best_draft)
            session.result_html = formatted_html
            session.status = 'COMPLETED'
        else:
            session.result_html = "<p class='error'>Failed to generate a valid exam within the time limit.</p>"
            session.status = 'FAILED'

        session.save()
        print(f"⏱️ Generation Loop Ended. Session {exam_session_id} marked as {session.status}.")

    except Exception as e:
        print(f"Async Flow Error: {e}")
        try:
            session = ExamSession.objects.get(id=exam_session_id)
            session.status = 'FAILED'
            session.save()
        except:
            pass