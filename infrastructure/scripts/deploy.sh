#!/usr/bin/env bash
# ============================================================================
# Impressions Generator — Infrastructure Deployment Script
# Healthcare application (HIPAA) deployed to Azure via Bicep
# ============================================================================

set -euo pipefail

# --- Default parameter values ---
ENVIRONMENT=""
LOCATION="swedencentral"
PROJECT_NAME="impgen"

# --- Parse arguments ---
usage() {
    echo "Usage: $0 -e <dev|staging|prod> [-l <location>] [-p <projectName>]"
    echo ""
    echo "  -e  Environment (required): dev, staging, or prod"
    echo "  -l  Azure region (default: swedencentral)"
    echo "  -p  Project name (default: impgen)"
    exit 1
}

while getopts "e:l:p:h" opt; do
    case $opt in
        e) ENVIRONMENT="$OPTARG" ;;
        l) LOCATION="$OPTARG" ;;
        p) PROJECT_NAME="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

if [[ -z "$ENVIRONMENT" ]]; then
    echo "ERROR: Environment is required."
    usage
fi

if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "prod" ]]; then
    echo "ERROR: Environment must be dev, staging, or prod."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo " Impressions Generator - Infrastructure Deploy"
echo " Environment: $ENVIRONMENT"
echo " Location:    $LOCATION"
echo " Project:     $PROJECT_NAME"
echo "============================================"

# --- Check Azure CLI login ---
echo ""
echo "Checking Azure CLI login status..."
if ! az account show > /dev/null 2>&1; then
    echo "ERROR: Not logged into Azure CLI. Run 'az login' first."
    exit 1
fi

ACCOUNT_NAME=$(az account show --query "user.name" -o tsv)
SUBSCRIPTION=$(az account show --query "name" -o tsv)
echo "Logged in as: $ACCOUNT_NAME"
echo "Subscription: $SUBSCRIPTION"

# --- Deploy Bicep template at subscription scope ---
echo ""
echo "Starting deployment..."

DEPLOYMENT_NAME="${PROJECT_NAME}-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
TEMPLATE_FILE="${INFRA_DIR}/main.bicep"

if ! RESULT=$(az deployment sub create \
    --name "$DEPLOYMENT_NAME" \
    --location "$LOCATION" \
    --template-file "$TEMPLATE_FILE" \
    --parameters \
        environmentName="$ENVIRONMENT" \
        location="$LOCATION" \
        projectName="$PROJECT_NAME" \
    --output json 2>&1); then
    echo ""
    echo "ERROR: Deployment failed."
    echo "$RESULT"
    exit 1
fi

STATE=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['provisioningState'])" 2>/dev/null || echo "Unknown")

if [[ "$STATE" == "Succeeded" ]]; then
    echo ""
    echo "============================================"
    echo " Deployment Succeeded!"
    echo "============================================"
    echo ""
    echo "Deployed Resource URLs:"
    echo "  Resource Group:    $(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['resourceGroupName']['value'])")"
    echo "  Container App:     $(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['containerAppUrl']['value'])")"
    echo "  Static Web App:    $(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['staticWebAppUrl']['value'])")"
    echo "  Cosmos DB:         $(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['cosmosEndpoint']['value'])")"
    echo "  OpenAI:            $(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['openaiEndpoint']['value'])")"
    echo "  AI Search:         $(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['searchEndpoint']['value'])")"
    echo "  Key Vault:         $(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['keyVaultUri']['value'])")"
    echo "  Storage Account:   $(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['storageAccountName']['value'])")"
    echo "  App Insights:      (connected)"
else
    echo ""
    echo "ERROR: Deployment ended with state: $STATE"
    exit 1
fi
