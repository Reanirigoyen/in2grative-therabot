import streamlit as st

st.set_page_config(
    page_title="In2Grative TheraBot",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.write("✅ App loaded successfully!")
st.write("🚀 App started!")  # TEMP DEBUG
# In therabot_app.py (above your main code)
import os
from datetime import datetime, timedelta
import random
import pandas as pd
import matplotlib.pyplot as plt
import base64
import sqlite3
import hashlib
from PIL import Image

# Initialize database
conn = sqlite3.connect('therapy_app.db', check_same_thread=False)
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              username TEXT UNIQUE, 
              password TEXT, 
              email TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS mood_entries
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              date TEXT,
              mood INTEGER,
              note TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS journal_entries
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              date TEXT,
              entry TEXT,
              sentiment REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS self_care_activities
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              date TEXT,
              activity TEXT,
              category TEXT,
              duration INTEGER)''')

c.execute('''CREATE TABLE IF NOT EXISTS sleep_data
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              date TEXT,
              hours REAL,
              quality TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS ai_therapist_questions
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              date TEXT,
              question TEXT,
              response TEXT)''')

conn.commit() # Finalize table creation

# Initialize session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Welcome"
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = 'Guest'

# helper: Get image base64
def get_image_base64(path):
    if os.path.exists(path):
        try:
            with open(path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error loading image from {path}: {e}")
            return None
    else:
        print(f"File does not exist at: {path}")
        parent_dir = os.path.dirname(path)
        if os.path.exists(parent_dir):
            print(f"Parent directory exists. Contents: {os.listdir(parent_dir)}")
        else:
            print(f"Parent directory does not exist: {parent_dir}")
        return None

# Use the specific path to the image
import os
from PIL import Image

image_path = os.path.join(os.path.dirname(__file__), "In2Grative_Therapy_Logo_Design.png")

try:
    logo_base64 = get_image_base64(image_path)
    print(f"[INITIAL LOAD] Logo exists? {logo_base64 is not None}")
except Exception as e:
    print(f"Error loading logo: {e}")
    logo_base64 = None
    # Optionally provide a default image or continue without logo

# Authentication helpers
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def create_user(username, password, email):
    global c
    c.execute('INSERT INTO users (username, password, email) VALUES (?,?,?)',
              (username, make_hashes(password), email))
    conn.commit()
    return c.lastrowid

def login_user(username, password):
    global c
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    if data and check_hashes(password, data[2]):
        return data[0]  # Return user ID
    return None

# AI Memory and Analysis Functions
def analyze_journal_sentiment(text):
    positive_words = ['happy', 'good', 'great', 'joy', 'excited', 'calm', 'peaceful']
    negative_words = ['sad', 'bad', 'angry', 'anxious', 'stress', 'depressed']
    score = 0
    text_lower = text.lower()
    for word in positive_words:
        if word in text_lower:
            score += 1
    for word in negative_words:
        if word in text_lower:
            score -= 1
    word_count = max(1, len(text.split()))
    return score / word_count

def generate_ai_response(user_id):
    global c
    c.execute('SELECT entry FROM journal_entries WHERE user_id = ? ORDER BY date DESC LIMIT 3', (user_id,))
    recent_entries = c.fetchall()
    c.execute('SELECT mood FROM mood_entries WHERE user_id = ? ORDER BY date DESC LIMIT 7', (user_id,))
    mood_data = c.fetchall()
    avg_mood = sum([m[0] for m in mood_data])/len(mood_data) if mood_data else 5
    if recent_entries:
        sentiment = analyze_journal_sentiment(" ".join([e[0] for e in recent_entries]))
        if sentiment > 0.3:
            return "I'm noticing some positive themes in your recent reflections. Let's build on this momentum!"
        elif sentiment < -0.3:
            return "Your recent entries suggest you've been facing some challenges. Remember growth often comes through difficulty."
    if avg_mood < 4:
        return "I see your mood has been lower recently. Would you like to explore some coping strategies?"
    return "How are you feeling today compared to yesterday?"
def generate_cbt_response(user_input, user_id=None):
    """Generate CBT-focused responses with cognitive restructuring"""
    techniques = [
        ("Identifying Cognitive Distortions", 
         f"I notice you might be experiencing {random.choice(['all-or-nothing thinking', 'overgeneralization', 'mental filtering', 'disqualifying the positive'])}. "
         "Would it help to examine the evidence for and against this thought?"),
         
        ("Behavioral Activation",
         "When we feel down, we often stop doing things that bring us joy. What's one small activity you used to enjoy "
         "that you could try this week, even if you don't feel like it?"),
         
        ("Thought Record",
         "Let's examine that thought more closely. On a scale of 0-100%, how much do you believe this thought? "
         "What evidence supports it? What evidence contradicts it?"),
         
        ("Socratic Questioning",
         "If a friend had this thought, what would you tell them? Is there another way to look at this situation?"),
         
        ("Graded Task Assignment",
         "Big challenges can feel overwhelming. Could we break this down into smaller, more manageable steps? "
         "What would be a tiny first step you could take?")
    ]
    
    # Special responses for veterans/first responders
    if user_id:
        c.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        username = c.fetchone()[0]
        if any(word in username.lower() for word in ['vet', 'military', 'responder', 'officer', 'fire', 'ems']):
            techniques.extend([
                ("Moral Injury Exploration",
                 "Many service professionals struggle with conflicts between their actions and their values. "
                 "Would it help to explore this with more nuance - recognizing both the difficult circumstances "
                 "and your good intentions?"),
                 
                ("Operational Stress Management",
                 "Your training taught you to push through extreme situations, but now your mind/body may need "
                 "different care. What would compassionate maintenance look like for your heroic brain?")
            ])
    
    technique, response = random.choice(techniques)
    return f"""
    **CBT Technique: {technique}**  
    {response}
    
    *Remember: Thoughts are mental events, not necessarily facts. The way we interpret situations affects how we feel.*
    """

def generate_act_response(user_input, user_id=None):
    """Acceptance and Commitment Therapy responses"""
    metaphors = [
        ("Chessboard Metaphor",
         "Imagine your thoughts and feelings as pieces on a chessboard. You're the chessboard itself - "
         "the space where the game happens but not defined by any single piece. Can you observe your "
         "current experience with this perspective?"),
         
        ("Passengers on the Bus",
         "Picture your difficult thoughts as noisy passengers on a bus you're driving. You don't have to "
         "make them get off, but you also don't have to obey their directions. Where do you want to steer "
         "your bus today?"),
         
        ("Tug-of-War with a Monster",
         "Struggling with painful thoughts is like a tug-of-war with a monster. The alternative isn't winning, "
         "but dropping the rope. What would dropping the rope look like in this situation?")
    ]
    
    technique, response = random.choice(metaphors)
    return f"""
    **ACT Approach: {technique}**  
    {response}
    
    *Psychological flexibility means making room for discomfort while still moving toward what matters.*
    """

def generate_dbt_response(user_input):
    """Dialectical Behavior Therapy skills"""
    skills = [
        ("DEAR MAN",
         "For effective communication, try:\n"
         "**D**escribe the situation\n**E**xpress your feelings\n"
         "**A**ssert your needs\n**R**einforce positive outcomes\n"
         "**M**indful of the moment\n**A**ppear confident\n**N**egotiate when needed"),
         
        ("TIP for Crisis",
         "To quickly change body chemistry:\n"
         "**T**ip the temperature (cold water on face)\n"
         "**I**ntense exercise\n**P**aced breathing"),
         
        ("Radical Acceptance",
         "Pain + Non-Acceptance = Suffering. Radical acceptance means fully acknowledging reality "
         "without judging it as good or bad. What would need to happen for you to move toward acceptance here?")
    ]
    
    technique, response = random.choice(skills)
    return f"""
    **DBT Skill: {technique}**  
    {response}
    
    *You're building an emotional toolkit - not every tool works for every situation, but having options helps.*
    """

def generate_somatic_response(user_input):
    """Body-based interventions"""
    exercises = [
        ("Grounding Techniques",
         "Let's reconnect with the present:\n1. Name 5 things you see\n2. 4 things you can touch\n"
         "3. 3 sounds you hear\n4. 2 smells you notice\n5. 1 taste in your mouth\n"
         "How does your body feel after this?"),
         
        ("Body Scan",
         "Close your eyes and slowly bring attention to:\n1. Your feet on the floor\n2. Legs supported\n"
         "3. Back against the chair\n4. Hands resting\n5. Facial muscles\nNotice any tension without judgment"),
         
        ("Voo Breathing",
         "For nervous system reset:\n1. Take a deep breath\n2. Exhale with 'Voo' sound (like foghorn)\n"
         "3. Repeat 3-5 times\nThis stimulates the vagus nerve for calm")
    ]
    
    technique, response = random.choice(exercises)
    return f"""
    **Somatic Exercise: {technique}**  
    {response}
    
    *Trauma and stress live in the body - these tools help complete the stress cycle.*
    """


def answer_ai_therapist_question(question, user_id=None):
    """Generate a therapeutic response with proper disclaimers"""
    # Crisis response (same as before)
    crisis_keywords = ["suicide", "kill myself", "end my life", "self-harm", "hurting myself"]
    if any(keyword in question.lower() for keyword in crisis_keywords):
        return crisis_response()
    
    # Determine therapeutic approach based on question content
    question_lower = question.lower()
    
    # Veteran/first responder specific responses
    if user_id:
        c.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        username = c.fetchone()[0] if c.fetchone() else ""
        if any(word in username.lower() for word in ['vet', 'military', 'responder', 'officer', 'fire', 'ems']):
            military_responses = [
                ("I hear the weight of your experience. Many service professionals find it hard to transition "
                 "between 'mission mode' and 'home mode'. What helps you recalibrate?"),
                 
                ("Your training taught you to suppress reactions during crises - now we're working on safe "
                 "ways to process those experiences. What's one small way you could honor your feelings today?"),
                 
                ("The hypervigilance that kept you safe on duty may feel intrusive now. Let's explore "
                 "gradual ways to help your nervous system recognize safety.")
            ]
            if any(word in question_lower for word in ['service', 'deployed', 'mission', 'duty', 'call']):
                return format_response(random.choice(military_responses), "For Service Professionals")
    
    # Therapeutic modality matching
    if any(word in question_lower for word in ['thought', 'think', 'belief', 'mind']):
        return generate_cbt_response(question, user_id)
    elif any(word in question_lower for word in ['accept', 'values', 'present', 'struggle']):
        return generate_act_response(question, user_id)
    elif any(word in question_lower for word in ['emotion', 'regulate', 'intense', 'borderline']):
        return generate_dbt_response(question)
    elif any(word in question_lower for word in ['body', 'pain', 'physic', 'somatic', 'trauma']):
        return generate_somatic_response(question)
    
    # Default multi-modal response
    approaches = [
        generate_cbt_response(question, user_id),
        generate_act_response(question, user_id),
        generate_dbt_response(question),
        generate_somatic_response(question)
    ]
    response = random.choice(approaches)
    
    return f"""
    {response}
    
    *Remember: I'm an AI assistant, not a licensed therapist. For professional help, consider reaching out to:\n
    - Veterans Crisis Line: 988 then press 1\n
    - First Responder Lifeline: 1-800-273-TALK (8255)\n
    - Psychology Today Therapist Finder: https://www.psychologytoday.com*
    """

def format_response(response, technique):
    """Format therapeutic responses consistently"""
    return f"""
    **{technique} Approach**  
    {response}
    
    *This does not replace medical advice. If you're in crisis, please contact a professional or 911 immediately.*
    """

def crisis_response():
    """Enhanced crisis response with veteran/first responder options"""
    return """
    **Important:** I'm deeply concerned about what you're sharing. You're not alone.

    **For Veterans:**
    - 🇺🇸 Veterans Crisis Line: Dial 988 then press 1
    - 📱 Text 838255
    - 💬 Online chat: veteranscrisisline.net

    **For First Responders:**
    - 🚒 First Responder Lifeline: 1-800-273-TALK (8255)
    - 🚔 Code Green Campaign: codegreen.org

    **For Everyone:**
    - 🌍 International help: befrienders.org
    - 💙 Crisis Text Line: Text HOME to 741741 (US/UK/Canada)

    Please reach out now. Your service to others matters - you matter.
    
    st.subheader("When to Seek Immediate Help")
st.write("""
Consider reaching out for professional help if you're experiencing:
- Thoughts of harming yourself or others
- Inability to perform daily tasks
- Extreme mood swings
- Withdrawal from social interactions
- Significant changes in eating/sleeping patterns
- Hearing voices or seeing things others don't
""")


# Self-Assessment Tools
def self_assessments():
    st.header("🧐 Self-Assessment Tools")
    st.write("""
    *These brief screenings can help identify potential mental health concerns, 
    but they are not diagnostic tools. Always consult a professional for assessment.*
    """)
    
    tab1, tab2, tab3 = st.tabs(["Depression", "Anxiety", "Stress"])
    
    with tab1:
        st.subheader("PHQ-9 Depression Screening")
        st.write("Over the last 2 weeks, how often have you been bothered by:")
        
        phq9_questions = [
            "Little interest or pleasure in doing things",
            "Feeling down, depressed, or hopeless",
            "Trouble falling or staying asleep, or sleeping too much",
            "Feeling tired or having little energy",
            "Poor appetite or overeating",
            "Feeling bad about yourself or that you're a failure",
            "Trouble concentrating on things",
            "Moving/speaking slowly or being fidgety/restless",
            "Thoughts that you'd be better off dead or hurting yourself"
        ]
        
        scores = []
        for i, question in enumerate(phq9_questions):
            score = st.radio(
                question,
                options=("Not at all", "Several days", "More than half the days", "Nearly every day"),
                key=f"phq9_{i}"
            )
            scores.append({"Not at all": 0, "Several days": 1, "More than half the days": 2, "Nearly every day": 3}[score])
        
        if st.button("Calculate PHQ-9 Score"):
            total = sum(scores)
            st.write(f"**Your score:** {total}/27")
            
            if total >= 15:
                st.error("""
                **Score suggests moderately severe depression.**
                Consider reaching out to a mental health professional for evaluation.
                """)
            elif total >= 10:
                st.warning("""
                **Score suggests moderate depression.**
                Monitoring your mood and considering professional support may be helpful.
                """)
            elif total >= 5:
                st.info("""
                **Score suggests mild depression.**
                Self-care strategies and monitoring may be beneficial.
                """)
            else:
                st.success("""
                **Score suggests minimal depression.**
                Continue healthy habits that support your wellbeing.
                """)
    
    with tab2:
        st.subheader("GAD-7 Anxiety Screening")
        st.write("Over the last 2 weeks, how often have you been bothered by:")
        
        gad7_questions = [
            "Feeling nervous, anxious, or on edge",
            "Not being able to stop or control worrying",
            "Worrying too much about different things",
            "Trouble relaxing",
            "Being so restless that it's hard to sit still",
            "Becoming easily annoyed or irritable",
            "Feeling afraid as if something awful might happen"
        ]
        
        scores = []
        for i, question in enumerate(gad7_questions):
            score = st.radio(
                question,
                options=("Not at all", "Several days", "More than half the days", "Nearly every day"),
                key=f"gad7_{i}"
            )
            scores.append({"Not at all": 0, "Several days": 1, "More than half the days": 2, "Nearly every day": 3}[score])
        
        if st.button("Calculate GAD-7 Score"):
            total = sum(scores)
            st.write(f"**Your score:** {total}/21")
            
            if total >= 15:
                st.error("""
                **Score suggests severe anxiety.**
                Consider reaching out to a mental health professional for evaluation.
                """)
            elif total >= 10:
                st.warning("""
                **Score suggests moderate anxiety.**
                Monitoring your anxiety and considering professional support may be helpful.
                """)
            elif total >= 5:
                st.info("""
                **Score suggests mild anxiety.**
                Self-care strategies and monitoring may be beneficial.
                """)
            else:
                st.success("""
                **Score suggests minimal anxiety.**
                Continue healthy habits that support your wellbeing.
                """)
    
    with tab3:
        st.subheader("Perceived Stress Scale")
        st.write("How often have you felt or thought this way in the last month:")
        
        pss_questions = [
            "Unable to control important things in your life",
            "Confident about handling personal problems",
            "Things were going your way",
            "Difficulties were piling up so high you couldn't overcome them"
        ]
        
        scores = []
        for i, question in enumerate(pss_questions):
            if i in [1, 2]:  # Positively worded questions
                score = st.radio(
                    question,
                    options=("Never", "Almost never", "Sometimes", "Fairly often", "Very often"),
                    key=f"pss_{i}"
                )
                rev_score = {"Never": 4, "Almost never": 3, "Sometimes": 2, "Fairly often": 1, "Very often": 0}[score]
                scores.append(rev_score)
            else:
                score = st.radio(
                    question,
                    options=("Never", "Almost never", "Sometimes", "Fairly often", "Very often"),
                    key=f"pss_{i}"
                )
                scores.append({"Never": 0, "Almost never": 1, "Sometimes": 2, "Fairly often": 3, "Very often": 4}[score])
        
        if st.button("Calculate Stress Score"):
            total = sum(scores)
            st.write(f"**Your score:** {total}/16")
            
            if total >= 13:
                st.error("""
                **High perceived stress.**
                Consider stress management techniques and professional support.
                """)
            elif total >= 7:
                st.warning("""
                **Moderate perceived stress.**
                Stress management strategies may be helpful.
                """)
            else:
                st.success("""
                **Low perceived stress.**
                Continue healthy coping strategies.
                """)

# AI Therapist Feature
def ai_therapist():
    st.header("💬 Ask an AI Therapist")
    st.warning("""
    **Important Disclaimer:** 
    This AI is not a substitute for professional therapy. It can provide general 
    mental health information but cannot diagnose or treat conditions. 
    For emergencies, please use the [crisis resources](#crisis-support).
    """)
    
    st.write("""
    You can ask general questions about:
    - Coping strategies
    - Understanding emotions
    - Mental health information
    - Self-care techniques
    - Relationship concerns
    """)
    
    question = st.text_area("What would you like to ask?", height=150)
    
    if st.button("Get Response"):
        if not question.strip():
            st.warning("Please enter a question")
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            response = answer_ai_therapist_question(question, st.session_state.get('user_id'))
            
            # Store the question and response
            if 'user_id' in st.session_state:
                c.execute('''INSERT INTO ai_therapist_questions 
                            (user_id, date, question, response) 
                            VALUES (?,?,?,?)''',
                          (st.session_state.user_id, today, question, response))
                conn.commit()
            
            st.subheader("AI Response")
            st.markdown(response)
            
            st.markdown("---")
            st.write("""
            **Remember:**
            - This is not medical advice
            - AI doesn't replace human therapists
            - For emergencies, use crisis resources
            - Consider professional help for persistent concerns
            """)

# Enhanced Self-Care Guidance
def self_care_guidance():
    st.header("🧘 Self-Care Strategies")
    
    tab1, tab2, tab3 = st.tabs(["Quick Relief", "Daily Practices", "Professional Help"])
    
    with tab1:
        st.subheader("Immediate Coping Strategies")
        st.write("""
        **For acute distress:**
        - 🌬️ **5-4-3-2-1 Grounding Technique**: 
          Name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste
        - ❄️ **Temperature Change**: 
          Hold an ice cube or splash cold water on your face
        - 🏃 **Movement**: 
          Walk briskly or do jumping jacks to release tension
        - 📝 **Thought Download**: 
          Write down everything in your mind without filtering
        """)
        
        st.subheader("Calming Breathing Exercises")
        st.write("""
        **4-7-8 Breathing:**
        1. Breathe in quietly through nose for 4 seconds
        2. Hold breath for 7 seconds
        3. Exhale completely through mouth for 8 seconds
        4. Repeat 3-4 times
        
        **Box Breathing:**
        1. Inhale for 4 seconds
        2. Hold for 4 seconds
        3. Exhale for 4 seconds
        4. Hold for 4 seconds
        5. Repeat
        """)
    
    with tab2:
        st.subheader("Daily Mental Health Practices")
        st.write("""
        **Morning Routine:**
        - ☀️ Get sunlight within 1 hour of waking
        - 💧 Drink a glass of water
        - 🧘 5 minutes of mindfulness
        
        **Evening Routine:**
        - 📵 Digital detox 1 hour before bed
        - ✏️ Reflect on 3 good things from your day
        - 🛌 Consistent sleep schedule
        
        **Weekly Practices:**
        - 🚶‍♂️ Regular physical activity
        - 🎨 Creative expression
        - 👥 Social connection
        """)
        
        st.subheader("Nutrition for Mental Health")
        st.write("""
        - 🥑 Omega-3 fatty acids (fish, walnuts, flaxseeds)
        - 🍌 Magnesium-rich foods (leafy greens, nuts, bananas)
        - 🍫 Limited processed sugars
        - 💧 Stay hydrated
        - ☕ Moderate caffeine
        """)
    
    with tab3:
        st.subheader("When to Seek Professional Help")
        st.write("""
        Consider reaching out to a therapist if you experience:
        - Persistent sadness or anxiety
        - Difficulty functioning at work/school
        - Significant changes in sleep/appetite
        - Loss of interest in activities
        - Thoughts of self-harm
        """)
        
        st.subheader("Types of Mental Health Professionals")
        st.write("""
        - **Psychiatrists**: MDs who can prescribe medication
        - **Psychologists**: PhDs providing therapy
        - **LCSWs/LPCs**: Licensed therapists
        - **Counselors**: Various specialties
        """)
        
        st.subheader("Therapy Options")
        st.write("""
        - **CBT**: Focuses on thought patterns
        - **DBT**: Emotion regulation skills
        - **Psychodynamic**: Explores past experiences
        - **Group Therapy**: Peer support
        - **Online Therapy**: Convenient access
        """)

def welcome_page():
    print(f"[WELCOME PAGE] Logo exists? {logo_base64 is not None}")
    if logo_base64:
        st.markdown(f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{logo_base64}" style="max-width: 200px; margin-bottom: 10px;">
            <h3>Guided by science, powered by AI, grounded in care</h3>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="text-align: center;">
            <h3>In2Grative TheraBot</h3>
            <h3>Guided by science, powered by AI, grounded in care</h3>
        </div>
        """, unsafe_allow_html=True)
    
    if not st.session_state.user_id:
        st.header("Welcome to In2Grative TheraBot")
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            with st.form("Login"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    user_id = login_user(username, password)
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
        
        with tab2:
            with st.form("Register"):
                new_username = st.text_input("Choose a username")
                new_email = st.text_input("Email")
                new_password = st.text_input("Choose a password", type="password")
                confirm_password = st.text_input("Confirm password", type="password")
                if st.form_submit_button("Create Account"):
                    if new_password == confirm_password:
                        try:
                            user_id = create_user(new_username, new_password, new_email)
                            st.session_state.user_id = user_id
                            st.session_state.username = new_username
                            st.success("Account created successfully!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Username already exists")
                    else:
                        st.error("Passwords don't match")
    else:
        st.header(f"Welcome back, {st.session_state.get('username', 'Guest')}!")
        st.write("How would you like to engage today?")
        # AI-generated personalized greeting
        ai_response = generate_ai_response(st.session_state.user_id)
        st.info(f"**TheraBot:** {ai_response}")
        
        cols = st.columns(2)
        with cols[0]:
            if st.button("📊 Check my mood", key="btn_mood"):
                st.session_state.current_page = "Mood Scale"
                st.rerun()
            if st.button("📝 Journal", key="btn_journal"):
                st.session_state.current_page = "Journal Entry"
                st.rerun()
            if st.button("🧐 Self-Assessment", key="btn_assessment"):
                st.session_state.current_page = "Self-Assessment"
                st.rerun()
        with cols[1]:
            if st.button("🌿 Self-care", key="btn_selfcare"):
                st.session_state.current_page = "Self-Care Library"
                st.rerun()
            if st.button("📈 View my progress", key="btn_progress"):
                st.session_state.current_page = "Progress Tracking"
                st.rerun()
            if st.button("💬 Ask AI Therapist", key="btn_ai"):
                st.session_state.current_page = "AI Therapist"
                st.rerun()
        
        # Quick mood check-in
        st.subheader("Quick Mood Check")
        mood = st.slider("How are you feeling right now?", 0, 10, 5)
        if st.button("Log Quick Mood", key="btn_quick_mood"):
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute('INSERT INTO mood_entries (user_id, date, mood) VALUES (?,?,?)',
                      (st.session_state.user_id, today, mood))
            conn.commit()
            st.success("Mood logged!")

# Enhanced Mood Scale with tracking
def mood_scale():
    st.header("📊 Mood Tracker")
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Check if mood already logged today
    c.execute('SELECT mood, note FROM mood_entries WHERE user_id = ? AND date = ?',
              (st.session_state.user_id, today))
    existing_entry = c.fetchone()
    
    if existing_entry:
        st.success(f"You already logged your mood today: {existing_entry[0]}/10")
        if existing_entry[1]:
            st.write(f"Note: {existing_entry[1]}")
        if st.button("Update today's mood"):
            c.execute('DELETE FROM mood_entries WHERE user_id = ? AND date = ?',
                      (st.session_state.user_id, today))
            conn.commit()
            st.rerun()
    else:
        mood = st.slider("Rate your mood (0 = Very Low, 10 = Excellent)", 0, 10, 5)
        note = st.text_area("Optional notes about your mood:")
        
        if st.button("Log Mood"):
            c.execute('INSERT INTO mood_entries (user_id, date, mood, note) VALUES (?,?,?,?)',
                      (st.session_state.user_id, today, mood, note))
            conn.commit()
            
            # AI response based on mood
            if mood <= 3:
                response = "I hear you're feeling pretty low right now. That's really tough. 💙"
                st.markdown("### You might find these helpful:")
                with st.expander("Coping Strategies for Low Mood"):
                    st.write("""
                    - Try a grounding exercise (see Self-Care section)
                    - Reach out to someone you trust
                    - Engage in a small, manageable activity
                    - Be gentle with yourself - moods naturally fluctuate
                    """)
            elif mood <= 6:
                response = "Thanks for checking in. Middle-of-the-road days are normal. Maybe we can find a small boost? ✨"
            else:
                response = "That's wonderful to hear! Let's build on this positive energy! 🌟"
            
            st.success(f"**TheraBot:** {response}\n\nMood logged successfully!")
            st.balloons() if mood >= 8 else None
    
    # Mood history visualization
    st.subheader("Your Mood History")
    mood_fig = plot_mood_trend(st.session_state.user_id)
    if mood_fig:
        st.pyplot(mood_fig)
    else:
        st.info("Log more moods to see your trends over time")

# Enhanced Journal with AI memory
def generate_journal_prompt(user_id=None):
    """Dynamic journal prompts with memory of past entries"""
    base_prompts = [
        "What's one thing you want to remember from today?",
        "Describe a moment that surprised you",
        "What emotion visited you most today? What did it need?",
        "Write a letter to your future self about this chapter of your life",
        "What's something you're beginning to understand about yourself?",
        "What nourished you today? What depleted you?"
    ]
    
    # Special prompts for veterans/first responders
    if user_id:
        c.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        username = c.fetchone()[0] if c.fetchone() else ""
        if any(word in username.lower() for word in ['vet', 'military', 'responder', 'officer', 'fire', 'ems']):
            base_prompts.extend([
                "How has your service shaped how you see the world today?",
                "What's one strength from your service that serves you now?",
                "If your trauma could speak, what would it want others to understand?",
                "What does 'safety' mean to your body now compared to during service?"
            ])
    
    # Context-aware prompts based on recent entries
    if user_id:
        c.execute('SELECT entry FROM journal_entries WHERE user_id = ? ORDER BY date DESC LIMIT 1', (user_id,))
        last_entry = c.fetchone()
        if last_entry:
            last_text = last_entry[0].lower()
            if 'happy' in last_text or 'joy' in last_text:
                base_prompts.extend([
                    "What conditions helped create this positive experience?",
                    "How might you cultivate more moments like this?"
                ])
            if 'stress' in last_text or 'anxious' in last_text:
                base_prompts.extend([
                    "What did this challenge reveal about your coping skills?",
                    "If this stress were a wave in the ocean, how might you ride it?"
                ])
    
    return random.choice(base_prompts)
def journal_entry():
    st.header("📝 Reflective Journal")
    
    # Use dynamic prompt generator
    prompt_options = ["Free writing"] + [generate_journal_prompt(st.session_state.user_id) for _ in range(5)]
    selected_prompt = st.selectbox("Choose a journal prompt or write freely:", prompt_options)
    
    if selected_prompt != "Free writing":
        st.write(f"**Prompt:** {selected_prompt}")
        st.caption("💡 Prompt generated based on your recent entries and profile")
    
    entry = st.text_area("Write your thoughts here:", height=300,
                        placeholder="Try to write for at least 5 minutes without stopping...")
    
    if st.button("Save Entry"):
        if len(entry) < 50:
            st.warning("That's quite brief! Journaling works best when we push past surface thoughts.")
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            sentiment = analyze_journal_sentiment(entry)
            
            c.execute('INSERT INTO journal_entries (user_id, date, entry, sentiment) VALUES (?,?,?,?)',
                      (st.session_state.user_id, today, entry, sentiment))
            conn.commit()
            
            # Enhanced AI response
            ai_response = generate_journal_feedback(entry, sentiment, st.session_state.user_id)
            st.success(f"**TheraBot:** {ai_response}\n\nJournal saved!")
            
            # Show connection to previous entry if available
            show_entry_connections(st.session_state.user_id, today)

def generate_journal_feedback(entry, sentiment, user_id):
    """Generate personalized journal feedback"""
    entry_lower = entry.lower()
    positive_words = sum(1 for word in ['happy', 'joy', 'proud', 'excited', 'grateful'] if word in entry_lower)
    negative_words = sum(1 for word in ['sad', 'angry', 'anxious', 'stress', 'tired'] if word in entry_lower)
    
    if sentiment > 0.3:
        responses = [
            "Your writing shines with positivity! Notice how describing these moments amplifies their power.",
            "These reflections are like sunshine breaking through clouds. What conditions helped create this brightness?",
            "Your words carry hope. Consider saving this entry to revisit on harder days."
        ]
        if 'grat' in entry_lower:
            responses.append("Practicing gratitude rewires our brains! You might enjoy a 'three good things' journal for 21 days.")
    elif sentiment < -0.3:
        responses = [
            "Writing about challenges takes courage. You're already changing your relationship to these feelings by naming them.",
            "Hard emotions demand space. By giving them room here, you prevent them from taking over elsewhere.",
            "This honest expression is the first step toward healing. Would a coping strategy help right now?"
        ]
        if any(word in entry_lower for word in ['alone', 'lonely']):
            responses.append("Loneliness is profoundly painful. Many find comfort knowing this feeling is shared by others - would resources on connection help?")
    else:
        responses = [
            "Your balanced reflection shows self-awareness. Noticing without judgment is a powerful skill.",
            "You're mapping your inner landscape - both the peaks and valleys make the terrain complete.",
            "This thoughtful processing builds emotional resilience over time."
        ]
    
    # Add therapeutic technique suggestion
    techniques = [
        "\n\nConsider trying: One-sentence journaling daily for consistency.",
        "\n\nExperiment: Highlight action verbs in your entry - where could you take small steps?",
        "\n\nPrompt for next time: What's the story I'm telling myself about this? Is there another version?"
    ]
    
    return random.choice(responses) + random.choice(techniques)

def show_entry_connections(user_id, current_date):
    """Show connections between current and past journal entries"""
    c.execute('''SELECT entry FROM journal_entries 
                 WHERE user_id = ? AND date != ? 
                 ORDER BY RANDOM() LIMIT 1''',
              (user_id, current_date))
    prev_entry = c.fetchone()
    
    if prev_entry:
        st.info("**Bridge to Past Writing:**\n" + 
               random.choice([
                   "This connects to when you wrote about similar themes before.",
                   "Your current reflections seem to dialogue with your past thoughts.",
                   "Notice any patterns between this entry and your previous writing?"
               ]))

# Enhanced Self-Care Library with tracking
def get_self_care_activities(category, user_id=None):
    """Expanded self-care suggestions with timing options"""
    activities = {
        "Morning Routine": [
            ("Sunlight within 30 mins of waking", "Circadian Health", 5),
            ("Hydration with electrolytes", "Physical", 2),
            ("3 things you're grateful for", "Emotional", 3),
            ("Stretch like a cat (full body)", "Physical", 4),
            ("Set 1 intention for the day", "Mindset", 2)
        ],
        "Evening Wind-Down": [
            ("Digital sunset (no screens)", "Sleep", 60),
            ("Gentle neck rolls", "Physical", 3),
            ("'Rose, Thorn, Bud' reflection", "Emotional", 5),
            ("4-7-8 breathing", "Relaxation", 4),
            ("Cool down room temperature", "Sleep", 1)
        ],
        "Weekly Reset": [
            ("Nature immersion (20+ mins)", "Mental", 30),
            ("Creative play (no rules)", "Joy", 45),
            ("Social connection", "Relationships", 60),
            ("Body scan meditation", "Mindfulness", 20),
            ("Personal retreat (2+ hours alone)", "Recharge", 120)
        ],
        "Nutrition Boosters": [
            ("Omega-3 rich meal", "Brain Health", 15),
            ("Fermented food for gut health", "Physical", 5),
            ("Herbal tea ritual", "Mindfulness", 10),
            ("Protein with each meal", "Energy", 1),
            ("Rainbow plate challenge", "Variety", 20)
        ],
        "For Service Professionals": [
            ("Tactical breathing (box breath)", "Regulation", 5),
            ("After-action review (non-judgmental)", "Processing", 10),
            ("Comrades check-in", "Connection", 15),
            ("Equipment maintenance metaphor", "Self-Care", 20),
            ("Boundary practice (saying no)", "Protection", 5)
        ]
    }
    
    # Add military/veteran specific activities if user matches
    if user_id:
        c.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        username = c.fetchone()[0] if c.fetchone() else ""
        if any(word in username.lower() for word in ['vet', 'military', 'responder', 'officer', 'fire', 'ems']):
            activities["For Service Professionals"].extend([
                ("Duty-to-civilian transition ritual", "Mindset", 10),
                ("Shared humanity reflection", "Perspective", 15),
                ("Adrenaline dump visualization", "Regulation", 8)
            ])
    
    return activities.get(category, [])
# Medical Disclaimer
def show_disclaimer():
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚠️ Important Disclaimer"):
        st.write("""
        **This application is not a substitute for professional medical advice, diagnosis, or treatment.**
        
        - Always seek the advice of your physician or qualified mental health provider
        - Never disregard professional medical advice or delay seeking it
        - In case of emergency, contact your local emergency services
        
        The AI responses are for informational purposes only and should not be considered medical advice.
        """)
def self_care_library():
    st.header("🌿 Self-Care Resource Library")
    
    tab1, tab2, tab3 = st.tabs(["Browse Activities", "Your Self-Care History", "Self-Care Guidance"])
    
    with tab1:
        category = st.selectbox("Browse by category:", [
            "Morning Routine",
            "Evening Wind-Down",
            "Weekly Reset",
            "Nutrition Boosters",
            "For Service Professionals"
        ])
        
        activities = get_self_care_activities(category, st.session_state.user_id)
        
        st.subheader(f"{category} Activities")
        cols = st.columns(2)
        for i, (activity, _, duration) in enumerate(activities):
            with cols[i%2]:
                with st.expander(f"⏱️ {duration} min | {activity}"):
                    st.write(f"**Category:** {_}")
                    if st.button("Log This Activity", key=f"log_{i}"):
                        log_self_care(activity, category, duration)
        
    with tab2:
        # ... [keep existing history tab code] ...
        
    with tab3:
        # Enhanced self-care guidance
        st.subheader("Science-Backed Self-Care Strategies")
        
        approach = st.radio("Focus Area:", 
                           ["Stress Relief", "Sleep Support", "Emotional Balance", "For Service Professionals"])
        
        if approach == "Stress Relief":
            st.write("""
            **Polyvagal Theory Techniques:**
            - 🎵 Humming/Singing: Activates vagus nerve
            - 👀 Peripheral Vision: Signals safety to brain
            - 🤝 Social Connection: Co-regulation
            
            **Cortisol Management:**
            - Morning sunlight exposure
            - Protein-rich breakfast
            - Afternoon movement breaks
            """)
            
        elif approach == "For Service Professionals":
            st.write("""
            **Operational Stress Management:**
            - 🚨 Post-Call Rituals: Physical shake-off + cognitive closure
            - 🛡️ Psychological Body Armor: Pre-shift intention setting
            - 🔄 Duty-to-Home Transition: Dedicated clothing change + 15min buffer
            
            **Moral Injury Support:**
            - Peer support groups
            - Expressive writing
            - Values clarification exercises
            """)

def main():
    # Add debugging code for the image file issue
    import os
    from pathlib import Path
    
    print(f"[MAIN] Current working directory: {os.getcwd()}")
    
    # Debug image path
    image_path = r"C:\TherabotApp\In2Grative_Therapy_Logo_Design.png"
    print(f"[MAIN] Does logo exist at full path? {os.path.exists(image_path)}")
    if not os.path.exists(image_path):
        print(f"[ERROR] Could not find logo at: {image_path}")
        print(f"[DEBUG] Directory contents: {os.listdir(os.path.dirname(image_path))}")
    
    # Initialize session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Welcome"
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    
    # Sidebar navigation (only show when logged in)
    if st.session_state.user_id:
        with st.sidebar:
            print(f"[SIDEBAR] Logo exists? {logo_base64 is not None}")
            if logo_base64:
                st.markdown(f"""
                <div style="text-align: center;">
                    <img src="data:image/png;base64,{logo_base64}" style="max-width: 200px; margin-bottom: 10px;">
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="text-align: center;">
                    <h3>In2Grative TheraBot</h3>
                </div>
                """, unsafe_allow_html=True)            
            st.markdown(f"### Welcome, {st.session_state.username}!")
            
            nav_options = {
                "Welcome": "🏠",
                "Mood Scale": "📊",
                "Journal Entry": "📝",
                "Self-Care Library": "🌿",
                "Progress Tracking": "📈",
                "Self-Assessment": "🧐",
                "AI Therapist": "💬",
                "Crisis Support": "🆘"
            }
            
            for page, icon in nav_options.items():
                if st.button(f"{icon} {page}"):
                    st.session_state.current_page = page
            
            st.markdown("---")
            st.markdown(f"**Today is:** {datetime.now().strftime('%A, %B %d')}")
            
            if st.button("🔐 Logout"):
                st.session_state.user_id = None
                st.session_state.current_page = "Welcome"
                st.rerun()
            
            # Show disclaimer in sidebar
            show_disclaimer()
    
    # Page routing
    if st.session_state.current_page == "Welcome":
        welcome_page()
    elif st.session_state.user_id:
        if st.session_state.current_page == "Mood Scale":
            mood_scale()
        elif st.session_state.current_page == "Journal Entry":
            journal_entry()
        elif st.session_state.current_page == "Self-Care Library":
            self_care_library()
        elif st.session_state.current_page == "Progress Tracking":
            progress_tracking()
        elif st.session_state.current_page == "Self-Assessment":
            self_assessments()
        elif st.session_state.current_page == "AI Therapist":
            ai_therapist()
        elif st.session_state.current_page == "Crisis Support":
            crisis_support()
    else:
        st.warning("Please login to access this page")
        st.session_state.current_page = "Welcome"
        st.rerun()
if __name__ == "__main__":
    main()