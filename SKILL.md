---
name: crm-setup
description: >
  Kích hoạt khi có mantra CRM SETUP, CRM, LED SETUP, hoặc yêu cầu cài đặt hệ thống
  quản lý khách hàng: Tự động deploy CRM trên Cloudflare Pages + D1 (miễn phí),
  hỗ trợ nhập liệu từ Excel/Facebook, đồng bộ danh bạ iPhone (Mac) hoặc Telegram (Windows).
---

# CRM Setup — Hệ Thống Quản Lý Khách Hàng 1 Lệnh

## Kích Hoạt

| Mantra | Mô tả |
|---|---|
| `CRM SETUP` | Cài đặt mới từ đầu |
| `CRM IMPORT` | Import dữ liệu từ Excel/CSV |
| `CRM SYNC` | Đồng bộ contacts (Mac→iPhone) hoặc Telegram (Windows) |
| `CRM HUB` | Mở trang web CRM |
| `LED [thông tin khách]` | Thêm lead qua AI chat |

## Quy Trình Cài Đặt (CRM SETUP)

### Bước 1: Kiểm tra môi trường
```bash
# Kiểm tra npm và wrangler
which npm || echo "Cần cài Node.js"
which wrangler || npm install -g wrangler
wrangler whoami || wrangler login
```

### Bước 2: Clone template và deploy
```bash
CRM_DIR="$HOME/Documents/CODE/my-crm"
git clone https://github.com/vietndj/crm-template.git "$CRM_DIR"
cd "$CRM_DIR"
chmod +x setup.sh
./setup.sh
```

### Bước 3: AI tự động hoàn thành
- Tạo D1 database
- Apply schema SQL
- Deploy frontend + API lên Cloudflare Pages
- Set master password
- Bung Chrome mở CRM live

## Kiến Trúc

### Stack
- **Frontend**: Alpine.js + Tailwind CSS (1 file HTML, không cần build)
- **Backend**: Cloudflare Pages Functions (serverless API)
- **Database**: Cloudflare D1 (SQLite cloud, 5GB free)
- **Auth**: Master password → Session token (24h)

### API Endpoints
| Method | Path | Mô tả |
|---|---|---|
| POST | `/api/auth` | Đăng nhập |
| GET | `/api/leads` | Danh sách leads (pagination, search, filter) |
| POST | `/api/leads` | Tạo lead mới |
| GET | `/api/leads/:id` | Chi tiết lead + interactions |
| PUT | `/api/leads/:id` | Cập nhật lead |
| DELETE | `/api/leads/:id` | Xóa lead (soft delete) |
| GET/POST | `/api/interactions` | Lịch sử tương tác |
| POST | `/api/import` | Import batch từ Excel/CSV |
| GET | `/api/export` | Export CSV |
| GET | `/api/stats` | Dashboard thống kê |
| GET/PUT | `/api/config` | Cấu hình hệ thống |
| POST | `/api/webhook/facebook` | Facebook Lead Ads webhook |

## Thêm Lead Qua AI

Khi người dùng gõ `LED [thông tin]`, AI thực hiện:

1. **Parse thông tin**: Trích xuất name, phone, email, industry, intent
2. **Chuẩn hóa SĐT**: Bỏ khoảng trắng, +84 → 0
3. **Gọi API**: POST /api/leads
4. **Ghi interaction**: POST /api/interactions (note đầu tiên)
5. **Platform sync**:
   - macOS: Chạy `sync/mac/sync_contacts.py` → đẩy vào Apple Contacts → iCloud → iPhone
   - Windows: Gửi notification qua Telegram Bot
6. **Phản hồi**: Xác nhận đã thêm + link CRM

### Ví dụ
```
User: LED Nguyễn Văn A, 0901234567, bán quần áo, hỏi khóa offline tháng 10

AI:
→ POST /api/leads {name: "Nguyễn Văn A", phone: "0901234567", industry: "Fashion", source: "ai"}
→ POST /api/interactions {lead_id: "xxx", type: "note", content: "Hỏi khóa offline tháng 10"}
→ [Mac] sync_contacts.py → Apple Contacts
→ ✅ Đã thêm lead Nguyễn Văn A. Mở CRM: https://my-crm.pages.dev
```

## Import Dữ Liệu (CRM IMPORT)

### Từ Facebook — 3 cách không ma sát (KHÔNG cần tạo Facebook App)

