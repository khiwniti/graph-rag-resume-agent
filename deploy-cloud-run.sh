#!/bin/bash
# Deploy Graph RAG Resume Agent to Google Cloud Run

set -e

echo "========================================"
echo "Graph RAG Resume Agent - Cloud Run Deploy"
echo "========================================"

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
SERVICE_NAME="graph-rag-agent"
REGION="${GCP_REGION:-us-central1}"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No GCP project ID set."
    echo "Set GCP_PROJECT_ID env var or run: gcloud config set project <project-id>"
    exit 1
fi

echo "Project ID: $PROJECT_ID"
echo "Service Name: $SERVICE_NAME"
echo "Region: $REGION"

# Step 1: Build Docker image
echo ""
echo "Step 1: Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .

# Step 2: Push to Container Registry
echo ""
echo "Step 2: Pushing to Google Container Registry..."
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

# Step 3: Deploy to Cloud Run
echo ""
echo "Step 3: Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars="GITHUB_TOKEN=${GITHUB_TOKEN},VERCEL_TOKEN=${VERCEL_TOKEN},CLOUDFLARE_TOKEN=${CLOUDFLARE_TOKEN},CLOUDFLARE_ACCOUNT_ID=${CLOUDFLARE_ACCOUNT_ID},NEO4J_URI=${NEO4J_URI},NEO4J_USER=${NEO4J_USER},NEO4J_PASSWORD=${NEO4J_PASSWORD}"

echo ""
echo "========================================"
echo "Deployment complete!"
echo "========================================"
echo ""
echo "Service URL: $(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')"
echo ""
echo "Next steps:"
echo "1. Test the /health endpoint"
echo "2. Configure Neo4j connection if not already done"
echo "3. Run data collection via /collect endpoint"
echo ""
