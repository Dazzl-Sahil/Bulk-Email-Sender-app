import streamlit as st
import smtplib
import pandas as pd
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import BytesIO
import os
import json
import plotly.graph_objects as go

# ----------------- SETTINGS -----------------
STATE_FILE = "email_progress.json"

# Page config
st.set_page_config(page_title="Bulk Email Sender", page_icon="📧", layout="wide")

# ----------------- CUSTOM CSS -----------------
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #f5f7fa, #c3cfe2); color: #333; }
.stContainer { border-radius: 12px; padding: 15px; background-color: rgba(255,255,255,0.95); box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 20px; }
div.stButton > button:first-child { background-color: #4a90e2; color: white; border-radius: 10px; height: 50px; width: 220px; font-size:16px; font-weight:bold; }
div.stButton > button:hover { background-color: #f39c12; color: white; }
.progress-box { padding:10px; border-radius:8px; font-weight:bold; }
hr { border: 2px solid #f39c12; }
.current-step { background-color:#4a90e2; color:white; padding:5px 10px; border-radius:8px; margin-bottom:5px; }
.step { padding:5px 10px; margin-bottom:5px; border-radius:8px; background-color:#f0f0f0; }
</style>
""", unsafe_allow_html=True)

# ----------------- FUNCTIONS -----------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_sent_index": -1, "fresh_mail_body": ""}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1605902711622-cfb43c4438d2?auto=format&fit=crop&w=400&q=80", use_column_width=True)
    st.markdown("<h3 style='color:#4a90e2'>Steps Guide</h3>", unsafe_allow_html=True)
    steps = ["Login", "Upload CSV", "Email Template", "Send Emails"]
    
    current_step = 0
    sender_email = st.session_state.get("sender_email", None)
    uploaded_file = st.session_state.get("uploaded_file", None)
    email_template_ready = st.session_state.get("email_template_ready", False)
    
    if not sender_email: current_step = 0
    elif not uploaded_file: current_step = 1
    elif not email_template_ready: current_step = 2
    else: current_step = 3
    
    for i, step in enumerate(steps):
        if i == current_step:
            st.markdown(f"<div class='current-step'>➡️ {step}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='step'>{step}</div>", unsafe_allow_html=True)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("⚠️ Reset Progress"):
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            st.success("✅ Progress reset successfully!")
        else:
            st.info("ℹ️ No progress file found.")
    st.markdown("[📖 Documentation](https://your-documentation-link.com)")
    st.markdown("[✉️ Contact Support](mailto:support@example.com)")

# ----------------- APP TITLE -----------------
st.image("https://images.unsplash.com/photo-1581091215360-1c2b5e3b47b4?auto=format&fit=crop&w=1200&q=80", use_column_width=True)
st.title("📧 Bulk Email Sender")
st.markdown("Send personalized bulk emails with reminders, resume, animated countdown, and live progress charts.")
st.info("💡 Features: HTML formatting, Resume, Reminders, Countdown & Pie Chart, Modern UI")

# ----------------- LOGIN -----------------
with st.container():
    st.markdown("<h3 style='color:#4a90e2'>🔐 Login Details</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        sender_email = st.text_input("Your Email")
        st.session_state.sender_email = sender_email
        sender_name = st.text_input("Sender Name")
    with col2:
        app_password = st.text_input("App Password", type="password")

# ----------------- UPLOAD CSV -----------------
df = None
with st.container():
    st.markdown("<h3 style='color:#4a90e2'>📂 Upload Recipient List</h3>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    st.session_state.uploaded_file = uploaded_file
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            required_cols = {"email", "first_name", "last_name"}
            if not required_cols.issubset(df.columns):
                st.error(f"❌ CSV missing required columns. Found: {list(df.columns)}")
                df = None
            else:
                st.write("📊 Preview of uploaded data (first 5 rows):")
                st.dataframe(df.head())
        except Exception as e:
            st.error(f"❌ Could not read CSV: {e}")

# ----------------- EMAIL TYPE & TEMPLATE -----------------
with st.container():
    st.markdown("<h3 style='color:#4a90e2'>📌 Email Type & Templates</h3>", unsafe_allow_html=True)
    email_type = st.radio("Choose Email Type", ["Fresh Mail", "Reminder 1", "Reminder 2", "Reminder 3"], horizontal=True)
    subject_template = st.text_input("Subject (use {full_name}, {first_name}, {last_name})")
    
    st.markdown("### ✉️ Email Body Template (HTML allowed: <b>, <i>, <span style='color:red;'>color</span>)")
    fresh_template_body = st.text_area(
        "Fresh Mail Template",
        value="Dear {first_name},\n\nThis is my <b>initial outreach</b>.\n\nRegards,\n{full_name}",
        height=200
    )
    
    reminder_template_body = None
    if email_type != "Fresh Mail":
        reminder_template_body = st.text_area(
            f"{email_type} Template",
            value="Dear {first_name},\n\nJust following up regarding my previous email.\n\nBest regards,\n{full_name}",
            height=200
        )
    
    st.session_state.email_template_ready = True

# ----------------- DELAY -----------------
with st.container():
    st.markdown("<h3 style='color:#4a90e2'>⏳ Sending Options</h3>", unsafe_allow_html=True)
    delay = st.slider("Delay between emails (seconds)", min_value=10, max_value=120, value=30, step=5)

# ----------------- SEND EMAIL LOGIC -----------------
state = load_state()
if st.button("🚀 Send Emails"):
    if df is not None and sender_email and app_password:
        start_index = state.get("last_sent_index", -1) + 1
        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(sender_email, app_password)
        except Exception as e:
            st.error(f"❌ Login failed: {e}")
            st.stop()

        progress = st.progress(0)
        status_placeholder = st.empty()
        countdown_placeholder = st.empty()
        pie_placeholder = st.empty()
        
        total = len(df)
        success_count = 0
        fail_count = 0
        failed_emails = []

        if email_type == "Fresh Mail":
            state["fresh_mail_body"] = fresh_template_body
            save_state(state)

        for idx, row in df.iloc[start_index:].iterrows():
            recipient = row["email"]
            first = row["first_name"]
            last = row["last_name"]
            full_name = f"{first} {last}"

            subject = subject_template.format(first_name=first, last_name=last, full_name=full_name)

            if email_type == "Fresh Mail":
                body = fresh_template_body.format(first_name=first, last_name=last, full_name=full_name)
            else:
                reminder_body = reminder_template_body.format(first_name=first, last_name=last, full_name=full_name)
                original_body = state.get("fresh_mail_body", "").format(first_name=first, last_name=last, full_name=full_name)
                body = reminder_body + "<br><br>----- Original Message -----<br>" + original_body

            msg = MIMEMultipart()
            msg["From"] = f"{sender_name} <{sender_email}>"
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            try:
                server.sendmail(sender_email, recipient, msg.as_string())
                success_count += 1
                state["last_sent_index"] = idx
                save_state(state)
            except Exception as e:
                fail_count += 1
                failed_emails.append({"email": recipient,"first_name": first,"last_name": last,"error": str(e)})

            # Update progress & status
            progress.progress((idx + 1)/total)
            status_placeholder.markdown(f"✅ Sent: {success_count} | ❌ Failed: {fail_count} | 📩 Total: {total}")

            # Countdown
            if idx < total - 1:
                for remaining in range(delay,0,-1):
                    countdown_placeholder.markdown(f"⏳ Waiting **{remaining} seconds** before next email...")
                    time.sleep(1)
                countdown_placeholder.empty()

        server.quit()
        st.success(f"🎉 Process completed!\n✅ Sent: {success_count}\n❌ Failed: {fail_count}\n📩 Total: {total}")

        # Export failed emails
        if fail_count > 0:
            failed_df = pd.DataFrame(failed_emails)
            buffer = BytesIO()
            failed_df.to_csv(buffer, index=False)
            buffer.seek(0)
            st.download_button(label="⬇️ Download Failed Emails CSV", data=buffer, file_name="failed_emails.csv", mime="text/csv")
    else:
        st.warning("⚠️ Please provide login details and upload a valid CSV.")
