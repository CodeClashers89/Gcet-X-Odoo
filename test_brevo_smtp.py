import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Brevo SMTP Configuration
smtp_server = "smtp-relay.brevo.com"
port = 465
sender_email = "hetmungara107@gmail.com"
receiver_email = "kamanipoojan@gmail.com"
login_user = "a139ab001@smtp-brevo.com"
password = "xsmtpsib-f2389cfceecc0dda3de5bf165e8a0de59322827644dc2dee3bb7df815ec93772-3q53Qxm3mQYGkWu3"

# Create message
message = MIMEMultipart("alternative")
message["Subject"] = "Test Email from Brevo SMTP - Direct Python"
message["From"] = sender_email
message["To"] = receiver_email

# Email body
text = "This is a test email sent directly using Python smtplib with Brevo SMTP on port 465."
html = f"""
<html>
  <body>
    <h2>Test Email from Brevo SMTP</h2>
    <p>{text}</p>
    <p>Sent at: 2026-01-31</p>
  </body>
</html>
"""

part1 = MIMEText(text, "plain")
part2 = MIMEText(html, "html")
message.attach(part1)
message.attach(part2)

# Send email
try:
    print(f"Connecting to {smtp_server}:{port}...")
    context = ssl.create_default_context()
    server = smtplib.SMTP_SSL(smtp_server, port, context=context)
    print("Connected! Logging in...")
    server.login(login_user, password)
    print("Login successful! Sending email...")
    server.sendmail(sender_email, receiver_email, message.as_string())
    print(f"✓ Email sent successfully to {receiver_email}")
    server.quit()
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
