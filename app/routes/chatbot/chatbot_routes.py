# ---- routes/chatbot/chatbot_routes.py ----
from flask import Blueprint, render_template, request, jsonify, current_app
from openai import OpenAI, APIError, RateLimitError, APIStatusError
from httpx import Timeout
from app.models import ChatbotMessage, db

import os
import logging
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from requests.exceptions import HTTPError
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type

# Load .env environment variables
load_dotenv()

# Initialize blueprint
chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ----------------------------
# LOCAL CHATBOT LOGIC
# ----------------------------
def local_chatbot_response(prompt: str) -> str:
    """
    Simple knowledge-based response system.
    Extend this dictionary to teach the bot specific answers.
    """
    prompt_lower = prompt.lower()

    # Predefined knowledge base
    predefined = {
        "how do i reset my password": "Click 'Forgot Password' on the login page to reset your password.",
        "how to register": "Use your student ID to sign up on the registration page and create your password.",
        "where can i see my grades": "Go to your student dashboard and click 'Results'.",
        "what is the registration deadline": "Registration closes at the end of Week 2 each semester.",
        "who do i contact for help": "You can reach the student support team via email at support@cavendish.edu.zm.",
        "where is the finance office": "The finance office is located on the main campus, ground floor, next to admissions."
    }

    # Return a known answer or fallback
    return predefined.get(prompt_lower, None)


# --- Retry wrapper for safe API/local response handling ---
@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((RateLimitError, APIError, APIStatusError, Timeout))
)
def safe_get_response(prompt: str):
    """
    Retry wrapper in case of transient failures or rate limits.
    Currently wraps local logic but ready for OpenAI integration later.
    """
    try:
        return local_chatbot_response(prompt)
    except Exception as e:
        logger.error(f"Error while generating response: {str(e)}")
        raise


# ----------------------------
# ROUTES
# ----------------------------

@chatbot_bp.route('/help', methods=['GET'])
def help_page():
    """
    Renders the help chatbot interface.
    """
    return render_template('help.html')


@chatbot_bp.route('/ask', methods=['POST'])
def ask_bot():
    """
    Handles messages sent from the frontend chatbot UI.
    - Checks if question exists in DB.
    - If not, uses local chatbot logic to respond.
    - Saves new Q&A for admin to review later.
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({"error": "Please enter a message."}), 400

        logger.info(f"🧠 User asked: {user_message}")

        # Step 1 — Check DB for known response
        known = ChatbotMessage.query.filter_by(question=user_message.lower()).first()
        if known:
            logger.info("✅ Found stored response in DB.")
            return jsonify({"response": known.answer, "known": True})

        # Step 2 — Generate a response using local chatbot
        response = safe_get_response(user_message)
        if not response:
            response = "I'm not sure about that — your question will be reviewed by an admin."

        # Step 3 — Save question and response to DB
        new_entry = ChatbotMessage(question=user_message.lower(), answer=response)
        db.session.add(new_entry)
        db.session.commit()

        logger.info(f"💾 Saved new chatbot message: {user_message}")

        return jsonify({"response": response, "known": False})

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error: {str(e)}")
        return jsonify({"error": "Database issue, please try again later."}), 500

    except Exception as e:
        logger.exception("Unexpected chatbot error")
        return jsonify({"error": "Internal Server Error"}), 500


@chatbot_bp.route('/unanswered', methods=['GET'])
def view_unanswered():
    """
    (Optional) Admin route to view all questions the bot didn’t know.
    """
    unanswered = ChatbotMessage.query.filter(ChatbotMessage.answer.ilike('%not sure%')).all()
    return render_template('chatbot/unanswered.html', unanswered=unanswered)
