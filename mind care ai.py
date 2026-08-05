"""
MindCare AI - Personal Mental Wellness Companion
================================================
A production-quality, privacy-focused Streamlit application providing emotional support,
mood tracking, healthy habit building, journaling, stress assessment, and coping strategies.

DISCLAIMER: This application is not a substitute for professional mental health care or clinical diagnosis.
"""

import os
import re
import json
import time
import hashlib
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional, Any

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# SQLAlchemy Core & ORM
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, Date, DateTime, Text, ForeignKey, desc
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

# Optional AI API Imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ==============================================================================
# CONFIGURATION & GLOBAL CONSTANTS
# ==============================================================================

DB_FILENAME = "mindcare_wellness.db"
DATABASE_URL = f"sqlite:///{DB_FILENAME}"

APP_TITLE = "MindCare AI"
APP_TAGLINE = "Your Personal Mental Wellness Companion"

# ==============================================================================
# DATABASE SCHEMAS & INITIALIZATION
# ==============================================================================

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Profile Info
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    occupation = Column(String(100), nullable=True)
    goals = Column(Text, nullable=True)
    timezone = Column(String(50), default="UTC")
    
    # Relationships
    mood_entries = relationship("MoodEntry", back_populates="user", cascade="all, delete-orphan")
    journals = relationship("JournalEntry", back_populates="user", cascade="all, delete-orphan")
    habits = relationship("HabitLog", back_populates="user", cascade="all, delete-orphan")
    sleep_logs = relationship("SleepLog", back_populates="user", cascade="all, delete-orphan")
    meditations = relationship("MeditationLog", back_populates="user", cascade="all, delete-orphan")
    chat_logs = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")

class MoodEntry(Base):
    __tablename__ = "mood_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    mood_score = Column(Integer, nullable=False)  # 1 - 10
    stress_level = Column(Integer, nullable=False) # 1 - 10
    energy_level = Column(Integer, nullable=False) # 1 - 10
    anxiety_level = Column(Integer, nullable=False) # 1 - 10
    sleep_quality = Column(Integer, nullable=False) # 1 - 10
    notes = Column(Text, nullable=True)
    detected_emotion = Column(String(30), nullable=True)
    
    user = relationship("User", back_populates="mood_entries")

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    entry_type = Column(String(20), default="daily") # "daily" or "gratitude"
    gratitude_items = Column(Text, nullable=True) # JSON stored string
    tags = Column(String(100), nullable=True)
    
    user = relationship("User", back_populates="journals")

class HabitLog(Base):
    __tablename__ = "habit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    habit_name = Column(String(50), nullable=False)
    completed = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="habits")

class SleepLog(Base):
    __tablename__ = "sleep_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    hours = Column(Float, nullable=False)
    quality = Column(Integer, nullable=False) # 1-10
    notes = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="sleep_logs")

class MeditationLog(Base):
    __tablename__ = "meditation_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    session_type = Column(String(50), nullable=False) # Breathing / Meditation
    duration_mins = Column(Integer, nullable=False)
    
    user = relationship("User", back_populates="meditations")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender = Column(String(10), nullable=False) # "user" or "assistant"
    message = Column(Text, nullable=False)
    emotion = Column(String(30), nullable=True)
    
    user = relationship("User", back_populates="chat_logs")

class StressAssessment(Base):
    __tablename__ = "stress_assessments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    score = Column(Integer, nullable=False)
    summary = Column(Text, nullable=False)

# Engine & Session Setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass # Session managed per query or closed manually

# ==============================================================================
# AUTHENTICATION & SECURITY UTILITIES
# ==============================================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def register_user(username: str, password: str, age: int = None, occupation: str = "") -> Tuple[bool, str]:
    db = get_db()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            return False, "Username already exists. Please choose another."
        
        user = User(
            username=username,
            password_hash=hash_password(password),
            age=age,
            occupation=occupation
        )
        db.add(user)
        db.commit()
        return True, "Registration successful! You can now log in."
    except Exception as e:
        db.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        db.close()

def authenticate_user(username: str, password: str) -> Optional[User]:
    db = get_db()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and verify_password(password, user.password_hash):
            return user
        return None
    finally:
        db.close()

# ==============================================================================
# NLP & EMOTION ANALYSIS ENGINE
# ==============================================================================

