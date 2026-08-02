"""
email_service.py — Transactional email via Resend
──────────────────────────────────────────────────
Sends OTP verification emails through Resend's API.

Setup:
  1. Create account at https://resend.com (free: 3,000 emails/month)
  2. Get your API key from the dashboard
  3. Set env var:  RESEND_API_KEY=re_xxxxxxxxxxxx

Sending domain:
  • Default (no setup): emails come FROM  onboarding@resend.dev
    Works immediately, but recipients see "via resend.dev" in some clients.
  • Custom domain:  verify noreply@yourdomain.com in Resend dashboard
    (add 2 DNS records — takes 5 minutes). Set RESEND_FROM_EMAIL env var.

Watermarks:  Resend adds ZERO watermarks, footers, or "powered by" text.
             The email is 100% yours.
"""
from __future__ import annotations

import os
import sys

# ─── Config ─────────────────────────────────────────────────
RESEND_API_KEY  = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM     = os.environ.get(
    "RESEND_FROM_EMAIL",
    "Aethel <onboarding@resend.dev>",   # fallback: Resend shared domain (works immediately)
)
APP_NAME        = "Aethel ATS"
SUPPORT_EMAIL   = "support@aethel.ai"


def _send_via_resend(to: str, subject: str, html: str) -> bool:
    """
    POST to Resend's /emails endpoint.
    Returns True on success, False on any failure.
    Falls back gracefully — never crashes the caller.
    """
    if not RESEND_API_KEY:
        # Dev mode: print the OTP to stdout instead of emailing
        print(f"[Email] RESEND_API_KEY not set — printing OTP to console instead.")
        print(f"[Email] TO: {to}  |  SUBJECT: {subject}")
        # Extract OTP from HTML for quick dev inspection
        import re
        codes = re.findall(r'\b\d{6}\b', html)
        if codes:
            print(f"[Email] OTP CODE: {codes[0]}")
        return True   # return True so registration flow still works in dev

    try:
        import requests
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "from":    RESEND_FROM,
                "to":      [to],
                "subject": subject,
                "html":    html,
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            print(f"[Email] Sent '{subject}' to {to!r} — Resend id: {resp.json().get('id')}")
            return True
        else:
            print(f"[Email] Resend error {resp.status_code}: {resp.text}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"[Email] send failed: {e}", file=sys.stderr)
        return False


# ─── Email templates ────────────────────────────────────────

def _otp_html(otp: str, name: str, purpose: str = "verify your email address") -> str:
    """Premium, brandable HTML OTP email. No external CSS or images."""
    digits = list(otp)
    digit_boxes = "".join(
        f'<span style="display:inline-block;width:40px;height:52px;line-height:52px;text-align:center;'
        f'font-size:28px;font-weight:900;font-family:monospace;'
        f'background:#111;color:#fff;border:1px solid #333;border-radius:8px;margin:0 3px;">'
        f'{d}</span>'
        for d in digits
    )
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your {APP_NAME} verification code</title>
</head>
<body style="margin:0;padding:0;background:#000;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#000;min-height:100vh;">
    <tr>
      <td align="center" style="padding:40px 20px;">
        <table width="520" cellpadding="0" cellspacing="0"
               style="background:#0a0a0a;border:1px solid #222;border-radius:16px;overflow:hidden;max-width:520px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="padding:32px 40px 24px;border-bottom:1px solid #1a1a1a;">
              <div style="font-size:22px;font-weight:900;color:#fff;letter-spacing:-0.5px;">
                ◈ {APP_NAME}
              </div>
              <div style="font-size:10px;font-weight:700;color:#555;letter-spacing:3px;text-transform:uppercase;margin-top:4px;">
                Precision Recruitment
              </div>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px 40px;">
              <p style="margin:0 0 8px;font-size:14px;color:#888;">
                Hi {name},
              </p>
              <p style="margin:0 0 28px;font-size:15px;color:#ccc;line-height:1.6;">
                Here's your code to {purpose}. It expires in <strong style="color:#fff;">10 minutes</strong>.
              </p>

              <!-- OTP boxes -->
              <div style="margin:0 0 28px;text-align:center;letter-spacing:4px;">
                {digit_boxes}
              </div>

              <p style="margin:0 0 24px;font-size:12px;color:#555;line-height:1.6;">
                If you didn't request this, you can safely ignore this email.
                Someone may have entered your email address by mistake.
              </p>

              <div style="border-top:1px solid #1a1a1a;padding-top:20px;">
                <p style="margin:0;font-size:11px;color:#444;">
                  This is a transactional email from {APP_NAME}.<br>
                  Questions? Contact us at
                  <a href="mailto:{SUPPORT_EMAIL}" style="color:#666;text-decoration:none;">{SUPPORT_EMAIL}</a>
                </p>
              </div>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


# ─── Public API ─────────────────────────────────────────────

def send_otp_email(to_email: str, otp: str, user_name: str) -> bool:
    """
    Send a 6-digit OTP verification email.
    Returns True if sent (or printed in dev mode), False on failure.
    """
    html = _otp_html(otp, user_name, purpose="verify your Aethel account")
    return _send_via_resend(
        to=to_email,
        subject=f"Your {APP_NAME} verification code: {otp}",
        html=html,
    )


def send_resend_otp_email(to_email: str, otp: str, user_name: str) -> bool:
    """
    Alias for resend flow — send a new OTP when user requests it again.
    """
    html = _otp_html(otp, user_name, purpose="verify your Aethel account")
    return _send_via_resend(
        to=to_email,
        subject=f"New {APP_NAME} verification code: {otp}",
        html=html,
    )
