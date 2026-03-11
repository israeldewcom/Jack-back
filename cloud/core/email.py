import os
import resend
from typing import List

resend.api_key = os.getenv("RESEND_API_KEY")

def send_email(to: List[str], subject: str, html: str):
    params = {
        "from": "CITP <noreply@citp.com>",
        "to": to,
        "subject": subject,
        "html": html,
    }
    return resend.Emails.send(params)

def send_invitation_email(email: str, inviter_name: str, invite_link: str):
    html = f"""
    <h2>You've been invited to join CITP</h2>
    <p>{inviter_name} has invited you to join their organization on CITP.</p>
    <p><a href="{invite_link}">Accept invitation</a></p>
    <p>This link expires in 7 days.</p>
    """
    return send_email([email], "Invitation to CITP", html)

def send_password_reset_email(email: str, reset_link: str):
    html = f"""
    <h2>Password reset requested</h2>
    <p>Click the link below to reset your password. This link expires in 1 hour.</p>
    <p><a href="{reset_link}">Reset password</a></p>
    <p>If you didn't request this, ignore this email.</p>
    """
    return send_email([email], "CITP Password Reset", html)
