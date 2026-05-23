#!/bin/bash
# Deploy Graph RAG Resume Agent to Vercel

set -e

echo "========================================"
echo "Graph RAG Resume Agent - Vercel Deploy"
echo "========================================"

# Check if vercel.json exists
if [ ! -f "vercel.json" ]; then
    echo "Error: vercel.json not found!"
    echo "Creating default vercel.json..."
    cat > vercel.json << 'EOF'
{
  "version": 2,
  "builds": [
    {
      "src": "requirements.txt",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
EOF
fi

# Login to Vercel (if not already logged in)
echo ""
echo "Step 1: Checking Vercel authentication..."
if ! npx vercel whoami 2>/dev/null; then
    echo "Not logged in. Starting authentication..."
    npx vercel login
fi

echo "Logged in as: $(npx vercel whoami)"

# Deploy
echo ""
echo "Step 2: Deploying to Vercel..."
echo "This will create a new deployment..."

npx vercel deploy --prod

echo ""
echo "========================================"
echo "Deployment complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Set environment variables in Vercel dashboard"
echo "2. Add Neo4j connection details"
echo "3. Test the /health endpoint"
echo ""