EMOTION_KEYWORDS = {
    "Anxiety": ["anxious", "worried", "panic", "nervous", "scared", "fear", "overwhelmed", "uneasy", "restless", "tense"],
    "Sadness": ["sad", "depressed", "unhappy", "crying", "miserable", "heartbroken", "down", "gloomy", "hopeless"],
    "Burnout": ["exhausted", "burnt out", "tired", "drained", "overworked", "fatigue", "can't focus", "empty"],
    "Anger": ["angry", "frustrated", "annoyed", "furious", "irritated", "rage", "mad", "upset"],
    "Loneliness": ["lonely", "isolated", "alone", "nobody", "disconnected", "abandoned", "miss everyone"],
    "Happiness": ["happy", "joy", "excited", "great", "wonderful", "blessed", "cheerful", "content", "delighted"],
    "Calm": ["calm", "relaxed", "peaceful", "tranquil", "serene", "grounded", "mindful", "at ease"],
    "Stress": ["stressed", "pressure", "deadline", "workload", "exam", "rushed", "hectic", "strained"]
}

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die", "self harm", 
    "cut myself", "overdose", "hurt myself", "don't want to live"
]

def detect_crisis(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in CRISIS_KEYWORDS)

def analyze_emotion(text: str) -> Tuple[str, float]:
    """Rule-based lightweight emotion classifier for local deterministic processing."""
    if not text:
        return "Calm", 0.5
    
    lowered = text.lower()
    scores = {emotion: 0 for emotion in EMOTION_KEYWORDS}
    
    words = re.findall(r'\w+', lowered)
    total_matches = 0
    
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for word in words:
            if word in keywords:
                scores[emotion] += 1
                total_matches += 1
                
    if total_matches == 0:
        return "Calm", 0.6
        
    top_emotion = max(scores, key=scores.get)
    confidence = min(0.95, 0.5 + (scores[top_emotion] / max(1, len(words))) * 2.0)
    return top_emotion, round(confidence, 2)

# ==============================================================================
# AI CHATBOT ENGINE
# ==============================================================================

SYSTEM_PROMPT = """You are MindCare AI, an empathetic, supportive, and compassionate mental wellness companion.
Your goals:
1. Provide active listening, validation, and emotional encouragement.
2. Ask gently reflective questions to help the user express their thoughts.
3. Suggest healthy evidence-informed coping techniques (e.g., deep breathing, grounding, rest, journaling).
4. Strictly maintain boundaries: DO NOT provide clinical diagnoses, medical advice, or therapeutic treatment.
5. If the user experiences severe distress or mentions self-harm, prioritize safety and encourage seeking immediate professional or emergency support.
Keep responses concise, warm, structured, and soothing."""

def generate_ai_response(user_message: str, chat_history: List[Dict[str, str]], api_key: str = "", provider: str = "Fallback") -> str:
    """Generates empathetic response via Gemini/OpenAI API or local rule engine."""
    
    # 1. Safety Check
    if detect_crisis(user_message):
        return ("I hear how much pain you're in right now, and I want you to be safe. "
                "Please know you don't have to carry this alone. "
                "I strongly encourage you to connect with someone who can support you right now:\n\n"
                "• **National Crisis Lifeline**: Call or text **988** (US/Canada)\n"
                "• **Tele-MANAS**: Call **14416** or **1800-891-4416** (India)\n"
                "• **Emergency Services**: Call your local emergency services (112, 911, or 999)\n"
                "• **Global Resources**: Visit [findahelpline.com](https://findahelpline.com/)\n\n"
                "Please reach out to a professional, a loved one, or a trusted person. Your safety and well-being matter.")

    # 2. Gemini Integration
    if provider == "Gemini" and GEMINI_AVAILABLE and api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_message}\nMindCare AI:"
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"*(Gemini API fallback error: {str(e)})*\n\n" + fallback_response(user_message)

    # 3. OpenAI Integration
    elif provider == "OpenAI" and OPENAI_AVAILABLE and api_key:
        try:
            client = openai.OpenAI(api_key=api_key)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for msg in chat_history[-6:]:
                messages.append({"role": msg["sender"], "content": msg["message"]})
            messages.append({"role": "user", "content": user_message})
            
            res = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=300
            )
            return res.choices[0].message.content
        except Exception as e:
            return f"*(OpenAI API fallback error: {str(e)})*\n\n" + fallback_response(user_message)

    # 4. Built-in Generative Rules Fallback Engine
    return fallback_response(user_message)

