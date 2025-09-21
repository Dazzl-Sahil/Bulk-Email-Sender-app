import streamlit as st
import smtplib
import pandas as pd
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Page config
st.set_page_config(page_title="Bulk Email Sender", page_icon="📧", layout="centered")

st.title("📧 Bulk Email Sender")
st.markdown("Send personalized bulk emails with placeholders and delay control.")

# --- Login Section ---
with st.container():
    st.subheader("🔐 Login Details")
    col1, col2 = st.columns(2)
    with col1:
        sender_email = st.text_input("Your Email")
        sender_name = st.text_input("Sender Name")
    with col2:
        app_password = st.text_input("App Password", type="password")

# --- Upload Section ---
with st.container():
    st.subheader("📂 Upload Recipient List")
    st.markdown("CSV must contain: **email, first_name, last_name**")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

# --- Email Template Section ---
with st.container():
    st.subheader("📝 Email Template")
    subject_template = st.text_input("Subject (use {full_name}, {first_name}, {last_name})")
    body_template = st.text_area(
        "Email Body (Markdown supported — use {first_name}, {last_name}, {full_name})",
        height=200
    )

# --- Delay Control ---
with st.container():
    st.subheader("⏳ Sending Options")
    delay = st.slider("Delay between emails (seconds)", min_value=10, max_value=120, value=30, step=5)

# --- Send Button ---
if st.button("🚀 Send Emails"):
    if uploaded_file is not None and sender_email and app_password:
        try:
            df = pd.read_csv(uploaded_file, encoding='ISO-8859-1')  # Handle encoding issues
        except Exception as e:
            st.error(f"❌ Failed to read CSV: {e}")
            st.stop()

        required_columns = ['email', 'first_name', 'last_name']
        if not all(col in df.columns for col in required_columns):
            st.error(f"❌ CSV must contain the following columns: {', '.join(required_columns)}")
            st.stop()

        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(sender_email, app_password)
        except Exception as e:
            st.error(f"❌ Failed to connect to SMTP server: {e}")
            st.stop()

        progress = st.progress(0)
        total = len(df)

        for idx, row in df.iterrows():
            recipient = row['email']
            first = row['first_name']
            last = row['last_name']
            full_name = f"{first} {last}"

            # Replace placeholders
            subject = subject_template.format(first_name=first, last_name=last, full_name=full_name)
            body = body_template.format(first_name=first, last_name=last, full_name=full_name)

            msg = MIMEMultipart()
            msg["From"] = f"{sender_name} <{sender_email}>"
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            try:
                server.sendmail(sender_email, recipient, msg.as_string())
                st.success(f"✅ Sent to {recipient}")
            except Exception as e:
                st.error(f"❌ Failed for {recipient}: {e}")

            progress.progress((idx + 1) / total)

            # Delay before sending the next email
            if idx < total - 1:
                st.info(f"⏳ Waiting {delay} seconds before next email...")
                time.sleep(delay)

        server.quit()
        st.success("🎉 All emails sent successfully!")
    else:
        st.warning("⚠️ Please provide login details and upload CSV.")
