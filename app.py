import streamlit as st
import smtplib
import pandas as pd
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import BytesIO
import os
import json
from streamlit_quill import st_quill  

# ----------------- SETTINGS -----------------
STATE_FILE = "email_progress.json"

# Page config
st.set_page_config(page_title="Bulk Email Sender", page_icon="📧", layout="centered")

st.title("📧 Bulk Email Sender")
st.markdown("Send personalized bulk emails with placeholders, resume option, reminders, and rich text formatting.")

st.info("""
💡 Formatting Options:
- **Bold / Italic / Underline**
- 🎨 Text Color / Highlight
- Font Family / Font Size
- Lists, Links, Blockquotes, Code Blocks
""")

# ----------------- Login Section -----------------
with st.container():
    st.subheader("🔐 Login Details")
    col1, col2 = st.columns(2)
    with col1:
        sender_email = st.text_input("Your Email")
        sender_name = st.text_input("Sender Name")
    with col2:
        app_password = st.text_input("App Password", type="password")

# ----------------- Upload Section -----------------
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

# ----------------- Email Options -----------------
with st.container():
    st.subheader("📌 Email Type")
    email_type = st.radio(
        "Choose Email Type",
        ["Fresh Mail", "Reminder 1", "Reminder 2", "Reminder 3"],
        horizontal=True,
    )

# ----------------- Template Section -----------------
with st.container():
    st.subheader("📝 Email Templates (Rich Text)")

    subject_template = st.text_input(
        "Subject (use {full_name}, {first_name}, {last_name})"
    )

    # Quill toolbar with fonts and sizes
    quill_toolbar = [
        ["bold", "italic", "underline", "strike"],
        [{"color": []}, {"background": []}],
        [{"font": []}],
        [{"size": ["small", False, "large", "huge"]}],
        [{"list": "ordered"}, {"list": "bullet"}],
        ["link", "blockquote", "code-block"],
    ]

    st.markdown("### ✉️ Fresh Mail Template")
    fresh_template_html = st_quill(
        value="Dear {first_name},<br><br>This is my <b>initial outreach</b>.<br><br>Regards,<br>{full_name}",
        placeholder="Write your Fresh Mail here...",
        key="fresh_template",
        html=True,
        toolbar=quill_toolbar
    )

    reminder_template_html = None
    if email_type != "Fresh Mail":
        st.markdown(f"### 🔄 {email_type} Template")
        reminder_template_html = st_quill(
            value="Dear {first_name},<br><br><span style='color:blue;'>Just following up</span> regarding my previous email.<br><br>Best regards,<br>{full_name}",
            placeholder="Write your Reminder here...",
            key="reminder_template",
            html=True,
            toolbar=quill_toolbar
        )

# ----------------- Delay -----------------
with st.container():
    st.subheader("⏳ Sending Options")
    delay = st.slider(
        "Delay between emails (seconds)", min_value=10, max_value=120, value=30, step=5
    )

# ----------------- Resume Logic -----------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_sent_index": -1, "fresh_mail_html": ""}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# ----------------- Send Emails -----------------
if st.button("🚀 Send Emails"):
    if df is not None and sender_email and app_password:
        state = load_state()
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

        total = len(df)
        success_count = 0
        fail_count = 0
        failed_emails = []

        # Save Fresh Mail template if sending Fresh Mail
        if email_type == "Fresh Mail":
            state["fresh_mail_html"] = fresh_template_html
            save_state(state)

        for idx, row in df.iloc[start_index:].iterrows():
            recipient = row["email"]
            first = row["first_name"]
            last = row["last_name"]
            full_name = f"{first} {last}"

            subject = subject_template.format(
                first_name=first, last_name=last, full_name=full_name
            )

            # Compose email body
            if email_type == "Fresh Mail":
                body = fresh_template_html.format(
                    first_name=first, last_name=last, full_name=full_name
                )
            else:
                reminder_body = reminder_template_html.format(
                    first_name=first, last_name=last, full_name=full_name
                )
                original_body = state.get("fresh_mail_html", "").format(
                    first_name=first, last_name=last, full_name=full_name
                )
                body = reminder_body + "<br><br>----- Original Message -----<br>" + original_body

            # Create HTML email
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
                failed_emails.append({
                    "email": recipient,
                    "first_name": first,
                    "last_name": last,
                    "error": str(e)
                })

            # Update progress and status
            progress.progress((idx + 1) / total)
            status_placeholder.markdown(
                f"✅ Sent: {success_count} | ❌ Failed: {fail_count} | 📩 Total: {total}"
            )

            # Countdown before next email
            if idx < total - 1:
                for remaining in range(delay, 0, -1):
                    countdown_placeholder.markdown(
                        f"⏳ Waiting **{remaining} seconds** before next email..."
                    )
                    time.sleep(1)

        server.quit()
        st.success(
            f"🎉 Process completed!\n\n✅ Sent: {success_count}\n❌ Failed: {fail_count}\n📩 Total: {total}"
        )
        countdown_placeholder.empty()

        if fail_count > 0:
            failed_df = pd.DataFrame(failed_emails)
            buffer = BytesIO()
            failed_df.to_csv(buffer, index=False)
            buffer.seek(0)
            st.error("Some emails failed. Download the list below:")
            st.download_button(
                label="⬇️ Download Failed Emails CSV",
                data=buffer,
                file_name="failed_emails.csv",
                mime="text/csv",
            )
    else:
        st.warning("⚠️ Please provide login details and upload a valid CSV.")
