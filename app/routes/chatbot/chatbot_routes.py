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
            "howdy", "greetings", "what's up", "yo", "hola", "hi there"
        ]
        self.farewells = [
            "bye", "goodbye", "see you", "farewell", "quit", "exit", "stop",
            "thanks bye", "thank you bye", "later", "catch you later"
        ]
        self.gratitude = [
            "thank", "thanks", "appreciate", "thank you", "thx", "ty", "much appreciated"
        ]

    def _build_knowledge_base(self):
        """
        Comprehensive knowledge base for Cavendish University
        """
        return {
            # =========================
            # STUDENT REGISTRATION FAQ
            # =========================
            "new_student_registration": {
                "patterns": [
                    r"new.*student.*register",
                    r"how.*register.*new student",
                    r"first.*time.*register",
                    r"student.*registration process"
                ],
                "response": """To register as a new student:

1. Open the Student Registration Portal.
2. Click Student Registration.
3. Enter your Student Number and Full Name.
4. Create a password.
5. Verify your email address.
6. Log into your account.
7. Select your programme, year level and semester.
8. Upload payment proof.
9. Submit your registration for approval.

Once approved, you can download your Registration Slip from your dashboard."""
            },

            "registration_approval": {
                "patterns": [
                    r"approval.*take",
                    r"how long.*registration",
                    r"registration.*approval",
                    r"pending.*approval"
                ],
                "response": """Registration approval normally takes between 24 and 72 working hours after payment proof has been submitted.

Approval time may vary depending on:
• Verification of payment
• Registration volume
• Weekends and public holidays
You will receive an email notification once your registration has been approved."""
            },

            "download_regslip": {
                "patterns": [
                    r"download.*registration slip",
                    r"download.*reg slip",
                    r"print.*registration slip",
                    r"get.*registration slip"
                ],
                "response": """To download your Registration Slip:

1. Log into the Student Portal.
2. Open your Dashboard.
3. Select your approved registration.
4. Click Download Registration Slip.

Your Registration Slip becomes available only after approval by the Registrar's Office."""
            },

            "registration_requirements": {
                "patterns": [
                    r"documents.*need",
                    r"before.*register",
                    r"what.*need.*register",
                    r"registration.*requirements"
                ],
                "response": """Before registering, ensure you have:

• Valid Student Number
• Active Email Address
• Programme Information
• Year Level Information
• Payment Proof
• Stable Internet Connection

Having these ready will make your registration process faster and easier."""
            },

            "registration_status": {
                "patterns": [
                    r"registration.*status",
                    r"check.*registration",
                    r"track.*registration",
                    r"application.*status"
                ],
                "response": """To check your registration status:

1. Log into the Student Portal.
2. Go to Dashboard.
3. View Registration Status.

Possible statuses:
• Pending Approval
• Approved
• Rejected
• Payment Verification Pending"""
            },

            # =========================
            # PAYMENTS & FINANCE
            # =========================
            "payment_upload_faq": {
                "patterns": [
                    r"upload.*payment",
                    r"submit.*payment proof",
                    r"payment.*receipt",
                    r"upload.*receipt"
                ],
                "response": """To upload payment proof:

1. Log into the portal.
2. Open Registration.
3. Click Upload Payment Proof.
4. Select your receipt.
5. Submit.

Supported formats:
• PDF
• JPG
• JPEG
• PNG

Ensure the receipt is clear and readable."""
            },

            "payment_methods_faq": {
                "patterns": [
                    r"payment.*methods",
                    r"how.*pay",
                    r"payment.*options"
                ],
                "response": """Available payment methods may include:

• Bank Deposit
• Bank Transfer
• Mobile Money
• Online Payment Systems

Always use your Student Number as the payment reference."""
            },

            "payment_approval_faq": {
                "patterns": [
                    r"payment.*approval",
                    r"payment.*verification",
                    r"how long.*payment"
                ],
                "response": """Payment verification normally takes between 24 and 48 working hours.

Once payment has been verified, your registration can proceed for approval."""
            },

            "payment_status_faq": {
                "patterns": [
                    r"payment.*status",
                    r"check.*payment",
                    r"verify.*payment"
                ],
                "response": """To check payment status:

1. Log into your account.
2. Open Dashboard.
3. Navigate to Payment Status.

Possible statuses:
• Pending Verification
• Verified
• Rejected"""
            },

            # =========================
            # TECHNICAL SUPPORT
            # =========================
            "reset_password_faq": {
                "patterns": [
                    r"reset.*password",
                    r"forgot.*password",
                    r"change.*password"
                ],
                "response": """To reset your password:

1. Click Forgot Password on the login page.
2. Enter your registered email address.
3. Follow the instructions sent to your email.

If you do not receive the email, contact IT Support."""
            },

            "login_issue_faq": {
                "patterns": [
                    r"can't.*login",
                    r"cannot.*login",
                    r"login.*problem",
                    r"unable.*login"
                ],
                "response": """If you cannot log in:

• Verify your Student Number.
• Check your password carefully.
• Reset your password if necessary.
• Ensure your internet connection is stable.

If the issue continues, contact IT Support."""
            },

            "portal_issue_faq": {
                "patterns": [
                    r"portal.*issue",
                    r"portal.*down",
                    r"cannot.*access.*portal",
                    r"website.*problem"
                ],
                "response": """If the portal is not accessible:

• Refresh the page.
• Clear browser cache.
• Try another browser.
• Check your internet connection.

If the problem persists, contact IT Support immediately."""
            },

            # =========================
            # ACADEMIC SERVICES
            # =========================
            "graduation_faq": {
                "patterns": [
                    r"graduation.*requirements",
                    r"graduate",
                    r"graduation"
                ],
                "response": """Graduation requirements generally include:

• Successful completion of all required courses.
• Full payment of university fees.
• Meeting programme credit requirements.
• Clearance from relevant departments.

Contact the Registrar's Office for programme-specific graduation requirements."""
            },

            "transcript_faq": {
                "patterns": [
                    r"transcript",
                    r"academic record",
                    r"results transcript"
                ],
                "response": """To request an academic transcript:

1. Submit a transcript request through the Registrar's Office.
2. Complete any required forms.
3. Pay applicable processing fees.
4. Wait for processing and collection instructions.

Processing times may vary."""
            },

            "accommodation_faq": {
                "patterns": [
                    r"accommodation",
                    r"hostel",
                    r"housing",
                    r"student residence"
                ],
                "response": """For accommodation information:

• Contact Student Affairs.
• Visit the accommodation office.
• Review approved off-campus accommodation options.

Availability may vary throughout the academic year."""
            },

            "scholarship_faq": {
                "patterns": [
                    r"scholarship",
                    r"bursary",
                    r"financial aid",
                    r"sponsorship"
                ],
                "response": """Scholarship opportunities may be available through:

• Cavendish University
• Government bursary schemes
• NGO sponsorship programs
• Corporate scholarship initiatives

Contact Admissions or Student Affairs for current opportunities."""
            },

            "industrial_attachment_faq": {
                "patterns": [
                    r"industrial attachment",
                    r"internship",
                    r"attachment placement",
                    r"work placement"
                ],
                "response": """Industrial Attachment is a structured work-based learning programme that allows students to gain practical industry experience.

Students should:

• Meet programme eligibility requirements.
• Obtain placement approval.
• Submit required reports.
• Complete assessment requirements.

Contact your department coordinator for attachment guidelines."""
            },

            # =========================
            # CONTACTS
            # =========================
            "admin_contact_faq": {
                "patterns": [
                    r"contact.*admin",
                    r"contact.*registrar",
                    r"administrator",
                    r"who.*contact"
                ],
                "response": """For registration assistance:

Registrar's Office
Email: registrar@cavendish.ac.zm

IT Support
Email: itsupport@cavendish.ac.zm

Finance Office
Email: finance@cavendish.ac.zm

General Enquiries
Email: info@cavendish.ac.zm

Location:
Plot 15267 Chindo Road, Lusaka, Zambia"""
            },

            # =========================
            # AUTHENTICATION & ACCESS
            # =========================
            "password": {
                "patterns": [
                    r"forgot.*password", r"reset.*password", r"can't.*login",
                    r"password.*reset", r"lost.*password", r"change.*password"
                ],
                "response": """To reset your password, click the 'Forgot Password?' link on the login page. You'll receive an email with instructions to create a new password. If you don't receive the email, check your spam folder or contact IT support at itsupport@cavendish.edu.zm."""
            },
            
            "login": {
                "patterns": [
                    r"can't.*log in", r"login.*problem", r"sign in.*issue",
                    r"account.*locked", r"invalid.*credentials"
                ],
                "response": """If you're having trouble logging in, ensure you're using your correct student number (e.g., CUN-2022-001) and password. If the problem persists, use the 'Forgot Password' feature or contact IT support at itsupport@cavendish.edu.zm."""
            },

            # =========================
            # REGISTRATION PROCESS
            # =========================
            "registration": {
                "patterns": [
                    r"how.*register", r"registration.*process", r"enroll.*course",
                    r"sign up.*portal", r"create.*account"
                ],
                "response": """To register as a new student:
1. Visit the registration portal
2. Click 'Student Registration'
3. Fill in your personal details
4. Provide your academic information
5. Create your account credentials
6. Verify your email address
7. Select your programme and semester
8. Upload payment proof
9. Submit registration
10. Wait for approval
11. Download Registration Slip

You'll need your official student number and personal details ready."""
            },

            "approval": {
                "patterns": [
                    r"how long.*approval", r"when.*approved",
                    r"registration.*approved", r"approval.*take",
                    r"waiting.*approval", r"how long.*verified"
                ],
                "response": """Registration applications are normally reviewed within 24 to 72 working hours after payment proof has been uploaded successfully.

Approval times may vary depending on:
• Payment verification status
• Registration volume
• Public holidays and weekends

You will receive an email notification once your registration has been approved. If your application remains pending for more than 72 hours, contact the Registrar's Office."""
            },

            "registration_slip": {
                "patterns": [
                    r"download.*registration slip", r"get.*registration slip",
                    r"print.*registration slip", r"reg slip", r"proof.*registration"
                ],
                "response": """Once your registration has been approved:

1. Log in to the Student Registration Portal
2. Open your Dashboard
3. Select the approved semester
4. Click 'Download Registration Slip'

The Registration Slip serves as proof of your semester registration and can be printed for official use. You can also access it anytime from your student dashboard."""
            },

            "requirements": {
                "patterns": [
                    r"before.*register", r"requirements.*register",
                    r"need.*before.*registration", r"what.*need.*register",
                    r"what do i need"
                ],
                "response": """Before starting registration, ensure you have:
• A valid Student Number
• An active email address
• Your chosen academic programme
• Payment proof (if applicable)
• Stable internet connection
• National ID/Passport
• Academic certificates & transcripts

You should also know:
• Your academic year level
• Current semester
• Courses you intend to register for"""
            },

            "status": {
                "patterns": [
                    r"check.*status", r"registration.*status",
                    r"track.*application", r"application.*status",
                    r"status of my registration"
                ],
                "response": """To check your registration status:

1. Log into the portal
2. Go to your Dashboard
3. View the Registration Status section

Possible statuses:
• Pending Approval - Your application is being reviewed
• Approved - Your registration has been confirmed
• Rejected - Your application needs corrections
• Payment Verification Pending - Waiting for payment confirmation

If your application remains pending for more than 72 hours, contact the Registrar's Office."""
            },

            "payment_upload": {
                "patterns": [
                    r"upload.*payment", r"submit.*payment",
                    r"payment.*proof", r"payment.*receipt",
                    r"bank.*receipt", r"upload.*receipt"
                ],
                "response": """To upload payment proof:

1. Log into the portal
2. Navigate to Registration
3. Click Upload Payment Proof
4. Select your receipt image or PDF
5. Submit for verification

Supported formats:
• PDF
• JPG
• JPEG
• PNG

Ensure the receipt is clear and readable. Payment approvals typically take 24-48 hours."""
            },

            "course_selection": {
                "patterns": [
                    r"select.*courses", r"choose.*courses",
                    r"register.*courses", r"course.*selection",
                    r"add.*course", r"enroll.*courses"
                ],
                "response": """Course selection is completed during registration.

Steps:
1. Choose your programme
2. Select year level
3. Select semester
4. Choose available courses from the list
5. Submit registration

Only approved courses for your programme and semester will be displayed. Mandatory courses are shown with credit hours."""
            },

            "registrar": {
                "patterns": [
                    r"contact.*registrar", r"registrar.*office",
                    r"speak.*admin", r"contact.*admin",
                    r"administrator", r"talk to someone"
                ],
                "response": """For registration assistance, contact:

📧 Registrar's Office: registrar@cavendish.ac.zm
📧 Admissions: admissions@cavendish.ac.zm
📧 Finance: finance@cavendish.ac.zm
📧 IT Support: itsupport@cavendish.ac.zm
📧 Student Affairs: studentaffairs@cavendish.ac.zm

📍 Physical Address: Plot 15267 Chindo Road, Lusaka, Zambia

Office Hours: Monday - Friday, 08:00 AM to 05:00 PM"""
            },

            "rejected": {
                "patterns": [
                    r"registration.*rejected", r"application.*rejected",
                    r"why.*rejected", r"rejection", r"was rejected"
                ],
                "response": """A registration application may be rejected because of:
• Missing payment proof
• Invalid or unclear payment proof
• Incorrect programme selection
• Missing required information
• Administrative issues
• Outstanding fees

If your application is rejected, review the feedback provided, correct the issues, and submit a corrected application. Contact the Registrar's Office if you need clarification."""
            },

            "new_student": {
                "patterns": [
                    r"new.*student", r"first.*time.*register",
                    r"freshman", r"first.*registration", r"new.*registration"
                ],
                "response": """Welcome to Cavendish University! 🎓

For first-time registration:

1. Create your student portal account
2. Verify your email address
3. Log into the portal
4. Select programme and semester
5. View available courses
6. Upload payment proof
7. Submit registration
8. Wait for approval (24-72 hours)
9. Download your Registration Slip

The process normally takes a few minutes to complete, while approval may take up to 72 working hours. You'll receive email notifications at each step."""
            },

            "student_number": {
                "patterns": [
                    r"forgot.*student number", r"lost.*student number",
                    r"don't know.*student number", r"find.*student number"
                ],
                "response": """If you have forgotten your Student Number:
• Check previous admission documents
• Check university admission emails
• Contact Admissions or Registry
• Look at your admission letter

You will need your Student Number to access the registration portal. Contact admissions@cavendish.ac.zm for assistance."""
            },

            "portal_link": {
                "patterns": [
                    r"portal.*link", r"registration.*portal",
                    r"portal.*website", r"where.*portal",
                    r"portal.*url", r"access.*portal"
                ],
                "response": """You can access the Student Registration Portal through the Cavendish University website under 'Student Portal' or 'Registration'.

If you are unable to access the portal, check your internet connection or contact IT Support for assistance at itsupport@cavendish.edu.zm."""
            },

            "admissions": {
                "patterns": [
                    r"admission", r"apply", r"application",
                    r"entry requirements", r"how.*apply", r"joining"
                ],
                "response": """To apply to Cavendish University Zambia:

1. Complete the online application form
2. Submit certified academic documents
3. Submit identification documents
4. Pay the application fee
5. Await admission decision

Admissions Office:
📧 admissions@cavendish.ac.zm
📞 +260 211 387700

Visit our website for specific programme requirements."""
            },

            "student_portal": {
                "patterns": [
                    r"student portal", r"portal login",
                    r"dashboard", r"my account", r"portal features"
                ],
                "response": """The Student Portal allows you to:
• Register courses
• View results and transcripts
• Download registration slips
• Track payment history
• Update profile information
• Access academic calendar
• View timetable

Log in using your Student Number and password."""
            },

            "payment_approval_status": {
                "patterns": [
                    r"payment.*approved", r"approval.*payment",
                    r"verify.*payment", r"payment.*verified"
                ],
                "response": """Payment approvals are usually completed within 24–48 hours after submission.

If your payment remains pending after 48 hours, contact finance@cavendish.ac.zm with:
• Student Number
• Payment Receipt
• Date of Payment
• Bank Reference Number

Our finance team will assist you promptly."""
            },

            "graduation_info": {
                "patterns": [
                    r"graduation", r"graduate",
                    r"degree collection", r"certificate collection"
                ],
                "response": """Graduation information is published by the Registry Office.

For graduation inquiries:
📧 registry@cavendish.ac.zm

Students must ensure:
• All fees cleared
• Results finalized
• Graduation application submitted
• Clearance obtained from all departments"""
            },

            "transcript_request": {
                "patterns": [
                    r"transcript", r"academic transcript",
                    r"official transcript", r"results"
                ],
                "response": """Official transcripts may be requested through the Registry Office.

Requirements:
• Student Number
• Clearance of outstanding balances
• Transcript processing fee
• Written request letter

Processing takes 5-10 working days. Contact registry@cavendish.ac.zm for the transcript application form."""
            },

            "deferral_request": {
                "patterns": [
                    r"defer", r"deferment",
                    r"postpone semester", r"pause studies"
                ],
                "response": """Students wishing to defer studies should submit a formal request to the Registry Office.

Include:
• Student Number
• Reason for deferral
• Supporting documentation
• Expected return semester

Deferral requests should be submitted before the semester begins. Contact registry@cavendish.ac.zm for the deferral form."""
            },

            "exams_info": {
                "patterns": [
                    r"exam", r"examination",
                    r"supplementary", r"rewrite", r"exam timetable"
                ],
                "response": """Examination information includes:
• Exam timetables
• Supplementary exams
• Exam venues
• Special arrangements
• Exam regulations

Check your student portal regularly for updates. Contact your faculty for specific exam-related questions."""
            },

            "accommodation_info": {
                "patterns": [
                    r"hostel", r"accommodation",
                    r"residence", r"housing", r"room"
                ],
                "response": """For accommodation inquiries:

📧 studentaffairs@cavendish.ac.zm

Student Affairs can assist with:
• Hostel information and availability
• Private accommodation referrals
• Housing guidance
• Lease agreements

Accommodation applications open before each semester."""
            },

            "library_info": {
                "patterns": [
                    r"library", r"books",
                    r"research materials", r"e-library", r"borrow"
                ],
                "response": """The University Library provides:
• Physical books and textbooks
• E-books and digital resources
• Journals and periodicals
• Research databases
• Study spaces
• Computer access

Contact the Library Desk for assistance with borrowing and research."""
            },

            "scholarship_info": {
                "patterns": [
                    r"scholarship", r"bursary",
                    r"financial aid", r"sponsorship"
                ],
                "response": """Scholarships and financial assistance opportunities may be available.

Contact:
📧 admissions@cavendish.ac.zm

for current scholarship opportunities, eligibility requirements, and application deadlines. Scholarships are limited and awarded based on merit or need."""
            },

            "attachment_info": {
                "patterns": [
                    r"industrial attachment", r"internship",
                    r"attachment letter", r"placement", r"work experience"
                ],
                "response": """Industrial attachment support is coordinated by your faculty.

Students may request:
• Introduction letters
• Assessment forms
• Placement guidance
• Logbook templates

Contact your department coordinator at least one month before the attachment period."""
            },

            "clearance_info": {
                "patterns": [
                    r"clearance", r"graduation clearance",
                    r"student clearance", r"final clearance"
                ],
                "response": """Student clearance requires approval from:
• Library - No outstanding books/fines
• Finance - No outstanding fees
• Academic - Results finalized
• Registry - Graduation application submitted

Contact Registry for final clearance processing at least two weeks before graduation."""
            },

            "payment_methods_info": {
                "patterns": [
                    r"payment methods", r"ways to pay",
                    r"how to pay", r"fee payment options"
                ],
                "response": """Payment methods available:
• Bank Transfer (Use student number as reference)
• Online Payment Portal
• Mobile Money (MTN/Airtel)
• Cash at Finance Office
• Credit/Debit Card

Fee structures vary by programme. Log into your student portal to view your specific fee breakdown and payment deadlines."""
            },

            "semester_dates_info": {
                "patterns": [
                    r"semester dates", r"academic calendar",
                    r"when does semester start", r"school calendar"
                ],
                "response": """Semester dates are published in the Academic Calendar available on the university website.

Typical schedule:
• Semester 1: January - May
• Semester 2: August - December
• Summer Semester: June - July

Exact dates vary each year. Check the official Academic Calendar on the Cavendish University website."""
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
        elif context != "unknown":
            return self.knowledge_base[context]["response"]
        else:
            return self._get_fallback_response(message)

    def _get_greeting_response(self):
        """Generate friendly greeting response"""
        greetings = [
            "Hello! 👋 Welcome to Cavendish University Help Center. How can I assist you with your registration today?",
            "Hi there! I'm here to help with your Cavendish University questions. What would you like to know?",
            "Good day! ☀️ Welcome to Cavendish University support. How may I assist you with registration, payments, or academic information?",
            "Hello! I'm the Cavendish HelpBot. I can help with registration, payments, course selection, results, timetables, and more. What do you need help with?"
        ]
        import random
        return random.choice(greetings)

    def _get_farewell_response(self):
        """Generate friendly farewell response"""
        farewells = [
            "Goodbye! 👋 Feel free to reach out if you have more questions. Have a great day!",
            "Thank you for chatting with the Cavendish HelpBot! Don't hesitate to come back if you need more assistance.",
            "See you! Remember, you can always return here for help with Cavendish University matters. Good luck with your studies! 🎓",
            "Farewell! Wishing you success in your academic journey at Cavendish University. Come back anytime you need assistance."
        ]
        import random
        return random.choice(farewells)

    def _get_gratitude_response(self):
        """Generate response to thank you messages"""
        gratitude_responses = [
            "You're welcome! 😊 I'm glad I could help. Is there anything else you'd like to know?",
            "Happy to help! Don't hesitate to ask if you have more questions about registration or any other university matter.",
            "You're very welcome! That's what I'm here for. Feel free to ask anything else about Cavendish University.",
            "My pleasure! Let me know if you need assistance with anything else - course registration, payments, results, or anything else!"
        ]
        import random
        return random.choice(gratitude_responses)

    def _get_fallback_response(self, original_message):
        """Generate intelligent fallback response that guides the user"""
        return f"""I understand you're asking about: '{original_message}'

I don't currently have a precise answer for that question, but I can help with many common topics:

📚 **Registration & Academics**
• How do I register as a new student?
• How long does registration approval take?
• How do I download my registration slip?
• What documents do I need before registering?
• How do I check my registration status?

💳 **Payments & Finance**
• How do I upload payment proof?
• What payment methods are available?
• How long does payment approval take?
• How do I check payment status?

🔧 **Technical Support**
• How do I reset my password?
• Can't log into the portal?
• Portal access issues

🎓 **Other Services**
• Graduation requirements
• Transcript requests
• Accommodation
• Scholarships
• Industrial attachment

**Contact us directly:**
📧 registrar@cavendish.ac.zm
📧 admissions@cavendish.ac.zm
📞 +260 211 387700

Your question has been recorded and will help improve our responses. Please try rephrasing your question or contact our support team for immediate assistance."""

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
        is_known_response = context not in ["unknown"]

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