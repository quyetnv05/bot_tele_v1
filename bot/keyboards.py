from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    keyboard = [
        [KeyboardButton(text="🛒 Mua Tài Khoản"), KeyboardButton(text="💰 Nạp Tiền")],
        [KeyboardButton(text="📜 Lịch Sử Mua"), KeyboardButton(text="📜 Lịch Sử Nạp")],
        [KeyboardButton(text="👤 Cá Nhân"), KeyboardButton(text="🤝 Cộng Tác Viên")],
        [KeyboardButton(text="📞 Hỗ Trợ"), KeyboardButton(text="ℹ️ Hướng Dẫn")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard, 
        resize_keyboard=True
    )

def get_welcome_inline_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🛒 Danh sách sản phẩm", callback_data="show_categories"), 
         InlineKeyboardButton(text="📡 API Key", callback_data="show_api_key")],
        [InlineKeyboardButton(text="🏦 Nạp số dư", callback_data="show_deposit"), 
         InlineKeyboardButton(text="🌍 Lịch sử mua hàng", callback_data="show_history")],
        [InlineKeyboardButton(text="🌐 Ngôn ngữ", callback_data="show_language"), 
         InlineKeyboardButton(text="🗣 Liên hệ hỗ trợ", callback_data="show_support")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_categories_keyboard(categories):
    builder = InlineKeyboardMarkup(inline_keyboard=[])
    for cat in categories:
        builder.inline_keyboard.append([InlineKeyboardButton(text=cat.name, callback_data=f"cat_{cat.id}")])
    return builder

def get_products_keyboard(products):
    builder = InlineKeyboardMarkup(inline_keyboard=[])
    for prod in products:
        builder.inline_keyboard.append([InlineKeyboardButton(text=f"{prod.name} - {prod.price}đ", callback_data=f"prod_{prod.id}")])
    builder.inline_keyboard.append([InlineKeyboardButton(text="🔙 Quay Lại", callback_data="back_to_cats")])
    return builder

def get_product_detail_keyboard(product_id):
    buttons = [
        [InlineKeyboardButton(text="✅ Mua Ngay", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton(text="💳 Thanh Toán QR Trực Tiếp", callback_data=f"direct_pay_{product_id}")],
        [InlineKeyboardButton(text="🎟️ Nhập Voucher", callback_data=f"use_voucher_{product_id}")],
        [InlineKeyboardButton(text="⬅️ Quay Lại", callback_data="back_to_prods")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_direct_payment_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔄 Kiểm tra thanh toán", callback_data="check_payment")],
        [InlineKeyboardButton(text="❌ Hủy", callback_data="back_to_prods")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_purchase_keyboard(product_id):
    keyboard = [
        [InlineKeyboardButton(text="✅ Mua Ngay", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton(text="🔙 Quay Lại", callback_data="back_to_prods")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_keyboard(reference_code):
    keyboard = [
        [InlineKeyboardButton(text="🔄 Kiểm Tra Thanh Toán", callback_data=f"check_pay_{reference_code}")],
        [InlineKeyboardButton(text="❌ Hủy Giao Dịch", callback_data=f"cancel_pay_{reference_code}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
