# ---- routes/chatbot/chatbot_routes.py ----
from flask import Blueprint, render_template, request, jsonify, current_app
from openai import OpenAI, APIError, RateLimitError, APIStatusError
from httpx import Timeout
from app.models import ChatbotMessage, db

import os
import logging
import re
from datetime import datetime
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
# ENHANCED LOCAL CHATBOT LOGIC
# ----------------------------
class CavendishChatbot:
    def __init__(self):
        self.knowledge_base = self._build_knowledge_base()
        self.greetings = [
            "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
            "howdy", "greetings", "what's up", "yo"
        ]
        self.farewells = [
            "bye", "goodbye", "see you", "farewell", "quit", "exit", "stop",
            "thanks bye", "thank you bye"
        ]
        self.gratitude = [
            "thank", "thanks", "appreciate", "thank you", "thx", "ty"
        ]

    def _build_knowledge_base(self):
        """
        Comprehensive knowledge base for Cavendish University
        """
        return {
            # Authentication & Access
            "password": {
                "patterns": [
                    r"forgot.*password", r"reset.*password", r"can't.*login",
                    r"password.*reset", r"lost.*password", r"change.*password"
                ],
                "response": "To reset your password, click the 'Forgot Password?' link on the login page. You'll receive an email with instructions to create a new password. If you don't receive the email, check your spam folder or contact IT support at itsupport@cavendish.edu.zm."
            },
            "login": {
                "patterns": [
                    r"can't.*log in", r"login.*problem", r"sign in.*issue",
                    r"account.*locked", r"invalid.*credentials"
                ],
                "response": "If you're having trouble logging in, ensure you're using your correct student number (e.g., CUN-2022-001) and password. If the problem persists, use the 'Forgot Password' feature or contact IT support at itsupport@cavendish.edu.zm."
            },

            # Registration & Enrollment
            "registration": {
                "patterns": [
                    r"how.*register", r"registration.*process", r"enroll.*course",
                    r"sign up.*portal", r"create.*account", r"new student.*register"
                ],
                "response": "To register as a new student:\n1. Visit the registration portal\n2. Click 'Student Registration'\n3. Fill in your personal details\n4. Provide your academic information\n5. Create your account credentials\n6. Verify your email address\n\nYou'll need your official student number and personal details ready."
            },
            "deadline": {
                "patterns": [
                    r"registration.*deadline", r"when.*register", r"last date.*registration",
                    r"enrollment.*deadline", r"deadline.*courses"
                ],
                "response": "Registration deadlines vary by program and intake. Generally:\n- Main Semester: Ends Week 2 of semester\n- Late Registration: Until Week 3 (with late fee)\n- Special Intakes: Check specific program dates\n\nFor exact dates, visit the academic calendar on the university website or contact admissions."
            },
            "documents": {
                "patterns": [
                    r"documents.*need", r"required.*documents", r"what.*papers",
                    r"registration.*documents", r"submit.*documents"
                ],
                "response": "For registration, you typically need:\n• National ID/Passport\n• Academic certificates & transcripts\n• Passport photos\n• Proof of payment\n• Medical certificate\n• Student number confirmation\n\nSpecific requirements may vary by program. Contact admissions for your program's exact requirements."
            },

            # Payments & Fees
            "payment": {
                "patterns": [
                    r"how.*pay", r"payment.*methods", r"fee.*payment",
                    r"tuition.*fee", r"how much.*fee", r"payment.*options"
                ],
                "response": "Payment methods available:\n• Bank Transfer (Use student number as reference)\n• Online Payment Portal\n• Mobile Money\n• Cash at Finance Office\n\nFee structures vary by program. Log into your student portal to view your specific fee breakdown and payment deadlines."
            },
            "payment_status": {
                "patterns": [
                    r"payment.*status", r"check.*payment", r"fee.*confirmed",
                    r"payment.*verification", r"upload.*payment"
                ],
                "response": "To check your payment status:\n1. Log into your student portal\n2. Go to 'Payment Status' section\n3. View recent payments and their approval status\n\nPayments typically take 24-48 hours to be verified. If your payment isn't showing after 48 hours, contact finance@cavendish.edu.zm."
            },
            "receipt": {
                "patterns": [
                    r"get.*receipt", r"payment.*receipt", r"fee.*receipt",
                    r"proof.*payment", r"payment.*confirmation"
                ],
                "response": "Payment receipts are automatically generated and available in your student portal under 'Payment History'. You can download and print them for your records. If you need an official stamped receipt, visit the finance office."
            },

            # Academic Information
            "courses": {
                "patterns": [
                    r"available.*courses", r"what.*courses", r"program.*offer",
                    r"study.*options", r"academic.*programs"
                ],
                "response": "Cavendish University offers various programs including:\n• Medicine & Health Sciences\n• Business & Management\n• Information Technology\n• Law\n• Education\n• Social Sciences\n\nVisit our website or contact admissions for the complete program list and entry requirements."
            },
            "timetable": {
                "patterns": [
                    r"class.*timetable", r"schedule", r"when.*classes",
                    r"timetable.*access", r"course.*schedule"
                ],
                "response": "Your personal class timetable is available in the student portal under 'My Timetable'. Timetables are updated before each semester. If you have timetable conflicts, contact your department coordinator."
            },
            "results": {
                "patterns": [
                    r"check.*results", r"exam.*marks", r"academic.*results",
                    r"grades", r"transcript"
                ],
                "response": "You can view your results:\n1. Log into student portal\n2. Navigate to 'Academic Records'\n3. Select 'Results' or 'Transcript'\n\nOfficial transcripts can be requested from the registry office. Results are typically released 2-3 weeks after exams."
            },

            # Support & Contact
            "contact": {
                "patterns": [
                    r"contact.*support", r"help.*desk", r"who.*contact",
                    r"support.*email", r"phone.*number", r"where.*office"
                ],
                "response": "You can contact us through:\n\n📞 General Inquiries: +260 211 387700\n📧 Email: info@cavendish.edu.zm\n📍 Location: Plot 15267 Chindo Road, Lusaka\n\nDepartment Contacts:\n• Admissions: admissions@cavendish.edu.zm\n• Finance: finance@cavendish.edu.zm\n• IT Support: itsupport@cavendish.edu.zm\n• Student Affairs: studentaffairs@cavendish.edu.zm"
            },
            "office_hours": {
                "patterns": [
                    r"office.*hours", r"when.*open", r"working.*hours",
                    r"available.*time", r"open.*close"
                ],
                "response": "University Office Hours:\n• Monday-Friday: 8:00 AM - 5:00 PM\n• Saturday: 9:00 AM - 1:00 PM\n• Sunday: Closed\n\nSpecific departments may have different hours. It's best to call ahead or check the department's notice."
            },

            # Technical Support
            "portal": {
                "patterns": [
                    r"portal.*down", r"can't.*access.*portal", r"website.*not working",
                    r"technical.*issue", r"system.*error"
                ],
                "response": "If you're experiencing technical issues with the portal:\n1. Clear your browser cache and cookies\n2. Try a different browser (Chrome/Firefox)\n3. Check your internet connection\n4. Try accessing from a different device\n\nIf problems persist, contact IT Support: itsupport@cavendish.edu.zm or +260 211 387700 (Ext. 123)"
            },

            # Emergency & Urgent
            "urgent": {
                "patterns": [
                    r"emergency", r"urgent", r"critical", r"immediately",
                    r"asap", r"right now"
                ],
                "response": "🚨 For urgent matters requiring immediate attention:\n\n📞 Emergency Contact: +260 211 387700\n🏥 Medical Emergency: Campus Security or call 992\n🔒 Security Issues: Campus Security Desk\n\nPlease describe your urgent issue and we'll connect you with the appropriate department immediately."
            }
        }

    def _match_pattern(self, message, patterns):
        """Check if message matches any of the patterns"""
        for pattern in patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    def _extract_context(self, message):
        """Extract context and keywords from message"""
        message_lower = message.lower()
        
        # Check for greetings
        if any(greeting in message_lower for greeting in self.greetings):
            return "greeting"
        
        # Check for farewells
        if any(farewell in message_lower for farewell in self.farewells):
            return "farewell"
        
        # Check for gratitude
        if any(grat in message_lower for grat in self.gratitude):
            return "gratitude"
        
        # Check knowledge base categories
        for category, data in self.knowledge_base.items():
            if self._match_pattern(message_lower, data["patterns"]):
                return category
        
        return "unknown"

    def generate_response(self, message):
        """
        Generate intelligent response based on message content
        """
        message_lower = message.lower().strip()
        context = self._extract_context(message_lower)

        # Handle special cases
        if context == "greeting":
            return self._get_greeting_response()
        elif context == "farewell":
            return self._get_farewell_response()
        elif context == "gratitude":
            return self._get_gratitude_response()
        elif context == "urgent":
            return self.knowledge_base["urgent"]["response"]
        elif context != "unknown":
            return self.knowledge_base[context]["response"]
        else:
            return self._get_fallback_response(message)

    def _get_greeting_response(self):
        """Generate friendly greeting response"""
        greetings = [
            "Hello! Welcome to Cavendish University Help Center. How can I assist you today?",
            "Hi there! I'm here to help with your Cavendish University questions. What can I help you with?",
            "Good day! Welcome to Cavendish University support. How may I assist you?",
            "Hello! I'm the Cavendish HelpBot. I can help with registration, payments, academic info, and more. What do you need help with?"
        ]
        import random
        return random.choice(greetings)

    def _get_farewell_response(self):
        """Generate friendly farewell response"""
        farewells = [
            "Goodbye! Feel free to reach out if you have more questions. Have a great day!",
            "Thank you for chatting! Don't hesitate to come back if you need more assistance.",
            "See you! Remember, you can always return here for help with Cavendish University matters.",
            "Farewell! Wishing you success in your academic journey at Cavendish University!"
        ]
        import random
        return random.choice(farewells)

    def _get_gratitude_response(self):
        """Generate response to thank you messages"""
        gratitude_responses = [
            "You're welcome! I'm glad I could help. Is there anything else you'd like to know?",
            "Happy to help! Don't hesitate to ask if you have more questions.",
            "You're very welcome! That's what I'm here for. Feel free to ask anything else about Cavendish University.",
            "My pleasure! Let me know if you need assistance with anything else."
        ]
        import random
        return random.choice(gratitude_responses)

    def _get_fallback_response(self, original_message):
        """Generate intelligent fallback response"""
        fallbacks = [
            f"I understand you're asking about '{original_message}'. While I review this with our team, you might find help by:\n\n• Checking the student portal FAQ section\n• Contacting the relevant department directly\n• Visiting the university website\n\nYour question has been saved and will be reviewed by our support team.",
            f"Thank you for your question about '{original_message}'. I'm still learning about all aspects of Cavendish University. In the meantime, you could:\n\n• Browse our online knowledge base\n• Contact student support\n• Check the university notice board\n\nI've noted your question for follow-up.",
            f"I appreciate your question regarding '{original_message}'. For the most accurate information on this topic, I recommend:\n\n• Consulting your department office\n• Checking official university communications\n• Contacting the relevant support office\n\nYour query has been recorded for our team's attention."
        ]
        import random
        return random.choice(fallbacks)