def fallback_response(message: str) -> str:
    """Intelligent offline fallback engine ensuring full functionality without external API keys."""
    emotion, _ = analyze_emotion(message)
    
    responses = {
        "Anxiety": "It sounds like you're feeling quite overwhelmed and tense right now. Try taking a slow, deep breath in through your nose, holding for 4 seconds, and releasing gently. What is creating the most pressure for you at this exact moment?",
        "Sadness": "I'm really sorry you're feeling down. It is completely okay to feel this way, and taking time to sit with your feelings is valid. Would you like to write about what's on your mind or try a calming grounding exercise?",
        "Burnout": "Feeling exhausted and drained is a clear signal from your mind and body that you need restorative care. Remember that resting is productive. Can you give yourself permission to take a 10-minute break right now?",
        "Anger": "It is completely valid to feel frustrated or angry when things feel unfair or overwhelming. Taking a brief physical pause or stepping away for a short walk can help reset your nervous system. What triggered this feeling today?",
        "Loneliness": "Feeling isolated can feel really heavy. Even when you're alone, please remember that your thoughts and feelings matter deeply. Would listening to a soothing guided breathing routine feel helpful right now?",
        "Happiness": "It makes me so glad to hear that you're feeling good today! Celebrating positive moments builds emotional resilience. What is something specific that brought a smile to your face?",
        "Calm": "It's wonderful that you're experiencing a sense of calm and peace. Grounding yourself in these calm moments helps build long-term emotional balance. How can we nourish this feeling today?",
        "Stress": "Dealing with heavy stress takes a real toll. Let's break things down into smaller, manageable pieces. What is one small thing you can pause or delegate right now to give yourself space?"
    }
    
    return responses.get(emotion, "Thank you for sharing that with me. I'm here to listen and support you without judgment. How are you taking care of yourself today?")

# ==============================================================================
# STYLES & UI THEMING (GLASSMORPHISM & ACCENTS)
# ==============================================================================

