---
name: crm-setup
description: >
  Kích hoạt khi có mantra CRM SETUP hoặc CRM. Khởi chạy CRM Zero-Setup với Python và SQLite tại localhost, không cần cài đặt phức tạp.
---

# CRM Setup — Hệ Thống Quản Lý Khách Hàng Zero-Setup

## Kích Hoạt

| Mantra | Mô tả |
|---|---|
| `CRM SETUP` hoặc `CRM` | Khởi chạy CRM Local |
| `CRM CLOUD` | Hướng dẫn deploy lên mây với Cloudflare D1 |

## Quy Trình Khởi Chạy Mới (Zero-Setup)

Với cách tiếp cận mới, người dùng KHÔNG cần Cloudflare, KHÔNG cần Firebase, KHÔNG cần Node.js. Chỉ cần Python 3 (có sẵn trên Mac/Linux/Windows).

### Bước 1: Tải về
Clone repository (hoặc tải file ZIP):
```bash
CRM_DIR="$HOME/Documents/CODE/my-crm"
git clone https://github.com/vietndj/crm-template.git "$CRM_DIR"
cd "$CRM_DIR"
```

### Bước 2: Chạy
```bash
python3 crm.py
```
Hệ thống sẽ tự động:
- Tạo database SQLite `crm.db` ngay tại thư mục
- Bật built-in HTTP server ở port 8899
- Phục vụ toàn bộ API (RESTful) và frontend (Alpine.js + Tailwind)
- Mở tự động trình duyệt vào `http://localhost:8899`

> Master password mặc định là `1234` (đổi được qua UI).

## Flow Sử Dụng

### 1. Import Dữ Liệu Dễ Dàng
- **Copy-paste chat**: Copy đoạn chat từ inbox, dán cho AI nhờ AI phân tích và POST `/api/leads`.
- **Chụp ảnh inbox**: Chụp màn hình gửi AI, AI đọc Vision và gọi API lưu danh sách khách.
- **Kéo thả file**: Dùng tính năng import CSV ngay trên Web UI tại mục Nhập liệu.

### 2. Hệ Thống Mềm Dẻo & Tùy Chỉnh
Hệ thống quản lý khách hàng cho phép tinh chỉnh sâu không cần code:
- **Tùy biến Pipeline**: Cập nhật các bước pipeline (Mới -> Đã liên hệ -> Chốt...) tùy theo luồng kinh doanh (bảng `pipeline_stages`).
- **Custom fields**: Dữ liệu linh hoạt, có thể thêm trường dữ liệu động dưới dạng JSON (`custom_fields`).
- **Cấu hình chung**: Thay đổi Tên business, tiền tệ, múi giờ thông qua bảng `config` và `GET/PUT /api/config`.

### 3. Khi Nào Lên Cloud? (CRM CLOUD)
CHỈ KHI user chủ động hỏi `CRM CLOUD` hoặc `Muốn dùng trên mây`, AI mới cung cấp hướng dẫn deploy:
1. Yêu cầu cài Node.js + Wrangler.
2. Tạo D1 database trên Cloudflare.
3. Apply `schema.sql` vào D1.
4. Deploy thư mục `dist/` cùng `functions/` (nếu có) lên Cloudflare Pages.

*(Bình thường mọi thao tác đều diễn ra tại Local bằng Python + SQLite)*

## API Endpoints (Local crm.py)

| Method | Path | Mô tả |
|---|---|---|
| POST | `/api/auth` | Đăng nhập bằng master password |
| GET | `/api/leads` | List leads (hỗ trợ search, filter) |
| POST | `/api/leads` | Tạo lead mới |
| GET | `/api/leads/<id>` | Chi tiết 1 lead |
| PUT | `/api/leads/<id>` | Cập nhật lead |
| DELETE | `/api/leads/<id>` | Xóa lead (soft delete) |
| POST | `/api/import` | Import hàng loạt leads |
| GET | `/api/stats` | Lấy số liệu tổng quan (dashboard) |
| POST | `/api/interactions` | Thêm lịch sử tương tác |
| GET | `/api/interactions?lead_id=x` | Lấy lịch sử theo lead |
| GET/PUT | `/api/config` | Cập nhật/lấy config hệ thống |
