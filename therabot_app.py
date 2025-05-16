import os
try:
    __file__
except NameError:
    __file__ = os.path.abspath('')  

import streamlit as st  # Set page config immediately after this
st.set_page_config(
    page_title="In2Grative TheraBot",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded"
)

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

conn.commit()

# (Rest of your original code follows here...)

# Make sure all Streamlit calls before this point are removed or moved after set_page_config

conn.commit()

# Set page configuration
st.set_page_config(
    page_title="In2Grative TheraBot",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded")

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
image_path = r"C:\Users\reanh\OneDrive\Desktop\in2grative_therabot_gsheets_bundle\In2Grative_Therapy_Logo_Design.png"
logo_base64 = get_image_base64(image_path)
print(f"[INITIAL LOAD] Logo exists? {logo_base64 is not None}")

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


def answer_ai_therapist_question(question, user_id=None):
    """Generate a response to a mental health question with appropriate disclaimers"""
    # Define common topics and responses
    common_topics = {
        "anxiety": "Anxiety can feel overwhelming, but techniques like deep breathing, grounding exercises, and challenging anxious thoughts can help. Would you like some specific exercises?",
        "depression": "Depression often makes everything feel harder. Small steps like maintaining a routine, getting sunlight, and reaching out to loved ones can help. Have you considered speaking with a professional?",
        "stress": "Stress management often involves identifying sources of stress, setting boundaries, and practicing relaxation techniques. What's causing you the most stress right now?",
        "relationships": "Relationships can be complex. Good communication involves active listening and expressing your needs clearly. What aspect of your relationships are you finding challenging?",
        "self-esteem": "Building self-esteem is a process. Try focusing on your strengths, practicing self-compassion, and setting achievable goals. What's one thing you appreciate about yourself today?",
        "sleep": "Good sleep hygiene includes consistent bedtimes, limiting screens before bed, and creating a restful environment. Are you having trouble falling asleep or staying asleep?"
    }
    
    # Check for crisis keywords
    crisis_keywords = ["suicide", "kill myself", "end my life", "self-harm", "hurting myself"]
    if any(keyword in question.lower() for keyword in crisis_keywords):
        return """
        **Important:** I'm deeply concerned about what you're sharing. 
        You're not alone, and there are people who want to help:
        
        - In the U.S.: Call/text 988 or chat at 988lifeline.org
        - UK: Call 116 123 (Samaritans)
        - International: Find a crisis line at www.befrienders.org
        
        Please reach out to a trusted person or professional right now. 
        Your life matters.
        """
    
    # Check for common topics
    for topic, response in common_topics.items():
        if topic in question.lower():
            return f"""
            **Regarding {topic}:** {response}
            
            *Remember: I'm an AI assistant, not a licensed therapist. 
            For professional help, consider reaching out to a mental health professional.*
            """
    
    # Default response
    return """
    Thank you for sharing. That sounds like an important concern. 
    While I can offer general support, I encourage you to discuss this with a mental health professional for personalized guidance.
    
    Some things that might help:
    - Journaling about your thoughts and feelings
    - Talking with trusted friends/family
    - Practicing self-care activities
    
    Would you like me to suggest some resources that might be relevant?
    """

# Data Visualization Functions
def plot_mood_trend(user_id):
    c.execute('SELECT date, mood FROM mood_entries WHERE user_id = ? ORDER BY date', (user_id,))
    data = c.fetchall()
    if len(data) < 2:
        return None
    
    df = pd.DataFrame(data, columns=['Date', 'Mood'])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    
    fig, ax = plt.subplots(figsize=(10, 4))
    df['Mood'].plot(ax=ax, marker='o', linestyle='-')
    ax.set_ylim(0, 10)
    ax.set_title('Your Mood Over Time')
    ax.set_ylabel('Mood (0-10)')
    ax.grid(True)
    
    return fig

def plot_self_care_categories(user_id):
    c.execute('SELECT category, COUNT(*) FROM self_care_activities WHERE user_id = ? GROUP BY category', (user_id,))
    data = c.fetchall()
    if not data:
        return None
    
    df = pd.DataFrame(data, columns=['Category', 'Count'])
    
    fig, ax = plt.subplots(figsize=(8, 8))
    df.set_index('Category')['Count'].plot.pie(ax=ax, autopct='%1.1f%%')
    ax.set_title('Self-Care Activity Distribution')
    ax.set_ylabel('')
    
    return fig

# Crisis Support Resources
def crisis_support():
    st.header("🆘 Immediate Support Resources")
    st.warning("""
    **If you're in crisis or experiencing thoughts of self-harm, please reach out now:**
    
    - 🇺🇸 **U.S. National Suicide Prevention Lifeline**: Call/text **988** or chat at [988lifeline.org](https://988lifeline.org)
    - 🇬🇧 **UK Samaritans**: Call **116 123** or email jo@samaritans.org
    - 🌍 **International Help**: Find crisis centers at [Befrienders Worldwide](https://www.befrienders.org)
    - 💬 **Crisis Text Line**: Text HOME to **741741** in the U.S.
    """)
    
    st.subheader("Additional Mental Health Resources")
    st.write("""
    - 🏥 [National Alliance on Mental Illness (NAMI)](https://www.nami.org)
    - 🧠 [Mental Health America](https://www.mhanational.org)
    - 🧘 [Headspace for Meditation](https://www.headspace.com)
    - 📱 [Talkspace Online Therapy](https://www.talkspace.com)
    - 🌎 [Psychology Today Therapist Finder](https://www.psychologytoday.com)
    """)
    
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
            if st.button("📊 Check my mood"):
                st.session_state.current_page = "Mood Scale"
                st.rerun()
            if st.button("📝 Journal"):
                st.session_state.current_page = "Journal Entry"
                st.rerun()
            if st.button("🧐 Self-Assessment"):
                st.session_state.current_page = "Self-Assessment"
                st.rerun()
        with cols[1]:
            if st.button("🌿 Self-care"):
                st.session_state.current_page = "Self-Care Library"
                st.rerun()
            if st.button("📈 View my progress"):
                st.session_state.current_page = "Progress Tracking"
                st.rerun()
            if st.button("💬 Ask AI Therapist"):
                st.session_state.current_page = "AI Therapist"
                st.rerun()
        
        # Quick mood check-in
        st.subheader("Quick Mood Check")
        mood = st.slider("How are you feeling right now?", 0, 10, 5)
        if st.button("Log Quick Mood"):
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
def journal_entry():
    st.header("📝 Reflective Journal")
    
    # Journal prompt generator
    prompts = [
        "What's been on your mind lately?",
        "What are you grateful for today?",
        "Describe a challenge you're facing and how you might approach it",
        "What's one thing you'd like to remember from today?",
        "Write a letter to your future self",
        "What emotions have you felt most strongly this week?"
    ]
    
    selected_prompt = st.selectbox("Choose a journal prompt or write freely:", 
                                  ["Free writing"] + prompts)
    
    if selected_prompt != "Free writing":
        st.write(f"**Prompt:** {selected_prompt}")
    
    entry = st.text_area("Write your thoughts here:", height=250)
    
    if st.button("Save Entry"):
        if len(entry) < 20:
            st.warning("That's quite brief! Are you sure you don't want to add more?")
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            sentiment = analyze_journal_sentiment(entry)
            
            c.execute('INSERT INTO journal_entries (user_id, date, entry, sentiment) VALUES (?,?,?,?)',
                      (st.session_state.user_id, today, entry, sentiment))
            conn.commit()
            
            # AI response based on content
            if sentiment > 0.2:
                ai_response = "I notice positive tones in your writing. Celebrate these moments!"
            elif sentiment < -0.2:
                ai_response = "Your words reflect some difficulty. Remember, writing about challenges is already a step toward processing them."
            else:
                ai_response = "Thank you for sharing these reflections. Regular journaling builds self-awareness."
            
            st.success(f"**TheraBot:** {ai_response}\n\nJournal saved!")
            
            # Connect to previous entries if available
            c.execute('SELECT entry FROM journal_entries WHERE user_id = ? AND date != ? ORDER BY date DESC LIMIT 1',
                      (st.session_state.user_id, today))
            prev_entry = c.fetchone()
            
            if prev_entry:
                st.info("**Connection to previous entry:** You might reflect on how this relates to what you wrote before.")

# Enhanced Self-Care Library with tracking
def self_care_library():
    st.header("🌿 Self-Care Resource Library")
    
    tab1, tab2, tab3 = st.tabs(["Browse Activities", "Your Self-Care History", "Self-Care Guidance"])
    
    with tab1:
        category = st.selectbox("Browse by category:", [
            "Quick Pick-Me-Ups (5 min or less)",
            "Emotional Care",
            "Physical Wellbeing",
            "Social Connection",
            "Productivity Boosters",
            "Creativity Sparks"
        ])
        
        if category == "Quick Pick-Me-Ups (5 min or less)":
            activities = [
                ("Deep breathing (4-7-8 technique)", "Relaxation", 5),
                ("Stretch break", "Physical", 5),
                ("Hydration station", "Physical", 2),
                ("Mini dance party", "Joy", 5),
                ("Nature gaze", "Mindfulness", 3)
            ]
        elif category == "Emotional Care":
            activities = [
                ("Self-compassion break", "Emotional", 3),
                ("Gratitude moment", "Emotional", 5),
                ("Emotional check-in", "Emotional", 5),
                ("Comfort object", "Emotional", 2)
            ]
        elif category == "Physical Wellbeing":
            activities = [
                ("Posture reset", "Physical", 1),
                ("Hydration check", "Physical", 1),
                ("Energy snack", "Physical", 5),
                ("Micro-movement", "Physical", 3)
            ]
        elif category == "Social Connection":
            activities = [
                ("Reach out to someone", "Social", 10),
                ("Social media detox", "Social", 30),
                ("Kindness boost", "Social", 5),
                ("Memory lane", "Social", 10)
            ]
        elif category == "Productivity Boosters":
            activities = [
                ("Pomodoro technique", "Focus", 25),
                ("Two-minute rule", "Focus", 2),
                ("Priority triage", "Focus", 10),
                ("Declutter sprint", "Focus", 15)
            ]
        elif category == "Creativity Sparks":
            activities = [
                ("Doodle break", "Creative", 10),
                ("Word play", "Creative", 5),
                ("Color therapy", "Creative", 15),
                ("Creative consumption", "Creative", 20)
            ]
        
        st.subheader(f"{category} Activities")
        for activity, _, duration in activities:
            if st.button(f"{activity} ({duration} min)"):
                today = datetime.now().strftime("%Y-%m-%d")
                c.execute('INSERT INTO self_care_activities (user_id, date, activity, category, duration) VALUES (?,?,?,?,?)',
                          (st.session_state.user_id, today, activity, category, duration))
                conn.commit()
                st.success(f"Logged: {activity}!")
    
    with tab2:
        st.subheader("Your Self-Care History")
        
        # Date range selector
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date", start_date)
        with col2:
            end_date = st.date_input("End date", end_date)
        
        # Fetch activities in date range
        c.execute('''SELECT date, activity, duration FROM self_care_activities 
                     WHERE user_id = ? AND date BETWEEN ? AND ?
                     ORDER BY date DESC''',
                  (st.session_state.user_id, start_date.strftime("%Y-%m-%d"), 
                   end_date.strftime("%Y-%m-%d")))
        activities = c.fetchall()
        
        if activities:
            st.write(f"Found {len(activities)} activities:")
            for date, activity, duration in activities:
                st.write(f"- {date}: {activity} ({duration} min)")
            
            # Visualization
            st.subheader("Activity Distribution")
            fig = plot_self_care_categories(st.session_state.user_id)
            if fig:
                st.pyplot(fig)
            else:
                st.info("Complete more activities to see visualizations")
        else:
            st.info("No self-care activities logged in this period")
    
    with tab3:
        self_care_guidance()

# Progress Tracking Dashboard
def progress_tracking():
    st.header("📈 Your Progress Dashboard")
    
    tab1, tab2, tab3 = st.tabs(["Mood Trends", "Journal Insights", "Self-Care Report"])
    
    with tab1:
        st.subheader("Mood Over Time")
        mood_fig = plot_mood_trend(st.session_state.user_id)
        if mood_fig:
            st.pyplot(mood_fig)
            
            # Mood statistics
            c.execute('SELECT AVG(mood), MIN(mood), MAX(mood) FROM mood_entries WHERE user_id = ?',
                      (st.session_state.user_id,))
            avg, min_mood, max_mood = c.fetchone()
            st.write(f"**Average mood:** {avg:.1f}/10")
            st.write(f"**Range:** {min_mood} (low) to {max_mood} (high)")
        else:
            st.info("Log more moods to see trends")
    
    with tab2:
        st.subheader("Journal Insights")
        c.execute('SELECT date, entry, sentiment FROM journal_entries WHERE user_id = ? ORDER BY date DESC LIMIT 5',
                  (st.session_state.user_id,))
        entries = c.fetchall()
        
        if entries:
            # Sentiment over time
            df = pd.DataFrame(entries, columns=['Date', 'Entry', 'Sentiment'])
            df['Date'] = pd.to_datetime(df['Date'])
            
            fig, ax = plt.subplots(figsize=(10, 4))
            df.plot(x='Date', y='Sentiment', ax=ax, marker='o')
            ax.set_title('Journal Sentiment Trend')
            ax.set_ylabel('Sentiment (-1 to 1)')
            ax.grid(True)
            st.pyplot(fig)
            
            # Common themes
            st.write("**Recent Journal Themes**")
            all_text = " ".join([e[1] for e in entries]).lower()
            common_words = pd.Series(all_text.split()).value_counts().head(10)
            st.bar_chart(common_words)
        else:
            st.info("Write more journal entries to see insights")
    
    with tab3:
        st.subheader("Self-Care Report")
        c.execute('''SELECT category, COUNT(*), SUM(duration) 
                     FROM self_care_activities 
                     WHERE user_id = ?
                     GROUP BY category''',
                  (st.session_state.user_id,))
        category_data = c.fetchall()
        
        if category_data:
            df = pd.DataFrame(category_data, columns=['Category', 'Count', 'Total Minutes'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Activities by Category**")
                st.bar_chart(df.set_index('Category')['Count'])
            
            with col2:
                st.write("**Time Spent**")
                st.bar_chart(df.set_index('Category')['Total Minutes'])
            
            st.write("**Recent Activities**")
            c.execute('''SELECT date, activity, duration 
                         FROM self_care_activities 
                         WHERE user_id = ? 
                         ORDER BY date DESC LIMIT 5''',
                      (st.session_state.user_id,))
            recent = c.fetchall()
            for date, activity, duration in recent:
                st.write(f"- {date}: {activity} ({duration} min)")
        else:
            st.info("Log self-care activities to see your report")

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

# Main app logic
def main():
    # Add debugging code for the image file issue
    import os
    from pathlib import Path
    
    print(f"[MAIN] Current working directory: {os.getcwd()}")
    
    # Use the same full path that works elsewhere
    image_path = r"C:\Users\reanh\OneDrive\Desktop\in2grative_therabot_gsheets_bundle\In2Grative_Therapy_Logo_Design.png"
    print(f"[MAIN] Does logo exist at full path? {os.path.exists(image_path)}")
    
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