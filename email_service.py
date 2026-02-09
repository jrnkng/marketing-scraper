import os
import smtplib
from email.mime.text import MIMEText


def send_email(subject: str, body: str) -> None:
    """Send an email via Gmail SMTP.

    Args:
        subject: Email subject line
        body: Email body (plain text)
        to_email: Recipient email. Defaults to sender (yourself).
    """
    sender = os.environ.get("GMAIL_ADDRESS", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not sender or not password:
        raise ValueError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in environment")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = sender

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)


def send_needs_response_email(
    post_id: str,
    title: str,
    body: str,
    generated_response: str,
    subreddit: str = "",
) -> None:
    """Send an email notification for a post that needs a response.

    Args:
        post_id: Reddit post ID
        title: Post title
        body: Original post body/content
        generated_response: The AI-generated response
        subreddit: Subreddit name (e.g., "r/hiking")
    """
    reddit_url = f"https://www.reddit.com/comments/{post_id}"

    email_body = f"""Post needs response!

Title: {title}

Subreddit: {subreddit}

Link: {reddit_url}

--- Original Post ---
{body}

--- Generated Response ---
{generated_response}
"""

    subject = f"[Reddit] Needs Response: {title[:50]}"
    send_email(subject, email_body)