def inject_custom_css():
    st.markdown("""
        <style>
            /* Global Font & Theme Adjustments */
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
            
            html, body, [class*="css"] {
                font-family: 'Plus Jakarta Sans', sans-serif;
            }
            
            /* Glassmorphism Cards */
            .mindcare-card {
                background: rgba(255, 255, 255, 0.75);
                backdrop-filter: blur(12px);
                border-radius: 16px;
                padding: 20px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
                margin-bottom: 20px;
            }
            
            .metric-card {
                background: linear-gradient(135deg, #eef2f3 0%, #8e9eab 100%);
                border-radius: 14px;
                padding: 16px;
                color: #2c3e50;
                text-align: center;
                box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            }
            
            .crisis-banner {
                background: #FFF0F0;
                border-left: 5px solid #E53E3E;
                padding: 15px 20px;
                border-radius: 8px;
                color: #9B2C2C;
                font-weight: 500;
                margin-bottom: 20px;
            }
            
            /* Modern Streamlit Elements */
            .stButton>button {
                border-radius: 10px;
                font-weight: 600;
                border: none;
                transition: all 0.3s ease;
            }
            
            .stButton>button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
            
            /* Animated Breathing Circle */
            .breathing-circle {
                width: 150px;
                height: 150px;
                background: radial-gradient(circle, rgba(163,231,216,1) 0%, rgba(46,134,171,1) 100%);
                border-radius: 50%;
                margin: 30px auto;
                animation: pulse 8s infinite ease-in-out;
                box-shadow: 0 0 25px rgba(46,134,171,0.4);
            }
            
            @keyframes pulse {
                0% { transform: scale(0.8); opacity: 0.7; }
                50% { transform: scale(1.25); opacity: 1; }
                100% { transform: scale(0.8); opacity: 0.7; }
            }
        </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# UI RENDER PAGES
# ==============================================================================

def render_auth_page():
    st.markdown("<h1 style='text-align: center; color: #2E86AB;'>🌿 MindCare AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>Your Personal Mental Wellness Companion</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔒 Login", "📝 Register"])
        
        with tab1:
            st.subheader("Welcome Back")
            login_user = st.text_input("Username", key="login_user")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Log In", use_container_width=True, type="primary"):
                user = authenticate_user(login_user, login_pass)
                if user:
                    st.session_state["user_id"] = user.id
                    st.session_state["username"] = user.username
                    st.session_state["logged_in"] = True
                    st.success(f"Welcome back, {user.username}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
                    
        with tab2:
            st.subheader("Create an Account")
            reg_user = st.text_input("Choose Username", key="reg_user")
            reg_pass = st.text_input("Choose Password", type="password", key="reg_pass")
            reg_age = st.number_input("Age (Optional)", min_value=10, max_value=120, value=22)
            reg_occ = st.selectbox("Occupation", ["Student", "Working Professional", "Remote Employee", "Parent", "Other"])
            
            if st.button("Sign Up", use_container_width=True):
                if reg_user and reg_pass:
                    success, msg = register_user(reg_user, reg_pass, reg_age, reg_occ)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("Please fill in both username and password.")

def render_dashboard(user_id: int):
    st.title("🏠 Wellness Dashboard")
    st.caption(f"Hello, **{st.session_state.get('username', 'Friend')}**! Here is your daily mental health overview.")
    
    db = get_db()
    today = date.today()
    
    # Fetch recent data
    today_mood = db.query(MoodEntry).filter(MoodEntry.user_id == user_id, MoodEntry.date == today).first()
    recent_moods = db.query(MoodEntry).filter(MoodEntry.user_id == user_id).order_by(desc(MoodEntry.date)).limit(7).all()
    today_sleep = db.query(SleepLog).filter(SleepLog.user_id == user_id, SleepLog.date == today).first()
    today_habits = db.query(HabitLog).filter(HabitLog.user_id == user_id, HabitLog.date == today).all()
    
    # Quick Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        mood_val = f"{today_mood.mood_score}/10" if today_mood else "Not Logged"
        st.metric("Today's Mood", mood_val, delta=today_mood.detected_emotion if today_mood else None)
    with m2:
        stress_val = f"{today_mood.stress_level}/10" if today_mood else "N/A"
        st.metric("Stress Index", stress_val)
    with m3:
        sleep_val = f"{today_sleep.hours} hrs" if today_sleep else "Not Logged"
        st.metric("Sleep Duration", sleep_val)
    with m4:
        completed_h = sum(1 for h in today_habits if h.completed) if today_habits else 0
        total_h = len(today_habits) if today_habits else 6
        st.metric("Habits Completed", f"{completed_h}/{total_h}")
        
    st.markdown("---")
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📈 7-Day Mood & Stress Trend")
        if recent_moods:
            df = pd.DataFrame([{
                "Date": m.date.strftime("%b %d"),
                "Mood Score": m.mood_score,
                "Stress Level": m.stress_level,
                "Energy Level": m.energy_level
            } for m in reversed(recent_moods)])
            
            fig = px.line(df, x="Date", y=["Mood Score", "Stress Level", "Energy Level"],
                          markers=True, color_discrete_sequence=["#2E86AB", "#E53E3E", "#A3E7D8"])
            fig.update_layout(yaxis=dict(range=[1, 10]), height=300, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No mood entries logged yet. Head to the **Mood Tracker** to log your first entry!")
            
    with col_right:
        st.subheader("💡 Daily Inspiration")
        st.markdown("""
        <div class="mindcare-card">
            <p style="font-style: italic; font-size: 1.1em; color: #2B4C7E;">
            "You don't have to control your thoughts. You just have to stop letting them control you."
            </p>
            <p style="text-align: right; font-weight: 600; color: #555;">— Dan Millman</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("🎯 Quick Actions")
        if st.button("🧘 5-Min Breathing Pause", use_container_width=True):
            st.session_state["current_page"] = "🧘 Breathing & Meditation"
            st.rerun()
        if st.button("💬 Talk to MindCare AI", use_container_width=True):
            st.session_state["current_page"] = "💬 AI Chat Companion"
            st.rerun()

    db.close()

def render_chat_page(user_id: int):
    st.title("💬 AI Chat Companion")
    st.caption("A safe, non-judgmental space to reflect, decompress, and explore emotional wellness.")
    
    # Crisis Banner Alert
    st.markdown("""
    <div class="crisis-banner">
        ⚠️ <b>Immediate Support:</b> If you are in severe distress or thinking of self-harm, please reach out directly to emergency services or call <b>988</b> (US/Canada) or <b>14416</b> (India).
    </div>
    """, unsafe_allow_html=True)
    
    # API Provider Settings in Sidebar Sub-expander
    with st.sidebar.expander("🤖 AI Provider Settings"):
        provider = st.selectbox("Provider", ["Fallback Engine (Offline)", "Gemini", "OpenAI"])
        api_key = st.text_input("API Key", type="password", help="Enter key to enable cloud LLM models.")
    
    db = get_db()
    
    # Load past session chat history from DB
    if "messages" not in st.session_state:
        history = db.query(ChatHistory).filter(ChatHistory.user_id == user_id).order_by(ChatHistory.timestamp.asc()).limit(20).all()
        st.session_state.messages = [{"sender": h.sender, "message": h.message} for h in history]
        if not st.session_state.messages:
            st.session_state.messages = [{
                "sender": "assistant",
                "message": "Hello! I'm your MindCare companion. How are you feeling today? I'm here to listen."
            }]

    # Render Chat Bubble UI
    for msg in st.session_state.messages:
        avatar = "🌿" if msg["sender"] == "assistant" else "👤"
        with st.chat_message(msg["sender"], avatar=avatar):
            st.write(msg["message"])

    # User Input Field
    if prompt := st.chat_input("Share what's on your mind..."):
        # Display user message
        st.session_state.messages.append({"sender": "user", "message": prompt})
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
            
        # Detect emotion
        detected_emotion, conf = analyze_emotion(prompt)
        
        # Save user message to DB
        user_msg_db = ChatHistory(user_id=user_id, sender="user", message=prompt, emotion=detected_emotion)
        db.add(user_msg_db)
        db.commit()

        # Generate response
        with st.chat_message("assistant", avatar="🌿"):
            with st.spinner("MindCare is typing..."):
                response_text = generate_ai_response(
                    user_message=prompt,
                    chat_history=st.session_state.messages,
                    api_key=api_key if provider != "Fallback Engine (Offline)" else "",
                    provider="Gemini" if provider == "Gemini" else ("OpenAI" if provider == "OpenAI" else "Fallback")
                )
                st.write(response_text)

        # Save assistant response to DB & session
        st.session_state.messages.append({"sender": "assistant", "message": response_text})
        assistant_msg_db = ChatHistory(user_id=user_id, sender="assistant", message=response_text)
        db.add(assistant_msg_db)
        db.commit()

    db.close()

def render_mood_tracker_page(user_id: int):
    st.title("📊 Mood & Emotion Tracker")
    st.caption("Log your daily emotional metrics to uncover trends and emotional patterns.")
    
    db = get_db()
    today = date.today()
    
    col_form, col_vis = st.columns([1, 1])
    
    with col_form:
        st.subheader("Log Today's Wellness")
        with st.form("mood_form"):
            mood_score = st.slider("Overall Mood (1 = Very Low, 10 = Joyful)", 1, 10, 6)
            stress_level = st.slider("Stress Level (1 = Calm, 10 = Overwhelmed)", 1, 10, 4)
            energy_level = st.slider("Energy Level (1 = Exhausted, 10 = Energized)", 1, 10, 5)
            anxiety_level = st.slider("Anxiety Level (1 = None, 10 = Severe)", 1, 10, 3)
            sleep_quality = st.slider("Sleep Quality (1 = Poor, 10 = Restful)", 1, 10, 7)
            notes = st.text_area("Daily Notes / Reflection", placeholder="What influenced your mood today?")
            
            submit_btn = st.form_submit_button("Save Log", type="primary", use_container_width=True)
            
            if submit_btn:
                detected_emo, _ = analyze_emotion(notes) if notes else ("Calm", 0.5)
                
                # Check existing entry for today
                existing = db.query(MoodEntry).filter(MoodEntry.user_id == user_id, MoodEntry.date == today).first()
                if existing:
                    existing.mood_score = mood_score
                    existing.stress_level = stress_level
                    existing.energy_level = energy_level
                    existing.anxiety_level = anxiety_level
                    existing.sleep_quality = sleep_quality
                    existing.notes = notes
                    existing.detected_emotion = detected_emo
                else:
                    entry = MoodEntry(
                        user_id=user_id,
                        date=today,
                        mood_score=mood_score,
                        stress_level=stress_level,
                        energy_level=energy_level,
                        anxiety_level=anxiety_level,
                        sleep_quality=sleep_quality,
                        notes=notes,
                        detected_emotion=detected_emo
                    )
                    db.add(entry)
                
                db.commit()
                st.success("Mood entry saved successfully!")
                
    with col_vis:
        st.subheader("Emotion Distribution")
        entries = db.query(MoodEntry).filter(MoodEntry.user_id == user_id).all()
        if entries:
            emotions = [e.detected_emotion for e in entries if e.detected_emotion]
            if emotions:
                emo_df = pd.DataFrame(emotions, columns=["Emotion"]).value_counts().reset_index()
                emo_df.columns = ["Emotion", "Count"]
                fig_pie = px.pie(emo_df, names="Emotion", values="Count", hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=20))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Log notes to view emotion analysis distribution.")
        else:
            st.info("No historical entries found.")

    db.close()

