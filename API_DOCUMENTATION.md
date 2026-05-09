# 📚 TÀI LIỆU HƯỚNG DẪN KẾT NỐI API

Tài liệu này hướng dẫn cách kết nối hệ thống của bạn với API của Bot Telegram để tự động hóa việc kiểm tra số dư, lấy danh sách sản phẩm và mua hàng.

---

## 🔐 1. XÁC THỰC (AUTHENTICATION)

Tất cả các yêu cầu API đều yêu cầu xác thực thông qua **API Key**. 
- Bạn có thể lấy API Key trực tiếp trên Bot Telegram (nút **📡 API Key**) hoặc yêu cầu Admin cấp.
- API Key phải được gửi kèm trong **Request Header** với tên: `X-API-Key`.

**Ví dụ Header:**
```http
X-API-Key: sk_e0aeb407abce5cd762f9b1c20666...
Content-Type: application/json
```

---

## 🚀 2. CÁC ENDPOINT CHUẨN (V1)

Dành cho các hệ thống tự code hoặc bot khác muốn tích hợp theo chuẩn riêng.

### 2.1 Kiểm tra số dư
- **Endpoint:** `/api/v1/balance`
- **Method:** `GET`
- **Phản hồi:**
```json
{
    "success": true,
    "balance": 1000000.0
}
```

### 2.2 Danh sách sản phẩm
- **Endpoint:** `/api/v1/products`
- **Method:** `GET`
- **Phản hồi:**
```json
{
    "success": true,
    "products": [
        {
            "id": 6,
            "name": "Tên sản phẩm",
            "price": 50000.0,
            "stock": 100,
            "description": "Mô tả sản phẩm"
        }
    ]
}
```

### 2.3 Mua hàng
- **Endpoint:** `/api/v1/buy`
- **Method:** `POST`
- **Body:** `{"product_id": 6, "quantity": 1}`
- **Phản hồi:**
```json
{
    "success": true,
    "product_name": "...",
    "credentials": ["tài khoản | mật khẩu"]
}
```

---

## 🔌 3. KẾT NỐI SHOPCLONEV7 (CMSNT)

Nếu bạn sử dụng mã nguồn ShopCloneV7 hoặc các bản tương tự của CMSNT, hãy sử dụng các đường dẫn sau để hệ thống tự động nhận diện.

- **Link Website nguồn:** `https://27ceb221cbae18.lhr.life`
- **Loại API:** Chọn `ShopCloneV7` hoặc `CMSNT`

### 3.1 Danh sách sản phẩm (CMSNT)
- **Endpoint:** `/api/cmsnt/v1/products`
- **Cấu trúc:** Trả về `"status": "success"` và bọc trong `"data"`.

### 3.2 Mua hàng (CMSNT)
- **Endpoint:** `/api/cmsnt/v1/buy`
- **Cấu trúc:** Trả về thông tin tài khoản trong mảng `data.products`.

---

## 🛠 4. HƯỚNG DẪN DÀNH CHO ĐỐI TÁC (CHỦ WEB SHOPCLONE)

**Bước 1:** Đăng nhập vào trang quản trị web ShopClone của bạn.
**Bước 2:** Truy cập menu **Sản phẩm** -> **Kết nối API**.
**Bước 3:** Nhấn **Thêm website API** và điền thông tin:
- **Link website:** `https://27ceb221cbae18.lhr.life`
- **API Key:** (Nhập Key được cấp)
- **Loại API:** `CMSNT`
**Bước 4:** Nhấn **Kết nối ngay**. 
- Hệ thống sẽ hiện số dư của bạn tại Bot.
- Bạn nhấn nút **Manager** để chọn danh mục và sản phẩm muốn đồng bộ về web của mình.

---

## ⚠️ LƯU Ý BẢO MẬT
- Tuyệt đối không chia sẻ API Key cho bất kỳ ai.
- Nếu nghi ngờ API Key bị lộ, hãy vào Bot Telegram và chọn **🔄 Cấp lại Key mới** để vô hiệu hóa key cũ.
- Đảm bảo số dư trong tài khoản Bot luôn đủ để các đơn hàng từ API không bị gián đoạn.
