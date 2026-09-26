@echo off
setlocal enabledelayedexpansion

echo Starting CRM setup...

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo npm not found. Please install Node.js manually.
    exit /b 1
)

where wrangler >nul 2>nul
if %errorlevel% neq 0 (
    echo wrangler not found. Installing via npm...
    npm install -g wrangler
)

echo Checking wrangler login...
wrangler whoami || wrangler login

set /p BUSINESS_NAME="Enter your business name (for CRM): "
set /p MASTER_PASSWORD="Enter master password for CRM: "

echo Creating D1 database 'crm-db'...
for /f "tokens=*" %%i in ('wrangler d1 create crm-db ^| findstr "database_id = "') do set DB_OUTPUT=%%i

if "%DB_OUTPUT%"=="" (
    echo Failed to extract database_id.
    exit /b 1
)

set DB_ID=%DB_OUTPUT:database_id = %
set DB_ID=%DB_ID:"=%
set DB_ID=%DB_ID: =%

echo Generating wrangler.toml...
powershell -Command "(gc wrangler.toml) -replace 'PLACEHOLDER', '%DB_ID%' | Out-File -encoding ASCII wrangler.toml"

echo Running migrations...
wrangler d1 execute crm-db --file=./schema.sql --remote

echo Deploying to Cloudflare Pages...
for /f "tokens=*" %%j in ('wrangler pages deploy ./dist --project-name=my-crm ^| findstr "https://.*\.pages\.dev"') do set APP_URL=%%j

echo Setting secrets...
echo %MASTER_PASSWORD% | wrangler pages secret put CRM_PASSWORD --project-name=my-crm
set WEBHOOK_SECRET=%RANDOM%%RANDOM%%RANDOM%
echo %WEBHOOK_SECRET% | wrangler pages secret put CRM_WEBHOOK_SECRET --project-name=my-crm

echo Setup Complete!
echo Your CRM is live at: %APP_URL%
echo Business Name: %BUSINESS_NAME%

start "" "%APP_URL%"
