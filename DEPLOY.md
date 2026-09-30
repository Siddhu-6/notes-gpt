# Deploying notes-gpt on Google Cloud Run

Cloud Run runs the Docker image in this repo, scales to zero when nobody is using it, and gives you an HTTPS URL. With the settings below, normal demo traffic stays inside the monthly free tier.

**What you get:** `https://notes-gpt-xxxxx-uc.a.run.app`, running the same app as Streamlit Cloud.

## What the Dockerfile does

- Installs CPU-only PyTorch (the default wheel bundles CUDA and triples the image size).
- Installs only what the app imports.
- Downloads `bge-small-en-v1.5` and `bge-reranker-base` **at build time**, then switches Hugging Face to offline mode, so a cold start never downloads 1+ GB.
- Runs Streamlit as a non-root user on the port Cloud Run gives it (`$PORT`, 8080).

Tested locally: the container passes Streamlit's health check within a few seconds, and retrieval works with networking disabled.

## One-time setup (about 15 minutes)

1. Go to <https://console.cloud.google.com>, sign in, and create a project (for example `notes-gpt-demo`). New accounts get the free trial credit; a card is needed to verify the account.
2. **Set a budget alert first:** Billing → Budgets & alerts → Create budget → ₹500, alerts at 50/90/100%.
3. Open **Cloud Shell** (the `>_` icon, top right). It already has `gcloud`, `git` and Docker, so nothing needs installing on your laptop.

## Deploy

Run these in Cloud Shell. Replace `YOUR_PROJECT_ID` and `gsk_...`.

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com

git clone https://github.com/Siddhu-6/notes-gpt.git && cd notes-gpt

# Store the Groq key as a secret instead of a plain environment variable
printf '%s' 'gsk_...' | gcloud secrets create groq-api-key --data-file=-

PROJECT_NUMBER=$(gcloud projects describe "$(gcloud config get-value project)" --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding groq-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor

# Build with Cloud Build and deploy (first build takes ~10 minutes: it downloads PyTorch and both models)
gcloud run deploy notes-gpt \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi --cpu 1 \
  --timeout 3600 \
  --session-affinity \
  --min-instances 0 --max-instances 2 \
  --set-secrets GROQ_API_KEY=groq-api-key:latest
```

When it finishes it prints the service URL. Open it, upload a PDF, ask a question.

### Why these flags

| Flag | Reason |
|---|---|
| `--memory 2Gi` | The reranker alone is ~1.1 GB in memory. With 1 GiB the instance gets killed. |
| `--timeout 3600` | Streamlit talks to the browser over a WebSocket. Cloud Run cuts WebSockets at the request timeout, which is 5 minutes by default and 60 at most. |
| `--session-affinity` | Uploaded PDFs live in memory on one instance. Affinity keeps a user on the same instance (best effort). |
| `--min-instances 0` | Scales to zero when idle, so you pay nothing between demos. The trade-off is a slower first request. |
| `--max-instances 2` | Caps cost if the link gets shared widely. |
| `us-central1` | The free tier's outbound data allowance is for North America. `asia-south1` (Mumbai) is faster from India but outbound traffic is billed. |

### Free tier maths

The free tier is 180,000 vCPU-seconds and 360,000 GiB-seconds per month per billing account. At 1 vCPU and 2 GiB that is about **50 hours of active use a month**. Cloud Run bills an instance while it serves a request, and an open Streamlit tab is one long request, so close demo tabs when you're done.

## Updating

Push changes to GitHub, then in Cloud Shell:

```bash
cd ~/notes-gpt && git pull
gcloud run deploy notes-gpt --source . --region us-central1
```

Flags from the first deploy are kept.

## Checking on it

```bash
gcloud run services describe notes-gpt --region us-central1 --format='value(status.url)'
gcloud run services logs read notes-gpt --region us-central1 --limit 50
```

## Troubleshooting

- **"Memory limit exceeded" in logs** → redeploy with `--memory 4Gi`.
- **First question after a while is slow** → cold start plus model loading. `--min-instances 1` removes it but is billed around the clock.
- **Upload fails with a 403** → add `--server.enableXsrfProtection=false` to the `streamlit run` command in the Dockerfile and redeploy.
- **Chat resets after an hour** → that is the 60-minute WebSocket cap; refresh the page.

## Same image on AWS

The Dockerfile is not GCP-specific. On AWS, push it to ECR and run it on ECS Fargate, or run it on an EC2 instance with `docker run -p 80:8080 -e GROQ_API_KEY=... notes-gpt`.
