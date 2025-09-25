import streamlit as st
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

st.set_page_config(page_title="Bulk Email Sender", page_icon="✉️", layout="centered")
st.title("📧 Bulk Email Sender App")

# Step 1: Upload CSV
st.header("Step 1: Upload CSV")
uploaded_file = st.file_uploader("Upload a CSV with columns: Name, Email, Message", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("CSV loaded successfully!")
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"Error reading CSV: {e}")

# Step 2: SMTP Configuration
st.header("Step 2: Configure SMTP")
smtp_server = st.text_input("SMTP Server (e.g., smtp.gmail.com)")
smtp_port = st.number_input("SMTP Port", value=587)
smtp_email = st.text_input("Your Email")
smtp_password = st.text_input("Your Email Password", type="password")

# Step 3: Send Emails
if st.button("Send Emails"):
    if uploaded_file is None:
        st.error("Please upload a CSV first.")
    elif not all([smtp_server, smtp_port, smtp_email, smtp_password]):
        st.error("Please fill in all SMTP details.")
    else:
        success_count = 0
        failed_count = 0
        for idx, row in df.iterrows():
            try:
                msg = MIMEMultipart()
                msg['From'] = smtp_email
                msg['To'] = row['Email']
                msg['Subject'] = "Message from Bulk Email Sender"
                msg.attach(MIMEText(row['Message'], 'plain'))

                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_email, smtp_password)
                server.send_message(msg)
                server.quit()
                
                success_count += 1
            except Exception as e:
                failed_count += 1
                st.warning(f"Failed to send to {row['Email']}: {e}")
        
        st.success(f"Emails sent! ✅ Success: {success_count}, Failed: {failed_count}")
