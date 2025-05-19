import streamlit as st
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("therabot-credentials.json", scope)
client = gspread.authorize(creds)

sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1wIewM-ehdoZTXB6OgP9vTXWqPhXkLZDfAY8O5w03Ntk")
mood_ws = sheet.worksheet("Mood Logs")
journal_ws = sheet.worksheet("Journal History")

# Streamlit UI
st.set_page_config(page_title="In2Grative TheraBot", layout="centered")
st.title("In2Grative TheraBot")
page = st.sidebar.selectbox("Navigate to:", ["Mood Scale", "Journal Entry"])

if page == "Mood Scale":
    st.header("Mood Scale")
    mood = st.slider("Rate your mood (0–10)", 0, 10)
    note = st.text_input("Optional note")
    if st.button("Submit Mood"):
        mood_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), mood, note])
        st.success("Mood entry saved to Google Sheets.")

elif page == "Journal Entry":
    st.header("Journal Entry")
    entry = st.text_area("Write your thoughts")
    if st.button("Submit Entry"):
        journal_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), entry])
        st.success("Journal entry saved to Google Sheets.")
