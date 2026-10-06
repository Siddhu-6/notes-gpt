# Deploying notes-gpt on Microsoft Azure

Live at: https://notes-gpt.wittyflower-e8ca6384.centralindia.azurecontainerapps.io/

Runs on **Azure Container Apps** (scale-to-zero, 2 GB, sticky sessions), on the free **Azure for Students** credit — no credit card. Azure for Students blocks ACR Tasks, so the image is built by **GitHub Actions** and pushed to **GHCR**; Container Apps just pulls it.

## 1. Image build (GitHub Actions → GHCR)

`.github/workflows/docker.yml` builds `Dockerfile` on every push to `main` and pushes to `ghcr.io/siddhu-6/notes-gpt:latest`. After the first green run, make the package public: repo → **Packages → notes-gpt → Package settings → Change visibility → Public**.

## 2. One-time Azure setup

Sign up at https://azure.microsoft.com/free/students with your college email, then in **Cloud Shell** (Bash):

```bash
az extension add --name containerapp --upgrade
az provider register -n Microsoft.App --wait
az provider register -n Microsoft.OperationalInsights --wait
az group create -n notes-gpt-rg -l centralindia
az containerapp env create -n notes-gpt-env -g notes-gpt-rg -l centralindia
```

## 3. Deploy (replace the Groq key)

```bash
az containerapp create -n notes-gpt -g notes-gpt-rg --environment notes-gpt-env \
  --image ghcr.io/siddhu-6/notes-gpt:latest \
  --target-port 8080 --ingress external \
  --cpu 1.0 --memory 2.0Gi --min-replicas 0 --max-replicas 1 \
  --secrets groq-key=gsk_YOUR_KEY \
  --env-vars GROQ_API_KEY=secretref:groq-key

az containerapp ingress sticky-sessions set -n notes-gpt -g notes-gpt-rg --affinity sticky
az containerapp show -n notes-gpt -g notes-gpt-rg --query properties.configuration.ingress.fqdn -o tsv
```

Open `https://<that URL>` — first hit after idle takes ~60–90s to cold-start.

## Update / cost / cleanup

```bash
# redeploy the latest image after a new GitHub Actions build
az containerapp update -n notes-gpt -g notes-gpt-rg --image ghcr.io/siddhu-6/notes-gpt:latest

# keep idle cost at zero (default); or make it instant-on with --min-replicas 1
# tear everything down
az group delete -n notes-gpt-rg --yes --no-wait
```

**Notes:** 2 GB is needed for the reranker (1 GB OOMs). Sticky sessions keep each visitor on one instance because the vector store is in memory. If uploads fail with 403, the `streamlit run` command already passes `--server.enableXsrfProtection=false`.