**Cách 1 — Copy-paste đoạn chat (Dễ nhất, dùng ngay):**
```
User: copy đoạn chat từ Messenger rồi dán vào AI:
"Chào shop, mình Tuấn 0901234567, hỏi khóa offline tháng 10 còn chỗ không ạ?"
Sau đó nói: "Lưu khách này lại"

AI tự động:
→ Parse: name="Tuấn", phone="0901234567", note="Hỏi khóa offline tháng 10"
→ POST /api/leads {source: "facebook"}
→ ✅ Đã lưu khách Tuấn
```

**Cách 2 — Chụp ảnh inbox Messenger rồi gửi cho AI (Siêu lười):**
```
User: chụp màn hình hộp thư Messenger → gửi ảnh vào Antigravity
Nói: "Lưu hết khách trong ảnh này"

AI dùng Vision đọc ảnh:
→ Nhặt tên + SĐT từng người nhắn tin
→ Batch POST /api/import
→ ✅ Đã lưu 5 khách từ ảnh inbox
```

**Cách 3 — Tải CSV từ Facebook Leads Center (Cho Lead Ads, 100 khách/lần):**
```
Bước 1: Meta Business Suite → Leads Center → Tải xuống file CSV
Bước 2: User nói: "CRM IMPORT file leads_facebook.csv"

AI:
1. Đọc CSV, map cột name/phone/email
2. POST /api/import { rows: [...], source: "facebook_csv" }
3. ✅ Import 150 leads từ Facebook Lead Ads, bỏ qua 3 trùng SĐT
```

> Không cần tạo Facebook App, không cần developer, không cần webhook setup.
> Facebook Webhook (tự động 100%) chỉ bật khi user yêu cầu ở giai đoạn nâng cao.

### Từ Excel/CSV (qua AI)
```
User: CRM IMPORT file leads.xlsx

AI:
1. Đọc file bằng Python (openpyxl/csv)
2. Map columns → schema fields
3. POST /api/import { rows: [...], source: "excel" }
4. Báo: "✅ Import 150 leads, bỏ qua 3 trùng SĐT"
```

### Từ Web UI
1. Mở CRM → tab "Nhập liệu"
2. Kéo thả file CSV/Excel
3. Map cột → trường dữ liệu
4. Preview → Xác nhận import

## Đồng Bộ Platform (CRM SYNC)

### macOS → iPhone
```bash
# Đồng bộ contacts CRM → Apple Contacts (tự sync iCloud → iPhone)
python3 ~/Documents/CODE/my-crm/sync/mac/sync_contacts.py \
  --api-url https://my-crm.pages.dev \
  --token YOUR_TOKEN

# Đồng bộ lịch sử cuộc gọi → CRM interactions
python3 ~/Documents/CODE/my-crm/sync/mac/sync_calls.py \
  --api-url https://my-crm.pages.dev \
  --token YOUR_TOKEN
```

**Tự động hóa**: AI có thể thiết lập cron job hoặc launchd để chạy mỗi 30 phút.

### Windows → Telegram
```bash
# Chạy Telegram bot listener
python3 ~/Documents/CODE/my-crm/sync/win/sync_telegram.py \
  --api-url https://my-crm.pages.dev \
  --token YOUR_TOKEN \
  --bot-token YOUR_BOT_TOKEN
```

**Telegram Bot commands:**
- `/leads` — Xem danh sách leads mới
- `/add Tên, SĐT, Ngành` — Thêm lead nhanh
- `/note [id] Nội dung` — Ghi chú cho lead
- `/search keyword` — Tìm kiếm
- `/status [id] [trạng thái]` — Cập nhật status

## Quản Lý Thủ Công (Khi AI Lỗi)

1. Mở `https://my-crm.pages.dev` trên bất kỳ trình duyệt
2. Đăng nhập bằng master password
3. Thao tác CRUD trực tiếp trên web:
   - Thêm/sửa/xóa lead
   - Ghi chú, đánh dấu trạng thái
   - Import/Export dữ liệu
   - Cấu hình hệ thống

## Yêu Cầu

- Node.js (npm) — để cài wrangler CLI
- Tài khoản Cloudflare miễn phí — để deploy
- [Tùy chọn Mac] Full Disk Access — để đọc Call History
- [Tùy chọn Win] Telegram Bot token — tạo qua @BotFather

## Thư Mục Dự Án

```
my-crm/
├── dist/index.html          # Frontend SPA
├── functions/api/            # Backend API (10 endpoints)
├── sync/mac/                 # macOS sync scripts
├── sync/win/                 # Windows Telegram sync
├── schema.sql                # Database schema
├── setup.sh / setup.bat      # Installer scripts
└── wrangler.toml             # Cloudflare config
```
