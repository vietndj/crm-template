#!/bin/bash

echo "Starting CRM setup..."

# Check npm
if ! command -v npm &> /dev/null; then
    echo "npm not found. Installing via brew..."
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install Node.js manually."
        exit 1
    fi
    brew install node
fi

# Check wrangler
if ! command -v wrangler &> /dev/null; then
    echo "wrangler not found. Installing via npm..."
    npm install -g wrangler
fi

echo "Checking wrangler login..."
wrangler whoami || wrangler login

read -p "Enter your business name (for CRM): " BUSINESS_NAME
read -p "Enter master password for CRM: " MASTER_PASSWORD

echo "Creating D1 database 'crm-db'..."
DB_OUTPUT=$(wrangler d1 create crm-db)
echo "$DB_OUTPUT"

DB_ID=$(echo "$DB_OUTPUT" | grep -oE "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}")

if [ -z "$DB_ID" ]; then
    echo "Failed to extract database_id."
    exit 1
fi

echo "Generating wrangler.toml..."
sed "s/PLACEHOLDER/$DB_ID/g" wrangler.toml > wrangler.toml.tmp && mv wrangler.toml.tmp wrangler.toml

echo "Running migrations..."
wrangler d1 execute crm-db --file=./schema.sql --remote

echo "Deploying to Cloudflare Pages..."
DEPLOY_OUTPUT=$(wrangler pages deploy ./dist --project-name=my-crm)
echo "$DEPLOY_OUTPUT"

APP_URL=$(echo "$DEPLOY_OUTPUT" | grep -oE "https://[^[:space:]]+\.pages\.dev")

echo "Setting secrets..."
echo "$MASTER_PASSWORD" | wrangler pages secret put CRM_PASSWORD --project-name=my-crm
WEBHOOK_SECRET=$(openssl rand -hex 16)
echo "$WEBHOOK_SECRET" | wrangler pages secret put CRM_WEBHOOK_SECRET --project-name=my-crm

echo "Setup Complete!"
echo "Your CRM is live at: $APP_URL"
echo "Business Name: $BUSINESS_NAME"

open "$APP_URL"
