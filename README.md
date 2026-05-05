# Gmail JobBot — Serverless Inbox Triage on Google Cloud

A serverless Python application that automatically triages job-search emails in Gmail. Deployed as a containerized **Cloud Run Job**, scheduled by **Cloud Scheduler**, and authenticated via **Google Secret Manager** — zero servers to manage, zero credentials in code.

> **The problem:** During an active job search, my inbox received 50+ automated "thanks for applying" emails per day, drowning out actual recruiter outreach. Manually triaging them cost ~30 minutes daily.
>
> **The fix:** A rule-based classifier that runs in the cloud every 30 minutes, marks acknowledgments as read, and surfaces real recruiter messages with priority labels — so the only unread emails left are the ones that matter.

---

## Demo

- 🎥 **Video walkthrough:** [INSERT_YOUTUBE_OR_DRIVE_LINK]
- 🎙️ **Audio breakdown:** urlkub.co/xZ31ei
- 📄 **Setup guide (PDF):** [`docs/Gmail_JobBot_Guide.pdf`](docs/Gmail_JobBot_Guide.pdf)

---

## Architecture

```
┌──────────────────┐     every 30 min      ┌──────────────────┐
│ Cloud Scheduler  │ ────────────────────▶ │  Cloud Run Job   │
└──────────────────┘                       │  (Python 3.11)   │
                                           └────────┬─────────┘
                                                    │
                            ┌───────────────────────┼───────────────────────┐
                            ▼                       ▼                       ▼
                  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
                  │ Secret Manager   │   │   Gmail API      │   │ Cloud Logging    │
                  │ (OAuth tokens)   │   │ (read + label)   │   │ (audit trail)    │
                  └──────────────────┘   └──────────────────┘   └──────────────────┘
```

**Flow:**
1. Cloud Scheduler triggers the Cloud Run Job on a cron schedule (`*/30 * * * *`).
2. The container boots, pulls OAuth credentials from Secret Manager (no keys in code or env vars).
3. Gmail API returns up to 25 unread messages from the last 14 days.
4. Each email is scored against keyword rules → assigned one of four labels.
5. Auto-acknowledgments get marked as read; high-signal emails stay unread for human review.
6. All actions are logged to Cloud Logging for auditability.

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Compute | Google Cloud Run Jobs (serverless containers) |
| Scheduling | Google Cloud Scheduler (cron) |
| Secrets | Google Secret Manager |
| Build | Cloud Build + Artifact Registry |
| API | Gmail API (`gmail.modify` scope) |
| Auth | OAuth 2.0 with refresh token flow |
| Container | Docker (slim base image, non-root user) |

---

## Classification logic

Four categories, applied in priority order:

| Category | Trigger | Action |
|---|---|---|
| `JobBot/Recruiter Priority` | Keywords like `recruiter`, `interview`, `phone screen`, `hiring manager` | Label only (stays unread) |
| `JobBot/Action Required` | Keywords like `offer`, `assessment`, `background check`, `please respond` | Label only (stays unread) |
| `JobBot/Auto Read` | Phrases like `thank you for applying`, `do not reply`, `application confirmation` | Label + mark as read |
| `JobBot/Review Manually` | Anything else | Label only (stays unread) |

The classifier is deliberately rule-based, not ML. For an inbox triage problem with clear keyword signals and a low cost of false negatives, a transparent rule engine is faster to ship, easier to debug, and trivial to tune. If volume or ambiguity grew, the next iteration would be a small fine-tuned classifier — but that's overkill for the current need.

---

## Safety constraints

This bot has access to a primary Gmail account, so the design prioritizes safety over cleverness:

- **No deletion, ever.** The code has no `delete` or `trash` calls. The `gmail.modify` scope was chosen specifically because it cannot delete.
- **No archiving.** Emails stay in the inbox; only the `UNREAD` flag and labels are touched.
- **Hard rate limit.** Maximum 25 emails processed per run, preventing runaway behavior or API quota issues.
- **Dry-run mode.** Set `DRY_RUN=true` to log all decisions without modifying any email — used during initial deployment to validate classification accuracy.
- **Least-privilege IAM.** The Cloud Run service account has only `secretmanager.secretAccessor` and the minimum runtime roles. No project-level admin permissions.
- **Secrets in Secret Manager only.** No credentials in the repo, container image, or environment variables.

