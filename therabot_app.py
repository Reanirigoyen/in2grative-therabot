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
    positive_words = ['happy', 'good', 'great', 'joy', 'excited', 'calm', 'peaceful', 'proud', 'grateful']
    negative_words = ['sad', 'bad', 'angry', 'anxious', 'stress', 'depressed', 'trauma', 'triggered', 'fear']
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
    user_type, trauma_history = get_user_type(user_id)
    global c
    c.execute('SELECT entry FROM journal_entries WHERE user_id = ? ORDER BY date DESC LIMIT 3', (user_id,))
    recent_entries = c.fetchall()
    c.execute('SELECT mood FROM mood_entries WHERE user_id = ? ORDER BY date DESC LIMIT 7', (user_id,))
    mood_data = c.fetchall()
    avg_mood = sum([m[0] for m in mood_data])/len(mood_data) if mood_data else 5
    
    # Customize response based on user type
    if user_type == 'veteran':
        base_response = "Thank you for your service. "
    elif user_type == 'first_responder':
        base_response = "Your work is deeply valued. "
    else:
        base_response = ""
    
    if recent_entries:
        sentiment = analyze_journal_sentiment(" ".join([e[0] for e in recent_entries]))
        if sentiment > 0.3:
            return base_response + "I'm noticing some positive themes in your recent reflections. Let's build on this momentum!"
        elif sentiment < -0.3:
            if trauma_history:
                return base_response + "Your recent entries suggest you've been facing some challenges related to past experiences. Would you like to explore some trauma-informed coping strategies?"
            return base_response + "Your recent entries suggest you've been facing some challenges. Remember growth often comes through difficulty."
    if avg_mood < 4:
        return base_response + "I see your mood has been lower recently. Would you like to explore some coping strategies?"
    return base_response + "How are you feeling today compared to yesterday?"

def generate_dynamic_journal_prompt(user_id):
    c.execute('SELECT entry FROM journal_entries WHERE user_id = ? ORDER BY date DESC LIMIT 5', (user_id,))
    recent_entries = [e[0] for e in c.fetchall()]
    
    if not recent_entries:
        return random.choice([
            "What's been on your mind lately?",
            "What are you grateful for today?",
            "Describe a challenge you're facing and how you might approach it"
        ])
    
    # Analyze for recurring themes
    all_text = " ".join(recent_entries).lower()
    themes = {
        'relationships': ['friend', 'partner', 'family', 'relationship', 'love', 'argue'],
        'work': ['work', 'job', 'career', 'boss', 'colleague'],
        'trauma': ['trauma', 'trigger', 'memory', 'flashback', 'ptsd'],
        'anxiety': ['anxious', 'worry', 'fear', 'panic', 'nervous'],
        'achievement': ['accomplish', 'proud', 'success', 'achievement', 'goal']
    }
    
    detected_themes = []
    for theme, keywords in themes.items():
        if any(keyword in all_text for keyword in keywords):
            detected_themes.append(theme)
    
    # Generate personalized prompt
    if not detected_themes:
        return random.choice([
            "What's one thing you'd like to remember from today?",
            "Write a letter to your future self",
            "What emotions have you felt most strongly this week?"
        ])
    
    main_theme = random.choice(detected_themes)
    if main_theme == 'relationships':
        return random.choice([
            "How have your relationships impacted your mood recently?",
            "What's one relationship dynamic you'd like to improve?",
            "Describe a meaningful connection you've experienced recently"
        ])
    elif main_theme == 'work':
        return random.choice([
            "How is your work affecting your wellbeing?",
            "What's one work-related stressor you'd like to manage better?",
            "Describe a work achievement you're proud of"
        ])
    elif main_theme == 'trauma':
        return random.choice([
            "What helps you feel grounded when recalling difficult experiences?",
            "How have you grown from past challenges?",
            "What's one way you've learned to care for yourself when triggered?"
        ])
    elif main_theme == 'anxiety':
        return random.choice([
            "What situations tend to trigger your anxiety?",
            "Describe a time you successfully managed anxious feelings",
            "What physical sensations do you notice when anxious?"
        ])
    elif main_theme == 'achievement':
        return random.choice([
            "What personal strengths helped you achieve recent successes?",
            "How do you celebrate your accomplishments?",
            "What goals are you working toward now?"
        ])
    
    return "What would you like to reflect on today?"