# Initialize chatbot
chatbot = CavendishChatbot()

# --- Retry wrapper for safe API/local response handling ---
@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((RateLimitError, APIError, APIStatusError, Timeout))
)
def safe_get_response(prompt: str):
    """
    Enhanced response generator with intelligent matching
    """
    try:
        return chatbot.generate_response(prompt)
    except Exception as e:
        logger.error(f"Error while generating response: {str(e)}")
        # Fallback to simple response
        return "I apologize, but I'm experiencing technical difficulties. Please try again in a moment or contact support directly at itsupport@cavendish.edu.zm."


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
    Enhanced chatbot endpoint with better response handling
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({"error": "Please enter a message."}), 400

        logger.info(f"🧠 User asked: {user_message}")

        # Step 1 — Check DB for known response (case-insensitive, similar matching)
        known = ChatbotMessage.query.filter(
            db.func.lower(ChatbotMessage.question) == user_message.lower()
        ).first()
        
        if known:
            logger.info("✅ Found stored response in DB.")
            return jsonify({
                "response": known.answer, 
                "known": True,
                "category": "stored"
            })

        # Step 2 — Generate intelligent response
        response = safe_get_response(user_message)
        
        # Determine if this was a known or unknown response
        context = chatbot._extract_context(user_message.lower())
        is_known_response = context not in ["unknown", "urgent"]

        # Step 3 — Save question and response to DB for learning
        new_entry = ChatbotMessage(
            question=user_message.lower(), 
            answer=response,
            category=context,
            is_known_response=is_known_response,
            created_at=datetime.utcnow()
        )
        db.session.add(new_entry)
        db.session.commit()

        logger.info(f"💾 Saved chatbot message - Category: {context}, Known: {is_known_response}")

        return jsonify({
            "response": response, 
            "known": is_known_response,
            "category": context
        })

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error: {str(e)}")
        # Still return a response even if DB fails
        response = chatbot.generate_response(user_message)
        return jsonify({
            "response": response,
            "known": False,
            "category": "error_fallback"
        })

    except Exception as e:
        logger.exception("Unexpected chatbot error")
        return jsonify({
            "error": "I'm having trouble processing your request right now. Please try again in a moment or contact support directly."
        }), 500