---

## Deployment

> ⚠️ This repo contains **no credentials**. To run it, you must provision your own GCP project and OAuth client.

### 1. Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. GCP infrastructure

Enable required APIs:

```bash
gcloud services enable \
  gmail.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

Create an OAuth Desktop client in the GCP Console, then run a one-time local script to obtain a refresh token. Store the three values in Secret Manager:

```bash
echo -n "<your-client-id>" | gcloud secrets create GMAIL_CLIENT_ID --data-file=-
echo -n "<your-client-secret>" | gcloud secrets create GMAIL_CLIENT_SECRET --data-file=-
echo -n "<your-refresh-token>" | gcloud secrets create GMAIL_REFRESH_TOKEN --data-file=-
```

### 3. Build and deploy

```bash
# Build the image
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/$PROJECT_ID/gmail-jobbot-repo/gmail-jobbot:latest

# Create the Cloud Run Job (start in dry-run mode)
gcloud run jobs create gmail-jobbot \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/gmail-jobbot-repo/gmail-jobbot:latest \
  --region us-central1 \
  --set-env-vars DRY_RUN=true

# Grant the runtime service account access to the secrets
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:<service-account-email>" \
  --role="roles/secretmanager.secretAccessor"

# Test it
gcloud run jobs execute gmail-jobbot --region us-central1

# When verified, flip off dry-run
gcloud run jobs update gmail-jobbot \
  --region us-central1 \
  --set-env-vars DRY_RUN=false
```

### 4. Schedule it

```bash
gcloud scheduler jobs create http gmail-jobbot-trigger \
  --location us-central1 \
  --schedule "*/30 * * * *" \
  --uri "https://<region>-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/gmail-jobbot:run" \
  --http-method POST \
  --oauth-service-account-email <service-account-email>
```

Full step-by-step guide with screenshots: [`docs/Gmail_JobBot_Guide.pdf`](docs/Gmail_JobBot_Guide.pdf)

---

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | (required) | GCP project ID, set automatically by Cloud Run |
| `DRY_RUN` | `true` | When `true`, logs decisions without modifying any email |

---

## What I'd build next

Honest list of where this stops short of production-grade:

- **Tests.** No unit tests on `classify_email()` yet. That's the obvious first follow-up.
- **Error handling.** Currently lets exceptions bubble up to Cloud Run logs. Should add structured retry logic for transient Gmail API errors (429, 503).
- **Metrics.** Should publish per-category counts to Cloud Monitoring so I can spot rule drift over time.
- **Multi-tenant.** Hardcoded to a single Gmail account. To make this a real product, OAuth onboarding + per-user secret namespacing would be needed.
- **Smarter classifier.** If the keyword rules start misfiring, a small embedding-based classifier (e.g., `sentence-transformers` + cosine similarity to labeled exemplars) would be the cheap upgrade before reaching for an LLM.

---

## Repository contents

```
gmail-jobbot-mvp/
├── main.py              # Application logic + classifier
├── requirements.txt     # Pinned Python dependencies
├── Dockerfile           # Container build (Python 3.11-slim, non-root)
├── .gitignore           # Excludes credentials and local artifacts
├── README.md            # This file
└── docs/
    └── Gmail_JobBot_Guide.pdf   # Full setup walkthrough
```

---

## Suggested GitHub topics

Add these tags to the repo (Settings → Topics) for discoverability:

`python` · `google-cloud-platform` · `cloud-run` · `gmail-api` · `serverless` · `automation` · `docker` · `oauth2` · `secret-manager` · `cloud-scheduler` · `devops` · `inbox-automation`

---

## License

MIT — see [`LICENSE`](LICENSE).

---

**Author:** Siva Sankeerth Daminenii
