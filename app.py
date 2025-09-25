import streamlit as st
import smtplib
import pandas as pd
import time
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import BytesIO
from datetime import datetime

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(page_title="Bulk Email Sender", page_icon="📧", layout="centered")
st.title("📧 Bulk Email Sender")
st.markdown("Send personalized bulk emails with placeholders, reminders, and countdown.")

# -----------------------------
# Login Section
# -----------------------------
with st.container():
    st.subheader("🔐 Login Details")
    col1, col2 = st.columns(2)
    with col1:
        sender_email = st.text_input("Your Email")
        sender_name = st.text_input("Sender Name")
    with col2:
        app_password = st.text_input("App Password", type="password")

# -----------------------------
# Upload Section
# -----------------------------
df = None
with st.container():
    st.subheader("📂 Upload Recipient List")
    st.markdown("CSV must contain: **first_name,last_name,email**")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

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

# -----------------------------
# Email Template Section
# -----------------------------
with st.container():
    st.subheader("📝 Email Template")
    subject_template = st.text_input(
        "Subject (use {full_name}, {first_name}, {last_name})"
    )
    body_template = st.text_area(
        "Email Body (use {first_name}, {last_name}, {full_name}, HTML allowed for bold <b>, italic <i>, color <span style='color:red'>)",
        height=200,
        placeholder="Dear {first_name},\n\nGreetings! Your message here.\n\nRegards,\n{full_name}"
    )

# -----------------------------
# Reminder Section
# -----------------------------
with st.container():
    st.subheader("⏳ Reminder Options")
    fresh_mail_date = st.date_input("If you sent a previous email, select its date:", value=None)
    reminder_option = st.selectbox("Select Reminder Type", ["Fresh Mail", "Reminder 1", "Reminder 2", "Reminder 3"])

# -----------------------------
# Delay Section
# -----------------------------
with st.container():
    st.subheader("⏳ Sending Options")
    delay = st.slider(
        "Delay between emails (seconds)", min_value=10, max_value=120, value=30, step=5
    )

# -----------------------------
# Progress Tracking File
# -----------------------------
progress_file = "email_progress.json"

def load_progress():
    try:
        with open(progress_file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_progress(progress):
    with open(progress_file, "w") as f:
        json.dump(progress, f)

# -----------------------------
# Send Emails
# -----------------------------
if st.button("🚀 Send Emails"):
    if df is not None and sender_email and app_password:
        # Try logging in
        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(sender_email, app_password)
        except Exception as e:
            st.error(f"❌ Login failed: {e}")
            st.stop()

        # Load progress
        progress = load_progress()
        start_idx = progress.get(reminder_option, 0)

        total = len(df)
        success_count = 0
        fail_count = 0
        failed_emails = []

        progress_bar = st.progress(0)
        status_text = st.empty()
        countdown_text = st.empty()

        for idx in range(start_idx, total):
            row = df.iloc[idx]
            recipient = row["email"]
            first = row["first_name"]
            last = row["last_name"]
            full_name = f"{first} {last}"

            # Subject and body
            subject = subject_template.format(first_name=first, last_name=last, full_name=full_name)
            body = body_template.format(first_name=first, last_name=last, full_name=full_name)

            # For reminder emails, add previous mail trail
            if reminder_option != "Fresh Mail" and fresh_mail_date:
                body = f"<p>Following up on our email sent on {fresh_mail_date}:</p><hr>{body}"

            msg = MIMEMultipart()
            msg["From"] = f"{sender_name} <{sender_email}>"
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            try:
                server.sendmail(sender_email, recipient, msg.as_string())
                success_count += 1
            except Exception as e:
                fail_count += 1
                failed_emails.append({
                    "email": recipient,
                    "first_name": first,
                    "last_name": last,
                    "error": str(e),
                })

            # Update progress
            progress_bar.progress((idx + 1) / total)
            status_text.text(f"Sent {idx + 1} of {total} emails")

            # Countdown timer
            for remaining in range(delay, 0, -1):
                countdown_text.text(f"⏳ Waiting {remaining} seconds before next email...")
                time.sleep(1)

            # Save progress
            progress[reminder_option] = idx + 1
            save_progress(progress)

        server.quit()

        # Final Summary
        st.success(f"🎉 Process completed!\n✅ Sent: {success_count}\n❌ Failed: {fail_count}\n📩 Total: {total}")

        # Export failed emails
        if fail_count > 0:
            failed_df = pd.DataFrame(failed_emails)
            buffer = BytesIO()
            failed_df.to_csv(buffer, index=False)
            buffer.seek(0)
            st.error("Some emails failed. Download CSV:")
            st.download_button(
                label="⬇️ Download Failed Emails CSV",
                data=buffer,
                file_name="failed_emails.csv",
                mime="text/csv"
            )
    else:
        st.warning("⚠️ Please provide login details and upload a valid CSV.")
