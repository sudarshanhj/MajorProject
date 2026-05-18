import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("DeepStegAI.Email")

def send_admin_notification(entry):
    """
    Sends an email notification to the administrator about a new contact message.
    entry: dict containing 'name', 'email', 'message', 'timestamp'
    """
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASS", "").replace(" ", "").strip()
    notify_email = os.environ.get("NOTIFY_EMAIL", "aravalli813@gmail.com").strip()
    use_mock = os.environ.get("USE_MOCK_EMAIL", "False").lower() == "true"

    if use_mock:
        print("\n" + "="*50)
        print("📨 [MOCK EMAIL] NEW ADMIN NOTIFICATION")
        print(f"To: {notify_email}")
        print(f"Subject: New Message from {entry.get('name')}")
        print(f"Content: {entry.get('message')}")
        print("="*50 + "\n")
        logger.info(f"Mock admin notification logged for {notify_email}")
        return

    if not smtp_user or not smtp_pass:
        logger.warning("SMTP credentials not configured. Skipping email notification.")
        return

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = notify_email
        msg['Subject'] = f"🚨 DeepStegAI: New Message from {entry.get('name', 'Anonymous')}"

        body = f"""
        <html>
        <body style="font-family: sans-serif; color: #1e293b;">
            <div style="background: #0f172a; padding: 20px; border-radius: 10px; color: white;">
                <h2 style="color: #00f2ff; margin-bottom: 20px; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">
                    New Support Inquiry Detected
                </h2>
                <p><strong>Operator Name:</strong> {entry.get('name', 'N/A')}</p>
                <p><strong>Contact Email:</strong> {entry.get('email', 'N/A')}</p>
                <p><strong>Timestamp:</strong> {entry.get('timestamp', 'N/A')}</p>
                <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 5px; margin-top: 20px; border-left: 4px solid #00f2ff;">
                    <p style="font-style: italic;">"{entry.get('message', 'No content')}"</p>
                </div>
                <p style="font-size: 10px; margin-top: 30px; opacity: 0.5;">
                    This is an automated encrypted notification from DeepStegAI Kernel.
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        # Connect and send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls() # Secure the connection
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            
        logger.info(f"Admin notification sent to {notify_email}")
        
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")

def send_password_reset_email(user_email, reset_token):
    """
    Sends a password reset link to the user.
    """
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASS", "").replace(" ", "").strip()
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173").strip()
    use_mock = os.environ.get("USE_MOCK_EMAIL", "False").lower() == "true"

    reset_link = f"{frontend_url}/reset-password?token={reset_token}"

    if use_mock:
        print("\n" + "="*50)
        print("📨 [MOCK EMAIL] PASSWORD RESET REQUEST")
        print(f"To: {user_email}")
        print(f"Reset Link: {reset_link}")
        print("="*50 + "\n")
        logger.info(f"Mock reset email logged for {user_email}")
        return

    if not smtp_user or not smtp_pass:
        logger.warning("SMTP credentials not configured. Skipping reset email.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = user_email
        msg['Subject'] = "🔐 DeepStegAI: Password Reset Request"
        
        body = f"""
        <html>
        <body style="font-family: sans-serif; color: #1e293b;">
            <div style="background: #0f172a; padding: 20px; border-radius: 10px; color: white;">
                <h2 style="color: #00f2ff;">Reset Your Password</h2>
                <p>We received a request to reset your DeepStegAI password. Click the button below to proceed:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" style="background: #00f2ff; color: #0f172a; padding: 12px 25px; border-radius: 5px; text-decoration: none; font-weight: bold;">Reset Password</a>
                </div>
                <p style="font-size: 12px; opacity: 0.7;">This link will expire in 1 hour. If you didn't request this, you can safely ignore this email.</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            
        logger.info(f"Password reset email sent to {user_email}")
        
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")

def send_user_receipt(entry):
    """
    Sends a confirmation receipt to the user who submitted a support message.
    """
    user_email = entry.get('email')
    if not user_email or user_email == 'No Email':
        return

    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASS", "").replace(" ", "").strip()
    use_mock = os.environ.get("USE_MOCK_EMAIL", "False").lower() == "true"

    if use_mock:
        print("\n" + "="*50)
        print("📨 [MOCK EMAIL] USER RECEIPT")
        print(f"To: {user_email}")
        print(f"Message: Protocol Initiated for ID #{entry.get('id')}")
        print("="*50 + "\n")
        logger.info(f"Mock user receipt logged for {user_email}")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = user_email
        msg['Subject'] = f"✅ DeepStegAI: Message Received (ID: #{entry.get('id')})"

        body = f"""
        <html>
        <body style="font-family: sans-serif; color: #1e293b;">
            <div style="background: #0f172a; padding: 20px; border-radius: 10px; color: white;">
                <h2 style="color: #00f2ff;">Protocol Initiated</h2>
                <p>Hello {entry.get('name', 'Operator')},</p>
                <p>We have successfully received your inquiry in the DeepStegAI Support Stream.</p>
                <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #00f2ff;">
                    <p style="font-size: 14px; opacity: 0.8;">"Our neural engines are processing your request. Administrator <strong>ARAVALLI</strong> has been notified and will respond shortly."</p>
                </div>
                <p><strong>Reference ID:</strong> #{entry.get('id')}</p>
                <p style="font-size: 10px; margin-top: 30px; opacity: 0.5;">
                    This is an automated encrypted confirmation from DeepStegAI Kernel.
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            
        logger.info(f"User receipt sent to {user_email}")
        
    except Exception as e:
        logger.error(f"Failed to send user receipt: {e}")

def send_otp_email(user_email, otp_code):
    """
    Sends a 6-digit OTP to the user for signup verification.
    """
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASS", "").replace(" ", "").strip()
    use_mock = os.environ.get("USE_MOCK_EMAIL", "False").lower() == "true"

    if use_mock:
        print("\n" + "="*50)
        print("📨 [MOCK EMAIL] OTP VERIFICATION")
        print(f"To: {user_email}")
        print(f"OTP Code: {otp_code}")
        print("="*50 + "\n")
        logger.info(f"Mock OTP email logged for {user_email}")
        return

    if not smtp_user or not smtp_pass:
        logger.warning("SMTP credentials not configured. Skipping OTP email.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = user_email
        msg['Subject'] = "🔐 DeepStegAI: Verify Your Email"
        
        body = f"""
        <html>
        <body style="font-family: sans-serif; color: #1e293b;">
            <div style="background: #0f172a; padding: 20px; border-radius: 10px; color: white;">
                <h2 style="color: #00f2ff;">Verify Your Email Address</h2>
                <p>Welcome to DeepStegAI! Please use the following One-Time Password to complete your registration:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <span style="background: rgba(255,255,255,0.1); color: #00f2ff; padding: 15px 30px; border-radius: 8px; font-size: 24px; font-weight: bold; letter-spacing: 5px;">{otp_code}</span>
                </div>
                <p style="font-size: 12px; opacity: 0.7;">This code will expire in 10 minutes. Do not share this code with anyone.</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            
        logger.info(f"OTP email sent to {user_email}")
        
    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")

