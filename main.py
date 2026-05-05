"""
Gmail JobBot - Serverless Inbox Triage
Runs as a Cloud Run Job, triggered by Cloud Scheduler every 30 minutes.
Classifies unread job-related emails and labels them accordingly.
"""

import os
from google.cloud import secretmanager
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ---------- Configuration ----------
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"
MAX_EMAILS_PER_RUN = 25

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# ---------- Classification rules ----------
AUTO_READ_PHRASES = [
    "thank you for applying",
    "we received your application",
    "your application has been submitted",
    "application confirmation",
    "thanks for your interest",
    "thank you for your interest",
    "your job application was received",
    "this is an automated message",
    "do not reply to this email",
    "no reply is required",
]

NEVER_AUTO_READ_PHRASES = [
    "interview", "schedule", "are you available", "next steps", "offer",
    "contract", "rate", "recruiter", "hiring manager", "please respond",
    "action required", "coding challenge", "assessment", "background check",
    "following up", "would like to connect", "phone screen", "vendor", "client",
]


# ---------- Secret + Auth helpers ----------
def get_secret(secret_name: str) -> str:
    """Fetch a secret payload from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def get_gmail_service():
    """Build an authenticated Gmail API client using OAuth credentials from Secret Manager."""
    client_id = get_secret("GMAIL_CLIENT_ID")
    client_secret = get_secret("GMAIL_CLIENT_SECRET")
    refresh_token = get_secret("GMAIL_REFRESH_TOKEN")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    return build("gmail", "v1", credentials=creds)


# ---------- Core logic ----------
def classify_email(subject: str, sender: str, snippet: str) -> str:
    """Rule-based classification. Returns one of four category strings."""
    text = f"{subject} {sender} {snippet}".lower()

    for phrase in NEVER_AUTO_READ_PHRASES:
        if phrase in text:
            if any(word in text for word in
                   ["recruiter", "interview", "schedule", "phone screen", "hiring manager"]):
                return "human_recruiter_or_vendor"
            return "action_required"

    for phrase in AUTO_READ_PHRASES:
        if phrase in text:
            return "auto_acknowledgment"

    return "review_manually"


def get_or_create_label(service, label_name: str) -> str:
    """Idempotent: returns label ID, creating it if missing."""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    label_body = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created_label = service.users().labels().create(userId="me", body=label_body).execute()
    return created_label["id"]


def get_header(headers, name: str) -> str:
    for header in headers:
        if header["name"].lower() == name.lower():
            return header["value"]
    return ""


def main():
    print(f"Starting Gmail JobBot... (DRY_RUN={DRY_RUN})")
    service = get_gmail_service()

    label_auto = get_or_create_label(service, "JobBot/Auto Read")
    label_recruiter = get_or_create_label(service, "JobBot/Recruiter Priority")
    label_action = get_or_create_label(service, "JobBot/Action Required")
    label_review = get_or_create_label(service, "JobBot/Review Manually")

    query = "in:inbox is:unread newer_than:14d"
    result = service.users().messages().list(
        userId="me", q=query, maxResults=MAX_EMAILS_PER_RUN
    ).execute()
    messages = result.get("messages", [])

    print(f"Found {len(messages)} unread inbox messages.")

    for msg in messages:
        msg_id = msg["id"]
        message = service.users().messages().get(
            userId="me", id=msg_id, format="metadata",
            metadataHeaders=["From", "Subject"]
        ).execute()

        headers = message.get("payload", {}).get("headers", [])
        sender = get_header(headers, "From")
        subject = get_header(headers, "Subject")
        snippet = message.get("snippet", "")
        category = classify_email(subject, sender, snippet)

        print("-----------------------------------")
        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print(f"Category: {category}")

        if category == "auto_acknowledgment":
            label_id, remove_unread = label_auto, True
        elif category == "human_recruiter_or_vendor":
            label_id, remove_unread = label_recruiter, False
        elif category == "action_required":
            label_id, remove_unread = label_action, False
        else:
            label_id, remove_unread = label_review, False

        body = {
            "addLabelIds": [label_id],
            "removeLabelIds": ["UNREAD"] if remove_unread else []
        }

        if DRY_RUN:
            print("DRY RUN: No changes made.")
        else:
            service.users().messages().modify(userId="me", id=msg_id, body=body).execute()
            print("Updated email.")

    print("Gmail JobBot finished.")


if __name__ == "__main__":
    main()