# Enhanced AI Therapist Responses with Different Modalities
def answer_ai_therapist_question(question, user_id=None, therapy_mode='CBT'):
    """Generate a response to a mental health question with appropriate disclaimers"""
    user_type, trauma_history = get_user_type(user_id) if user_id else ('general', 0)
    
    # Define common topics and responses for different therapy modes
    therapy_responses = {
        'CBT': {
            "anxiety": "Let's examine the thoughts behind your anxiety. What evidence supports or contradicts your anxious thoughts?",
            "depression": "Negative thought patterns often fuel depression. Can you identify any cognitive distortions in your thinking?",
            "stress": "Stress often comes from our appraisal of situations. How might you reframe this stressful situation?",
            "relationships": "Our thoughts about relationships affect our feelings. What automatic thoughts come up in your relationships?"
        },
        'ACT': {
            "anxiety": "Rather than fighting anxiety, can you make space for it while still taking valued actions?",
            "depression": "What values are important to you, and how might you take small steps toward them despite depressive feelings?",
            "stress": "Stress is inevitable, but suffering is optional. What would acceptance of this situation look like?",
            "relationships": "What core values do you want to guide your relationships?"
        },
        'DBT': {
            "anxiety": "Let's try a distress tolerance skill. Would paced breathing or self-soothing with senses help right now?",
            "depression": "Emotion regulation begins with naming emotions. What specific emotions are you feeling?",
            "stress": "In crisis, remember STOP: Stop, Take a step back, Observe, Proceed mindfully.",
            "relationships": "DEAR MAN skills can help: Describe, Express, Assert, Reinforce, stay Mindful, Appear confident, Negotiate."
        },
        'IFS': {
            "anxiety": "Which part of you feels anxious? Can you describe it with curiosity rather than judgment?",
            "depression": "A depressed part may be trying to protect you. What might it be protecting you from?",
            "stress": "When stressed, which parts of you are activated? Is there a calm Self that can witness them?",
            "relationships": "Which parts of you get activated in relationships? How might they interact with others' parts?"
        },
        'CPT': {
            "trauma": "Let's examine stuck points in your trauma narrative. What thoughts feel most distressing?",
            "anxiety": "Trauma can create unhelpful beliefs. What new understanding might challenge these beliefs?",
            "depression": "How might trauma-related beliefs be affecting your current mood?",
            "relationships": "How might trauma experiences be influencing your relationship patterns?"
        },
        'Somatic': {
            "trauma": "Notice any body sensations as we discuss this. Where do you feel it in your body?",
            "anxiety": "Let's ground in the body. Can you feel your feet on the floor and your breath moving?",
            "depression": "Depression often shows in the body. What physical sensations accompany your low mood?",
            "relationships": "How does your body respond when thinking about important relationships?"
        }
    }
    
    # Specialized responses for veterans and first responders
    specialized_responses = {
        'veteran': {
            "combat": "Combat experiences can have lasting impacts. How are these memories affecting you now?",
            "transition": "Transitioning to civilian life brings challenges. What aspects feel most difficult?",
            "moral_injury": "Moral injury involves deep wounds. What thoughts keep coming up about these experiences?"
        },
        'first_responder': {
            "critical_incident": "Critical incidents can accumulate. How has this recent event affected you?",
            "shift_work": "Irregular schedules disrupt wellbeing. How are you managing sleep and recovery?",
            "compassion_fatigue": "Caring constantly can deplete reserves. What replenishes your sense of purpose?"
        }
    }
    
    # Check for crisis keywords
    crisis_keywords = ["suicide", "kill myself", "end my life", "self-harm", "hurting myself"]
    if any(keyword in question.lower() for keyword in crisis_keywords):
        return """
        **Important:** I'm deeply concerned about what you're sharing. 
        You're not alone, and there are people who want to help:
        
        - Veterans/Military: Press 1 after dialing 988 (U.S.)
        - First Responders: 1-800-267-5463 (Canada) or 1-888-731-3473 (U.S.)
        - General Crisis: Call/text 988 or chat at 988lifeline.org
        
        Please reach out to a trusted person or professional right now. 
        Your life matters.
        """
    
    # Check for specialized topics first
    if user_type in ['veteran', 'first_responder']:
        for topic, response in specialized_responses[user_type].items():
            if topic in question.lower():
                return f"""
                **Regarding your experience:** {response}
                
                *{therapy_mode} perspective:* {therapy_responses[therapy_mode].get('trauma', 'This seems important to explore further.')}
                
                *Remember: I'm an AI assistant, not a licensed therapist. 
                For professional help, consider reaching out to a mental health professional.*
                """
    
    # Check for trauma-related topics
    trauma_keywords = ["trauma", "ptsd", "flashback", "trigger", "memory"]
    if trauma_history or any(keyword in question.lower() for keyword in trauma_keywords):
        return f"""
        **Trauma-informed response:** {therapy_responses[therapy_mode].get('trauma', 'Trauma affects everyone differently. Safety and pacing are important in healing.')}
        
        *Therapeutic approach ({therapy_mode}):* {therapy_responses[therapy_mode].get('trauma', 'Would you like to explore this memory with a grounding exercise?')}
        
        *Remember: Trauma healing often benefits from professional support. 
        Consider reaching out to a trauma specialist.*
        """
    
    # Check for common topics in current therapy mode
    for topic, response in therapy_responses[therapy_mode].items():
        if topic in question.lower():
            return f"""
            **{therapy_mode} perspective on {topic}:** {response}
            
            *Remember: I'm an AI assistant, not a licensed therapist. 
            For professional help, consider reaching out to a mental health professional.*
            """
    
    # Default response with current therapy mode
    return f"""
    **{therapy_mode} perspective:** Thank you for sharing. That sounds important to explore. 
    From a {therapy_mode} perspective, we might examine {random.choice(['your thoughts about this', 'how you experience this emotionally', 'what values are involved', 'how your body responds'])}.
    
    Some approaches that might help:
    - Journaling about this experience
    - Practicing a grounding exercise
    - Exploring alternative perspectives
    
    Would you like me to suggest some {therapy_mode} techniques that might be relevant?
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

# Trauma Assessment Tools
def trauma_assessment():
    st.header("🕯️ Trauma Screening Tools")
    st.warning("""
    **Important:** These assessments screen for possible trauma symptoms but cannot diagnose PTSD. 
    Trauma affects everyone differently. Consider professional evaluation for concerning results.
    """)
    
    tab1, tab2 = st.tabs(["PCL-5 (PTSD Checklist)", "PTSD Symptom Scale"])
    
    with tab1:
        st.subheader("PCL-5: PTSD Checklist for DSM-5")
        st.write("""
        In the past month, how much were you bothered by:
        (1 = Not at all, 2 = A little bit, 3 = Moderately, 4 = Quite a bit, 5 = Extremely)
        """)
        
        pcl5_questions = [
            "Repeated, disturbing memories of the stressful experience?",
            "Repeated, disturbing dreams of the stressful experience?",
            "Suddenly feeling or acting as if the stressful experience were happening again?",
            "Feeling very upset when something reminded you of the stressful experience?",
            "Having strong physical reactions when something reminded you of the stressful experience?",
            "Avoiding memories, thoughts, or feelings related to the stressful experience?",
            "Avoiding external reminders of the stressful experience?",
            "Trouble remembering important parts of the stressful experience?",
            "Having strong negative beliefs about yourself, others, or the world?",
            "Blaming yourself or someone else for the stressful experience?",
            "Having strong negative feelings like fear, horror, anger, guilt, or shame?",
            "Loss of interest in activities you used to enjoy?",
            "Feeling distant or cut off from other people?",
            "Trouble experiencing positive feelings?",
            "Irritable behavior, angry outbursts, or acting aggressively?",
            "Taking too many risks or doing things that could cause you harm?",
            "Being 'superalert' or watchful or on guard?",
            "Feeling jumpy or easily startled?",
            "Having difficulty concentrating?",
            "Trouble falling or staying asleep?"
        ]
        
        scores = []
        for i, question in enumerate(pcl5_questions):
            score = st.select_slider(
                question,
                options=[1, 2, 3, 4, 5],
                key=f"pcl5_{i}"
            )
            scores.append(score)
        
        if st.button("Calculate PCL-5 Score"):
            total = sum(scores)
            st.write(f"**Your score:** {total}/80")
            
            if total >= 33:
                st.error("""
                **Score suggests significant PTSD symptoms.**
                Consider reaching out to a trauma specialist for evaluation.
                Resources:
                - VA PTSD Program (for veterans)
                - Psychology Today's trauma specialist finder
                - ISTSS.org therapist directory
                """)
            elif total >= 20:
                st.warning("""
                **Score suggests moderate PTSD symptoms.**
                Monitoring symptoms and considering professional support may be helpful.
                """)
            else:
                st.success("""
                **Score suggests minimal PTSD symptoms.**
                Continue healthy habits that support your wellbeing.
                """)
            
            # Store assessment results
            if 'user_id' in st.session_state:
                today = datetime.now().strftime("%Y-%m-%d")
                c.execute('INSERT INTO trauma_assessments (user_id, date, pcl5_score) VALUES (?,?,?)',
                          (st.session_state.user_id, today, total))
                conn.commit()
    
    with tab2:
        st.subheader("PTSD Symptom Scale (PSS-I)")
        st.write("""
        In the past 2 weeks, how often have you experienced:
        (0 = Not at all, 1 = Once per week, 2 = 2-4 times per week, 3 = 5+ times per week)
        """)
        
        ptsd_questions = [
            "Intrusive memories of the event",
            "Distressing dreams about the event",
            "Flashbacks or feeling like it's happening again",
            "Upset when reminded of the event",
            "Physical reactions when reminded (e.g., sweating, pounding heart)",
            "Avoiding thoughts or feelings about the event",
            "Avoiding activities or situations that remind you",
            "Trouble remembering important parts of the event",
            "Loss of interest in activities",
            "Feeling detached from others",
            "Difficulty experiencing positive emotions",
            "Irritability or anger outbursts",
            "Difficulty concentrating",
            "Trouble falling or staying asleep",
            "Being overly alert or watchful",
            "Easily startled"
        ]
        
        scores = []
        for i, question in enumerate(ptsd_questions):
            score = st.radio(
                question,
                options=[0, 1, 2, 3],
                horizontal=True,
                key=f"ptsd_{i}"
            )
            scores.append(score)
        
        if st.button("Calculate PSS Score"):
            total = sum(scores)
            st.write(f"**Your score:** {total}/48")
            
            if total >= 20:
                st.error("""
                **Score suggests significant PTSD symptoms.**
                Consider reaching out to a trauma specialist for evaluation.
                """)
            elif total >= 11:
                st.warning("""
                **Score suggests moderate PTSD symptoms.**
                Monitoring symptoms and considering professional support may be helpful.
                """)
            else:
                st.success("""
                **Score suggests minimal PTSD symptoms.**
                Continue healthy habits that support your wellbeing.
                """)
            
            # Store assessment results
            if 'user_id' in st.session_state:
                today = datetime.now().strftime("%Y-%m-%d")
                c.execute('INSERT INTO trauma_assessments (user_id, date, ptsdi_score) VALUES (?,?,?)',
                          (st.session_state.user_id, today, total))
                conn.commit()

# Enhanced AI Therapist Feature with Conversation Flow
def ai_therapist():
    st.header("💬 AI Therapist")
    
    # Therapy mode selection
    st.subheader("Therapy Approach")
    therapy_mode = st.radio(
        "Select therapeutic approach:",
        ("CBT", "ACT", "DBT", "IFS", "CPT", "Somatic"),
        horizontal=True,
        index=0
    )
    st.session_state.therapy_mode = therapy_mode
    
    st.warning("""
    **Important Disclaimer:** 
    This AI is not a substitute for professional therapy. It can provide general 
    mental health information but cannot diagnose or treat conditions. 
    For emergencies, please use the [crisis resources](#crisis-support).
    """)
    
    # Display conversation history
    if st.session_state.conversation_history:
        st.subheader("Conversation History")
        for i, (speaker, message) in enumerate(st.session_state.conversation_history):
            if speaker == "You":
                st.markdown(f"**You:** {message}")
            else:
                st.markdown(f"**TheraBot ({therapy_mode}):** {message}")
            if i < len(st.session_state.conversation_history) - 1:
                st.markdown("---")
    
    # User input
    question = st.text_area("What would you like to discuss?", height=150)
    
    if st.button("Send"):
        if not question.strip():
            st.warning("Please enter a message")
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            response = answer_ai_therapist_question(
                question, 
                st.session_state.get('user_id'),
                therapy_mode
            )
            
            # Add to conversation history
            st.session_state.conversation_history.append(("You", question))
            st.session_state.conversation_history.append(("TheraBot", response))
            
            # Store the question and response
            if 'user_id' in st.session_state:
                c.execute('''INSERT INTO ai_therapist_questions 
                            (user_id, date, question, response, therapy_mode) 
                            VALUES (?,?,?,?,?)''',
                          (st.session_state.user_id, today, question, response, therapy_mode))
                conn.commit()
            
            st.rerun()
    
    if st.button("Clear Conversation"):
        st.session_state.conversation_history = []
        st.rerun()
    
    st.markdown("---")
    st.write("""
    **Remember:**
    - This is not medical advice
    - AI doesn't replace human therapists
    - For emergencies, use crisis resources
    - Consider professional help for persistent concerns
    """)

# Enhanced Self-Care Guidance with Specialized Content
def self_care_guidance():
    st.header("🧘 Self-Care Strategies")
    
    user_type, trauma_history = get_user_type(st.session_state.user_id) if 'user_id' in st.session_state else ('general', 0)
    
    tab1, tab2, tab3 = st.tabs(["Quick Relief", "Daily Practices", "Professional Help"])
    
    with tab1:
        st.subheader("Immediate Coping Strategies")
        
        if user_type == 'veteran' or trauma_history:
            st.write("""
            **For trauma-related distress:**
            - 🌍 **Orienting Exercise**: 
              Name 5 things you see, 4 sounds you hear, 3 things you can touch
            - 🕰️ **Temporal Awareness**: 
              Remind yourself "That was then, this is now"
            - 🚶 **Grounding Walk**: 
              Focus on each step and your surroundings
            """)
        
        if user_type == 'first_responder':
            st.write("""
            **For first responder stress:**
            - 🚨 **Critical Incident Pause**: 
              After intense calls, take 3 minutes to breathe and transition
            - 🛡️ **Boundary Visualization**: 
              Imagine a protective shield between work and personal life
            - 🤝 **Buddy Check**: 
              Quick connection with a colleague after tough shifts
            """)
        
        st.write("""
        **For acute distress:**
        - 🌬️ **5-4-3-2-1 Grounding**: 
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
        
        **Box Breathing (used by Navy SEALs):**
        1. Inhale for 4 seconds
        2. Hold for 4 seconds
        3. Exhale for 4 seconds
        4. Hold for 4 seconds
        5. Repeat
        """)
    
    with tab2:
        st.subheader("Daily Mental Health Practices")
        
        if user_type == 'veteran':
            st.write("""
            **For Veterans:**
            - 🎖️ **Service Connection**: 
              Maintain bonds with fellow veterans
            - 🕊️ **Transition Rituals**: 
              Create routines that mark civilian life
            - 📅 **Structure**: 
              Maintain regular daily rhythms
            """)
        
        if user_type == 'first_responder':
            st.write("""
            **For First Responders:**
            - 🔄 **Shift Transition**: 
              Decompression routine after shifts
            - 👥 **Peer Support**: 
              Regular check-ins with colleagues
            - 🧠 **Mental Rehearsal**: 
              Visualize handling challenging calls successfully
            """)
        
        st.write("""
        **General Practices:**
        - ☀️ Morning sunlight exposure
        - 💧 Stay hydrated
        - 🚶‍♂️ Regular movement
        - 🛌 Consistent sleep schedule
        - 🎨 Creative expression
        - 👥 Meaningful social connection
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
        - Trauma symptoms interfering with life
        """)
        
        if user_type == 'veteran':
            st.write("""
            **Veteran-Specific Resources:**
            - VA Mental Health Services
            - Wounded Warrior Project
            - Give an Hour
            - Cohen Veterans Network
            """)
        
        if user_type == 'first_responder':
            st.write("""
            **First Responder Resources:**
            - Code Green Campaign
            - First Responder Support Network
            - Safe Call Now
            - CopLine
            """)

# Enhanced Welcome Page with User Type Selection
def welcome_page():
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
                
                user_type = st.radio(
                    "User Type (optional):",
                    ["General User", "Veteran/Service Member", "First Responder"],
                    index=0
                )
                
                trauma_history = st.checkbox(
                    "I have experienced significant trauma (optional)",
                    value=False
                )
                
                if st.form_submit_button("Create Account"):
                    if new_password == confirm_password:
                        try:
                            user_type_db = {
                                "General User": "general",
                                "Veteran/Service Member": "veteran",
                                "First Responder": "first_responder"
                            }[user_type]
                            
                            user_id = create_user(
                                new_username, 
                                new_password, 
                                new_email,
                                user_type_db,
                                1 if trauma_history else 0
                            )
                            st.session_state.user_id = user_id
                            st.session_state.username = new_username
                            st.success("Account created successfully!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Username already exists")
                    else:
                        st.error("Passwords don't match")
    else:
        user_type, trauma_history = get_user_type(st.session_state.user_id)
        
        welcome_title = f"Welcome back, {st.session_state.get('username', 'Guest')}!"
        if user_type == 'veteran':
            welcome_title += " 🎖️"
        elif user_type == 'first_responder':
            welcome_title += " 🚨"
            
        st.header(welcome_title)
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
# Enhanced Journal with AI memory
def journal_entry():
    st.header("📝 Reflective Journal")
    
    # Get user type for personalized responses
    user_type, trauma_history = get_user_type(st.session_state.user_id)
    
    # Journal prompt generator - now with personalized prompts
    base_prompts = [
        "What's been on your mind lately?",
        "What are you grateful for today?",
        "Describe a challenge you're facing and how you might approach it",
        "What's one thing you'd like to remember from today?",
        "Write a letter to your future self",
        "What emotions have you felt most strongly this week?"
    ]
    
    veteran_prompts = [
        "How has your service experience influenced your perspective today?",
        "What strengths from your service help you in civilian life?",
        "Describe a transition challenge and how you're adapting",
        "What does 'service' mean to you now?"
    ]
    
    first_responder_prompts = [
        "How do you decompress after difficult shifts?",
        "What lessons from emergency response apply to daily life?",
        "Describe a work experience that changed your perspective",
        "How do you maintain boundaries between work and personal life?"
    ]
    
    trauma_prompts = [
        "What helps you feel grounded when recalling difficult experiences?",
        "How have you grown from past challenges?",
        "What's one way you've learned to care for yourself when triggered?"
    ]
    
    # Combine prompts based on user type
    if user_type == 'veteran':
        prompts = veteran_prompts + trauma_prompts if trauma_history else veteran_prompts + base_prompts
    elif user_type == 'first_responder':
        prompts = first_responder_prompts + trauma_prompts if trauma_history else first_responder_prompts + base_prompts
    else:
        prompts = trauma_prompts + base_prompts if trauma_history else base_prompts
    
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
            
            # Enhanced AI response based on user type and content
            if user_type == 'veteran':
                base_response = "Thank you for your service. "
                if "service" in entry.lower() or "military" in entry.lower():
                    base_response += "Your military experience has shaped who you are today. "
            elif user_type == 'first_responder':
                base_response = "Your work makes a profound difference. "
                if "shift" in entry.lower() or "call" in entry.lower():
                    base_response += "The challenges of first response work are unique. "
            else:
                base_response = ""
            
            if sentiment > 0.2:
                ai_response = base_response + "I notice positive tones in your writing. Celebrate these moments!"
            elif sentiment < -0.2:
                if trauma_history or any(word in entry.lower() for word in ['trauma', 'ptsd', 'trigger']):
                    ai_response = base_response + "Your words reflect difficult experiences. The VA and other organizations offer specialized support for trauma healing."
                else:
                    ai_response = base_response + "Your words reflect some difficulty. Remember, writing about challenges is already a step toward processing them."
            else:
                ai_response = base_response + "Thank you for sharing these reflections. Regular journaling builds self-awareness."
            
            st.success(f"**TheraBot:** {ai_response}\n\nJournal saved!")
            
            # Connect to previous entries if available
            c.execute('SELECT entry FROM journal_entries WHERE user_id = ? AND date != ? ORDER BY date DESC LIMIT 1',
                      (st.session_state.user_id, today))
            prev_entry = c.fetchone()
            
            if prev_entry:
                common_words = set(entry.lower().split()) & set(prev_entry[0].lower().split())
                if common_words:
                    st.info(f"**Connection to previous entry:** You mentioned similar themes about {', '.join(common_words)}.")

# ... (rest of the code remains the same)

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
    
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

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

def crisis_support():
    st.header("🆘 Crisis Support")
    st.warning("""
    If you or someone you know is in immediate danger, please call 911.

    **Crisis Resources:**
    - 🇺🇸 Veterans Crisis Line: 988 then press 1
    - 💙 Crisis Text Line: Text HOME to 741741
    - 🌍 International: [befrienders.org](https://www.befrienders.org)
    """)