@chatbot_bp.route('/unanswered', methods=['GET'])
def view_unanswered():
    """
    Admin route to view questions the bot couldn't answer well
    """
    unanswered = ChatbotMessage.query.filter(
        ChatbotMessage.is_known_response == False
    ).order_by(ChatbotMessage.created_at.desc()).all()
    
    return render_template('chatbot/unanswered.html', unanswered=unanswered)


@chatbot_bp.route('/stats', methods=['GET'])
def chatbot_stats():
    """
    Statistics about chatbot usage and performance
    """
    total_questions = ChatbotMessage.query.count()
    known_answers = ChatbotMessage.query.filter_by(is_known_response=True).count()
    unknown_answers = ChatbotMessage.query.filter_by(is_known_response=False).count()
    
    if total_questions > 0:
        success_rate = (known_answers / total_questions) * 100
    else:
        success_rate = 0
    
    return jsonify({
        "total_questions": total_questions,
        "known_answers": known_answers,
        "unknown_answers": unknown_answers,
        "success_rate": round(success_rate, 2),
        "categories": db.session.query(
            ChatbotMessage.category, 
            db.func.count(ChatbotMessage.id)
        ).group_by(ChatbotMessage.category).all()
    })


# Update your ChatbotMessage model to include new fields:
"""
class ChatbotMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='unknown')
    is_known_response = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatbotMessage {self.question}>'
"""