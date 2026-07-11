import resend
import logging
from packvote.backend.core.config import settings

# Initialize Resend client if key is set
if settings.resend_api_key and not settings.resend_api_key.startswith("change-me"):
    resend.api_key = settings.resend_api_key
else:
    logging.warning("Resend API key is not configured. Email sending will be mocked/printed to stdout.")

def send_management_link(to_email: str, trip_name: str, management_token: str) -> dict:
    """Sends the trip management link to the organiser via Resend."""
    manage_url = f"{settings.frontend_url}/manage?token={management_token}"
    html_content = f"""
    <h3>Your PackVote trip recovery link for <strong>{trip_name}</strong></h3>
    <p>Use the link below to access your organiser dashboard, where you can view participant status, copy participant survey links, and close the survey when ready:</p>
    <p><a href="{manage_url}" target="_blank">{manage_url}</a></p>
    <p>Happy travel planning!<br>The PackVote Team</p>
    """
    
    if not resend.api_key:
        print("\n=== MOCK EMAIL SENT ===")
        print(f"To: {to_email}")
        print(f"Subject: Your PackVote trip: {trip_name}")
        print(f"Content:\n{html_content}")
        print("=======================\n")
        return {"id": "mock-email-id", "mocked": True}
        
    try:
        response = resend.Emails.send({
            "from": settings.resend_from_email,
            "to": to_email,
            "subject": f"Your PackVote trip: {trip_name}",
            "html": html_content
        })
        return response
    except Exception as e:
        logging.error(f"Failed to send email via Resend: {e}")
        raise e
