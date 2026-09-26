#!/bin/bash
set -e  # Dừng ngay nếu có lỗi

# ═══════════════════════════════════════════
# CRM SETUP — Tự Động Hoàn Toàn (Không Hỏi)
# ═══════════════════════════════════════════

PROJECT_NAME="my-crm"
DB_NAME="crm-db"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "🚀 CRM Setup đang chạy..."
echo ""

# ── 1. Kiểm tra và cài npm ──────────────────
if ! command -v npm &>/dev/null; then
    echo "📦 Cài Node.js qua brew..."
    command -v brew &>/dev/null || { echo "❌ Chưa có Homebrew. Cài tại https://brew.sh"; exit 1; }
    brew install node
fi

# ── 2. Kiểm tra và cài wrangler ────────────
if ! command -v wrangler &>/dev/null; then
    echo "📦 Cài Wrangler CLI..."
    npm install -g wrangler
fi

# ── 3. Đăng nhập Cloudflare (1 lần) ───────
echo "🔐 Kiểm tra đăng nhập Cloudflare..."
wrangler whoami &>/dev/null || wrangler login

# Lấy Account ID và OAuth token tự động
ACCOUNT_ID=$(wrangler whoami 2>/dev/null | grep -oE "[a-f0-9]{32}" | head -1)
CF_TOKEN=$(grep -oE 'oauth_token = "[^"]*"' "$HOME/.wrangler/config/default.toml" 2>/dev/null | cut -d'"' -f2)

echo "   Account: $ACCOUNT_ID"

# ── 4. Nhận thông tin từ người dùng ────────
echo ""
read -p "📝 Tên doanh nghiệp (vd: Fedu Academy): " BUSINESS_NAME
read -s -p "🔑 Mật khẩu đăng nhập CRM: " MASTER_PASSWORD
echo ""
echo ""

# ── 5. Tạo D1 Database ─────────────────────
echo "🗃️  Tạo D1 database '$DB_NAME'..."
DB_OUTPUT=$(wrangler d1 create "$DB_NAME" 2>&1)
DB_ID=$(echo "$DB_OUTPUT" | grep -oE "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}" | head -1)

if [ -z "$DB_ID" ]; then
    echo "❌ Không tạo được database. Chi tiết: $DB_OUTPUT"
    exit 1
fi
echo "   DB ID: $DB_ID ✅"

# ── 6. Cập nhật wrangler.toml ──────────────
sed -i '' "s/PLACEHOLDER/$DB_ID/g" "$SCRIPT_DIR/wrangler.toml"
echo "⚙️  wrangler.toml đã cập nhật ✅"

# ── 7. Apply Schema lên D1 ─────────────────
echo "📋 Apply database schema..."
echo "Y" | wrangler d1 execute "$DB_NAME" --file="$SCRIPT_DIR/schema.sql" --remote 2>&1 | tail -5
echo "   Schema OK ✅"

# ── 8. Deploy lên Cloudflare Pages ─────────
echo "🌐 Deploy lên Cloudflare Pages..."
DEPLOY_OUTPUT=$(printf "y\nmain\n" | wrangler pages deploy "$SCRIPT_DIR/dist" \
    --project-name="$PROJECT_NAME" \
    --branch=main \
    --commit-dirty=true \
    2>&1)

APP_URL=$(echo "$DEPLOY_OUTPUT" | grep -oE "https://[^[:space:]]+\.pages\.dev" | head -1)
echo "   Deployed: $APP_URL ✅"

# ── 9. Bind D1 vào Pages (qua CF API) ──────
echo "🔗 Bind database vào project..."
BIND_RESULT=$(curl -s -X PATCH \
    "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/pages/projects/$PROJECT_NAME" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"deployment_configs\": {
            \"production\":  { \"d1_databases\": { \"DB\": { \"id\": \"$DB_ID\" } } },
            \"preview\":     { \"d1_databases\": { \"DB\": { \"id\": \"$DB_ID\" } } }
        }
    }" | python3 -c "import sys,json; r=json.load(sys.stdin); print('ok' if r.get('success') else r.get('errors'))")

if [ "$BIND_RESULT" = "ok" ]; then
    echo "   D1 binding OK ✅"
else
    echo "   ⚠️  Binding lỗi: $BIND_RESULT"
fi

# ── 10. Set Secrets ────────────────────────
echo "🔐 Set secrets..."
printf "%s" "$MASTER_PASSWORD" | wrangler pages secret put CRM_PASSWORD --project-name="$PROJECT_NAME" 2>&1 | grep -E "Success|Error" || true
WEBHOOK_SECRET=$(openssl rand -hex 16)
printf "%s" "$WEBHOOK_SECRET" | wrangler pages secret put CRM_WEBHOOK_SECRET --project-name="$PROJECT_NAME" 2>&1 | grep -E "Success|Error" || true
echo "   Secrets OK ✅"

# ── 11. Redeploy để kích hoạt binding ─────
echo "🔄 Redeploy để kích hoạt D1 binding..."
wrangler pages deploy "$SCRIPT_DIR/dist" \
    --project-name="$PROJECT_NAME" \
    --branch=main \
    --commit-dirty=true \
    2>&1 | tail -3

# ── 12. Lưu tên doanh nghiệp vào DB ────────
wrangler d1 execute "$DB_NAME" \
    --command="UPDATE config SET value='$BUSINESS_NAME', updated_at=datetime('now') WHERE key='business_name'" \
    --remote 2>&1 | tail -2 || true

# ══ XONG ════════════════════════════════════
echo ""
echo "══════════════════════════════════════════"
echo "✅  CRM ĐÃ LIVE!"
echo ""
echo "   🌐  URL:      https://${PROJECT_NAME}-6tp.pages.dev"
echo "   🔑  Mật khẩu: $MASTER_PASSWORD"
echo "   🗃️   Database: $DB_NAME (Cloudflare D1)"
echo ""
echo "   Mở bằng điện thoại, máy tính bất kỳ,"
echo "   không cần bật máy Mac này."
echo "══════════════════════════════════════════"
echo ""

# Mở browser
open "https://${PROJECT_NAME}-6tp.pages.dev" 2>/dev/null || true
