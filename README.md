# Telegram Sales Bot - Digital Product Shop

Một hệ thống Bot Telegram bán hàng tự động tích hợp API đối tác và thanh toán QR SePay, kèm theo trang quản trị Web Dashboard.

## 🚀 Tính năng

- **Bot Telegram (aiogram 3.x):**
  - Mua hàng tự động 24/7.
  - Tích hợp API đối tác (Reseller API) để đồng bộ sản phẩm và kho hàng.
  - Thông báo đẩy (Broadcast) khi kho hàng được cập nhật.
  - Hệ thống cấp bậc thành viên (VIP tiers) với chiết khấu tự động.
  - Hệ thống Affiliate (Hoa hồng giới thiệu).
  - Sử dụng Voucher giảm giá.
  - Nạp tiền tự động qua QR SePay (MB Bank).

- **Web Admin Dashboard (FastAPI):**
  - Quản lý danh mục và sản phẩm.
  - Quản lý kho hàng (Account).
  - Quản lý người dùng và số dư.
  - Thống kê đơn hàng và giao dịch.
  - Gửi tin nhắn Broadcast cho tất cả người dùng bot.
  - Cấu hình lợi nhuận (markup) cho sản phẩm đối tác.

## 🛠 Cài đặt

### 1. Clone dự án
```bash
git clone https://github.com/quyetnv05/bot_tele_v1.git
cd bot_tele_v1
```

### 2. Cài đặt môi trường
Khuyên dùng Python 3.10 trở lên.
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Cấu hình .env
Tạo file `.env` từ `.env.example` và điền đầy đủ thông tin:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_IDS=your_telegram_id
DATABASE_URL=sqlite:///./sales_bot.db
SEPAY_API_KEY=your_sepay_api_key
SEPAY_WEBHOOK_KEY=your_webhook_key
WEB_ADMIN_USERNAME=admin
WEB_ADMIN_PASSWORD=your_password
BASE_URL=http://localhost:8000
SUPPORT_USERNAME=your_username
PARTNER_API_KEY=your_partner_api_key
```

### 4. Khởi tạo cơ sở dữ liệu
```bash
python migrate.py
```

## 🚀 Khởi chạy

### Chạy Bot Telegram
```bash
python bot/bot_main.py
```

### Chạy Web Dashboard
```bash
python main.py
```
Trang quản trị mặc định tại: `http://localhost:8000/admin/login`

## 📝 Câu lệnh Bot

- `/start`: Khởi động bot và xem menu chính.
- `/shop`: Xem danh mục sản phẩm.
- `/profile`: Xem thông tin cá nhân và số dư.
- `/sync_partner` (Admin): Đồng bộ sản phẩm từ đối tác.
- `/partner_balance` (Admin): Kiểm tra số dư bên đối tác.

## 🤝 Đóng góp
Nếu bạn có bất kỳ đóng góp nào, vui lòng tạo **Pull Request** hoặc mở **Issue**.

## 📄 Giấy phép
Dự án được phát hành dưới giấy phép MIT.