def render_breathing_meditation_page(user_id: int):
    st.title("🧘 Breathing & Guided Mindfulness")
    st.caption("Reset your autonomic nervous system with evidence-based breathing techniques.")
    
    tab1, tab2 = st.tabs(["🫁 Interactive Breathing", "🎧 Guided Meditation Timer"])
    
    with tab1:
        st.subheader("Box Breathing (4-4-4-4)")
        st.markdown("Inhale for 4s, Hold for 4s, Exhale for 4s, Pause for 4s.")
        
        # CSS Animated Breathing Visualizer
        st.markdown('<div class="breathing-circle"></div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Start 1-Minute Breathing Cycle", use_container_width=True, type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for cycle in range(3): # 3 cycles ~ 48 seconds
                    status_text.markdown("### 🫁 **Inhale slowly...** (4s)")
                    for i in range(40):
                        time.sleep(0.1)
                    
                    status_text.markdown("### 🛑 **Hold breath...** (4s)")
                    for i in range(40):
                        time.sleep(0.1)
                        
                    status_text.markdown("### 💨 **Exhale gently...** (4s)")
                    for i in range(40):
                        time.sleep(0.1)
                        
                    status_text.markdown("### 🌿 **Pause...** (4s)")
                    for i in range(40):
                        time.sleep(0.1)
                        
                    progress_bar.progress((cycle + 1) / 3)
                    
                status_text.markdown("### ✨ **Session Complete! Take a moment to notice how you feel.**")
                
                # Log to DB
                db = get_db()
                med_log = MeditationLog(user_id=user_id, session_type="Box Breathing", duration_mins=1)
                db.add(med_log)
                db.commit()
                db.close()

    with tab2:
        st.subheader("Mindfulness Session Timer")
        duration = st.select_slider("Select Duration (Minutes)", options=[2, 5, 10, 15], value=5)
        st.info(f"Target Session: **{duration} Minutes** focused on gentle breath awareness.")
        
        if st.button("Begin Guided Session", type="primary"):
            st.success(f"Started {duration}-minute session. Focus gently on the rhythmic sound of your breathing.")
            # Log meditation
            db = get_db()
            med_log = MeditationLog(user_id=user_id, session_type="Guided Mindfulness", duration_mins=duration)
            db.add(med_log)
            db.commit()
            db.close()

def render_journal_page(user_id: int):
    st.title("📖 Journal & Gratitude")
    st.caption("Expressive writing relieves cognitive strain and improves emotional processing.")
    
    tab1, tab2 = st.tabs(["📝 Daily Reflections", "✨ Gratitude Log"])
    db = get_db()
    
    with tab1:
        st.subheader("Write a Journal Entry")
        j_title = st.text_input("Entry Title", placeholder="e.g., Reflections after exams...")
        j_content = st.text_area("Your Thoughts", height=180, placeholder="Write freely without editing yourself...")
        j_tags = st.text_input("Tags (comma separated)", placeholder="stress, study, personal")
        
        if st.button("Save Entry", type="primary"):
            if j_content and j_title:
                entry = JournalEntry(
                    user_id=user_id,
                    title=j_title,
                    content=j_content,
                    entry_type="daily",
                    tags=j_tags
                )
                db.add(entry)
                db.commit()
                st.success("Journal entry saved successfully!")
            else:
                st.warning("Please enter a title and content.")

        st.markdown("---")
        st.subheader("Past Entries")
        past_journals = db.query(JournalEntry).filter(JournalEntry.user_id == user_id, JournalEntry.entry_type == "daily").order_by(desc(JournalEntry.timestamp)).all()
        for j in past_journals:
            with st.expander(f"📅 {j.timestamp.strftime('%Y-%m-%d %H:%M')} - {j.title}"):
                st.write(j.content)
                if j.tags:
                    st.caption(f"🏷️ Tags: {j.tags}")

    with tab2:
        st.subheader("Three Good Things (Gratitude)")
        g1 = st.text_input("1. Something that brought you comfort or joy today:")
        g2 = st.text_input("2. A person or interaction you appreciated:")
        g3 = st.text_input("3. An achievement or moment of growth, no matter how small:")
        
        if st.button("Save Gratitude Log", type="primary"):
            if g1 or g2 or g3:
                gratitude_json = json.dumps([g1, g2, g3])
                entry = JournalEntry(
                    user_id=user_id,
                    title="Gratitude Reflection",
                    content="Recorded 3 good things today.",
                    entry_type="gratitude",
                    gratitude_items=gratitude_json
                )
                db.add(entry)
                db.commit()
                st.success("Gratitude log recorded! Cultivating gratitude builds resilience.")
            else:
                st.warning("Please fill in at least one item.")

    db.close()

def render_habit_tracker_page(user_id: int):
    st.title("📅 Habit Tracker")
    st.caption("Consistent small steps build powerful psychological momentum.")
    
    db = get_db()
    today = date.today()
    
    DEFAULT_HABITS = ["💧 Drink 2L Water", "🏃 20 Min Exercise / Walk", "🧘 5 Min Mindfulness", 
                      "📖 Read 10 Pages", "😴 Sleep Before 11 PM", "🥗 Healthy Meal"]
    
    # Initialize habits for today if not existing
    existing = db.query(HabitLog).filter(HabitLog.user_id == user_id, HabitLog.date == today).all()
    existing_names = [h.habit_name for h in existing]
    
    for h_name in DEFAULT_HABITS:
        if h_name not in existing_names:
            h_obj = HabitLog(user_id=user_id, date=today, habit_name=h_name, completed=False)
            db.add(h_obj)
    db.commit()
    
    # Re-fetch updated habits
    today_habits = db.query(HabitLog).filter(HabitLog.user_id == user_id, HabitLog.date == today).all()
    
    st.subheader(f"Today's Habit Checklist ({today.strftime('%A, %b %d')})")
    
    for habit in today_habits:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{habit.habit_name}**")
        with col2:
            is_done = st.checkbox("Done", value=habit.completed, key=f"habit_{habit.id}")
            if is_done != habit.completed:
                habit.completed = is_done
                db.commit()
                st.rerun()

    # Progress bar calculation
    completed_count = sum(1 for h in today_habits if h.completed)
    pct = completed_count / len(today_habits) if today_habits else 0
    st.progress(pct)
    st.caption(f"Progress: **{int(pct * 100)}%** completed today.")
    
    db.close()

def render_sleep_tracker_page(user_id: int):
    st.title("🌙 Sleep Tracker")
    st.caption("Quality sleep is the foundation of emotional regulation and mental sharpness.")
    
    db = get_db()
    today = date.today()
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Log Sleep Session")
        hours = st.number_input("Hours Slept", min_value=0.0, max_value=16.0, value=7.5, step=0.5)
        quality = st.slider("Sleep Quality (1 = Restless, 10 = Fully Rested)", 1, 10, 7)
        notes = st.text_input("Notes (e.g., Woke up twice, room cold)")
        
        if st.button("Log Sleep Record", type="primary"):
            existing = db.query(SleepLog).filter(SleepLog.user_id == user_id, SleepLog.date == today).first()
            if existing:
                existing.hours = hours
                existing.quality = quality
                existing.notes = notes
            else:
                s_log = SleepLog(user_id=user_id, date=today, hours=hours, quality=quality, notes=notes)
                db.add(s_log)
            db.commit()
            st.success("Sleep log recorded successfully!")
            
    with col2:
        st.subheader("Recent Sleep Trends")
        sleep_records = db.query(SleepLog).filter(SleepLog.user_id == user_id).order_by(desc(SleepLog.date)).limit(14).all()
        if sleep_records:
            s_df = pd.DataFrame([{
                "Date": s.date.strftime("%b %d"),
                "Hours": s.hours,
                "Quality": s.quality
            } for s in reversed(sleep_records)])
            
            fig = px.bar(s_df, x="Date", y="Hours", color="Quality", color_continuous_scale="Viridis")
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sleep logs recorded yet.")

    db.close()

def render_stress_assessment_page(user_id: int):
    st.title("📝 Stress Self-Assessment")
    st.caption("A brief wellness reflection tool based on perceived stress indicators.")
    
    st.warning("📌 **Note:** This assessment is for self-reflection purposes only and is NOT a medical or clinical diagnostic tool.")
    
    questions = [
        "How often have you felt overwhelmed by unexpected events recently?",
        "How often have you felt unable to control important things in your life?",
        "How often have you felt nervous, anxious, or stressed out?",
        "How often have you felt confident about your ability to handle personal problems?",
        "How often have you felt that difficulties were piling up too high to overcome?"
    ]
    
    scores = []
    with st.form("stress_form"):
        for idx, q in enumerate(questions):
            st.markdown(f"**Q{idx+1}: {q}**")
            # For Q4, inverted scoring mathematically handled
            val = st.radio("Select option", ["Never (0)", "Almost Never (1)", "Sometimes (2)", "Fairly Often (3)", "Very Often (4)"], key=f"q_{idx}")
            score_val = int(val.split("(")[1][0])
            scores.append(score_val)
        
        if st.form_submit_button("Submit Assessment", type="primary"):
            # Invert Q4 (index 3)
            scores[3] = 4 - scores[3]
            total_score = sum(scores) # 0 - 20 range
            
            if total_score <= 6:
                category = "Low Stress"
                summary = "You appear to be managing current demands well. Continue maintaining healthy recovery routines."
            elif total_score <= 13:
                category = "Moderate Stress"
                summary = "You are experiencing moderate stress. Consider incorporating daily micro-breaks and breathing exercises."
            else:
                category = "High Stress"
                summary = "Your responses indicate elevated stress levels. Prioritize rest, delegate tasks, and consider speaking with a professional."
                
            db = get_db()
            rec = StressAssessment(user_id=user_id, score=total_score, summary=f"{category}: {summary}")
            db.add(rec)
            db.commit()
            db.close()
            
            st.subheader(f"Assessment Result: **{category}** ({total_score}/20)")
            st.info(summary)

def render_resource_center_page():
    st.title("📚 Resource & Crisis Support Center")
    st.caption("Educational materials and immediate crisis assistance contact details.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🚨 Crisis Helplines")
        st.markdown("""
        If you or someone you know is in immediate danger or severe distress:
        
        * **United States & Canada**:
          * Call or Text **988** (National Suicide & Crisis Lifeline)
          * Text **HOME** to **741741** (Crisis Text Line)
          
        * **India**:
          * Call **14416** or **1800-891-4416** (Tele-MANAS)
          * Call **9152987821** (KIRAN Mental Health Helpline)
          
        * **United Kingdom**:
          * Call **111** (NHS Mental Health)
          * Call **116 123** (Samaritans)
          
        * **Global Support**:
          * Find resources worldwide at [findahelpline.com](https://findahelpline.com/)
        """)
        
    with col2:
        st.subheader("📖 Self-Care Toolkits")
        st.markdown("""
        **Grounding Strategy (5-4-3-2-1 Technique)**
        When experiencing acute anxiety or racing thoughts, look around you and identify:
        * 👁️ **5 things** you can see
        * ✋ **4 things** you can physically touch
        * 👂 **3 things** you can hear
        * 👃 **2 things** you can smell
        * 👅 **1 thing** you can taste
        
        **Sleep Hygiene Best Practices**
        1. Keep a fixed sleep-wake schedule, even on weekends.
        2. Keep the bedroom cool, dark, and quiet.
        3. Avoid bright screens 60 minutes prior to bed.
        """)

def render_settings_page(user_id: int):
    st.title("⚙️ Account Settings & Privacy")
    
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    
    st.subheader("Edit Profile Information")
    age = st.number_input("Age", min_value=10, max_value=120, value=user.age or 22)
    occ = st.text_input("Occupation", value=user.occupation or "")
    goals = st.text_area("Personal Wellness Goals", value=user.goals or "")
    
    if st.button("Update Profile", type="primary"):
        user.age = age
        user.occupation = occ
        user.goals = goals
        db.commit()
        st.success("Profile updated successfully!")
        
    st.markdown("---")
    st.subheader("🔒 Data & Privacy")
    
    if st.button("Export My Wellness Data (JSON)"):
        user_data = {
            "username": user.username,
            "created_at": str(user.created_at),
            "age": user.age,
            "occupation": user.occupation
        }
        st.download_button("Download JSON", data=json.dumps(user_data, indent=2), file_name="mindcare_export.json", mime="application/json")
        
    db.close()

# ==============================================================================
# MAIN APPLICATION CONTROLLER
# ==============================================================================

def main():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize DB tables on startup
    init_db()
    
    # Inject Custom CSS
    inject_custom_css()
    
    # Session state initialization
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "🏠 Dashboard"

    # Route based on auth state
    if not st.session_state["logged_in"]:
        render_auth_page()
    else:
        # Sidebar Navigation
        st.sidebar.markdown(f"### 🌿 MindCare AI")
        st.sidebar.caption(f"Logged in as: **{st.session_state.get('username')}**")
        st.sidebar.markdown("---")
        
        pages = [
            "🏠 Dashboard",
            "💬 AI Chat Companion",
            "📊 Mood Tracker",
            "🧘 Breathing & Meditation",
            "📖 Journal & Gratitude",
            "📅 Habit Tracker",
            "🌙 Sleep Tracker",
            "📝 Stress Self-Assessment",
            "📚 Resource Center",
            "⚙️ Settings"
        ]
        
        selected_page = st.sidebar.radio("Navigation", pages, index=pages.index(st.session_state["current_page"]))
        st.session_state["current_page"] = selected_page
        
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Log Out", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state.clear()
            st.rerun()
            
        # Page Router
        user_id = st.session_state["user_id"]
        
        if selected_page == "🏠 Dashboard":
            render_dashboard(user_id)
        elif selected_page == "💬 AI Chat Companion":
            render_chat_page(user_id)
        elif selected_page == "📊 Mood Tracker":
            render_mood_tracker_page(user_id)
        elif selected_page == "🧘 Breathing & Meditation":
            render_breathing_meditation_page(user_id)
        elif selected_page == "📖 Journal & Gratitude":
            render_journal_page(user_id)
        elif selected_page == "📅 Habit Tracker":
            render_habit_tracker_page(user_id)
        elif selected_page == "🌙 Sleep Tracker":
            render_sleep_tracker_page(user_id)
        elif selected_page == "📝 Stress Self-Assessment":
            render_stress_assessment_page(user_id)
        elif selected_page == "📚 Resource Center":
            render_resource_center_page()
        elif selected_page == "⚙️ Settings":
            render_settings_page(user_id)

if __name__ == "__main__":
    main()
