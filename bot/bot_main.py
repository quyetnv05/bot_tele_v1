import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, URLInputFile
import time
from sqlalchemy import func
from sqlalchemy.orm import Session
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from database.db import SessionLocal
from database.models import User, Category, Product, Transaction, Order, Account, Voucher
from bot.keyboards import get_main_menu, get_categories_keyboard, get_products_keyboard, get_product_detail_keyboard, get_direct_payment_keyboard, get_welcome_inline_keyboard
from bot.partner_api import partner_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from aiogram import BaseMiddleware

class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if config.MAINTENANCE_MODE:
            from aiogram.types import Message, CallbackQuery
            user_id = event.from_user.id
            if user_id not in config.ADMIN_IDS:
                if isinstance(event, Message):
                    await event.answer("🛠️ <b>Hệ thống đang bảo trì</b>\n\nVui lòng quay lại sau ít phút. Xin lỗi vì sự bất tiện này!", parse_mode="HTML")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Hệ thống đang bảo trì. Vui lòng quay lại sau!", show_alert=True)
                return
        return await handler(event, data)

from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError

# Increase timeout to 120 seconds to handle slow network connections
session = AiohttpSession(timeout=120)
bot = Bot(token=config.TELEGRAM_BOT_TOKEN, session=session)
dp = Dispatcher()
dp.message.outer_middleware(MaintenanceMiddleware())
dp.callback_query.outer_middleware(MaintenanceMiddleware())

async def set_commands():
    commands = [
        types.BotCommand(command="start", description="Bắt đầu / Menu chính"),
        types.BotCommand(command="shop", description="Xem sản phẩm"),
        types.BotCommand(command="profile", description="Thông tin cá nhân")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("partner_balance"))
async def partner_balance_handler(message: Message):
    if message.from_user.id not in config.ADMIN_IDS: return
    try:
        res = await partner_api.get_balance()
        if res and res.get("success"):
            await message.answer(f"💰 Số dư đối tác: <b>{res.get('balance', 0):,.0f}đ</b>", parse_mode="HTML")
        else:
            await message.answer("⚠️ Không lấy được số dư. Vui lòng kiểm tra lại API Key.")
    except Exception as e:
        await message.answer(f"Lỗi: {e}")

@dp.message(Command("sync_partner"))
async def sync_partner_handler(message: Message):
    if message.from_user.id not in config.ADMIN_IDS: return
    await message.answer("🔄 Đang đồng bộ danh mục sản phẩm từ đối tác...")
    try:
        res = await partner_api.get_products(force=True)
        if not res or not res.get("success"):
            await message.answer("⚠️ Lỗi đồng bộ. Vui lòng kiểm tra API Key.")
            return
            
        db: Session = SessionLocal()
        default_cat = db.query(Category).first()
        if not default_cat:
            default_cat = Category(name="Khác", description="Danh mục chung")
            db.add(default_cat)
            db.commit()
            db.refresh(default_cat)
            
        count = 0
        for p in res.get("products", []):
            existing = db.query(Product).filter(Product.partner_id == p["id"]).first()
            if not existing:
                new_p = Product(
                    category_id=default_cat.id,
                    name=p["name"],
                    description=p.get("description", ""),
                    price=p["price"],
                    is_partner=True,
                    partner_id=p["id"],
                    price_mode="auto",
                    markup_percent=10.0
                )
                db.add(new_p)
                count += 1
            else:
                existing.name = p["name"]
                existing.description = p.get("description", "")
        db.commit()
        db.close()
        await message.answer(f"✅ Đã đồng bộ thành công! Thêm mới {count} sản phẩm.")
    except Exception as e:
        await message.answer(f"Lỗi: {e}")

async def send_welcome_message(message: Message, user: User, db: Session, edit=False):
    # Prepare Stats
    tier_name, _, total_spent = get_user_tier(db, user)
    total_orders = db.query(func.count(Order.id)).filter(Order.user_id == user.id, Order.status == "completed").scalar() or 0
    total_global_sold = db.query(func.count(Account.id)).filter(Account.is_sold == True).scalar() or 0
    
    # Time Greeting
    hour = datetime.now().hour
    if 5 <= hour < 12: greeting = "Chào buổi sáng"
    elif 12 <= hour < 18: greeting = "Chào buổi chiều"
    else: greeting = "Chào buổi tối"
    
    welcome_text = (
        f"🌤 <b>{greeting}, {user.full_name}</b>\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n\n"
        f"🎖 <b>Cấp bậc:</b> {tier_name}\n"
        f"💰 Số dư: <b>{user.balance:,.0f}đ</b>\n"
        f"📥 Tổng chi tiêu: <b>{total_spent:,.0f}đ</b>\n"
        f"🛒 Tổng đơn hàng: <b>{total_orders}</b>\n"
        f"🏰 Tổng đã bán: <b>{total_global_sold}</b> tài khoản\n\n"
        "Chọn chức năng bên dưới:"
    )
    
    if edit:
        try:
            await message.edit_text(welcome_text, reply_markup=get_welcome_inline_keyboard(), parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Failed to edit welcome message: {e}")
    else:
        try:
            await message.answer(welcome_text, reply_markup=get_welcome_inline_keyboard(), parse_mode="HTML")
        except TelegramNetworkError as e:
            logger.error(f"Network error while sending welcome message: {e}")
            # Optional: Notify user or retry once? For now, just log and handle
            await asyncio.sleep(2) # Brief wait
            try:
                await message.answer(welcome_text, reply_markup=get_welcome_inline_keyboard(), parse_mode="HTML")
            except: pass
        except Exception as e:
            logger.error(f"Error in send_welcome_message: {e}")

@dp.message(Command("start"))
async def start_handler(message: Message):
    with SessionLocal() as db:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            # Check deep link for referral
            args = message.text.split()
            referred_by_id = None
            if len(args) > 1:
                ref_code = args[1]
                referrer = db.query(User).filter(User.referral_code == ref_code).first()
                if referrer:
                    referred_by_id = referrer.id
            
            import random
            import string
            new_ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
                referral_code=new_ref_code,
                referred_by_id=referred_by_id
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        await send_welcome_message(message, user, db)

@dp.message(F.text == "🛒 Mua Tài Khoản")
@dp.message(Command("shop"))
async def shop_handler(message: Message):
    with SessionLocal() as db:
        user_id = message.chat.id
        categories = db.query(Category).filter(Category.is_hidden == False).all()
        
        if not categories:
            await message.answer("Hiện tại shop chưa có danh mục sản phẩm nào.")
            return
            
        await message.answer("Vui lòng chọn danh mục bạn quan tâm:", reply_markup=get_categories_keyboard(categories))

@dp.callback_query(F.data.startswith("cat_"))
async def category_callback(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    with SessionLocal() as db:
        products = db.query(Product).filter(Product.category_id == cat_id, Product.is_hidden == False).all()
        
        if not products:
            await callback.answer("Danh mục này hiện chưa có sản phẩm.")
            return
            
        await callback.message.edit_text("Các sản phẩm trong danh mục này:", reply_markup=get_products_keyboard(products))

@dp.callback_query(F.data.startswith("prod_"))
async def product_callback(callback: CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    with SessionLocal() as db:
        product = db.query(Product).filter(Product.id == prod_id, Product.is_hidden == False).first()
        available_count = db.query(Account).filter(Account.product_id == prod_id, Account.is_sold == False).count()
        
        if not product:
            await callback.answer("Sản phẩm không tồn tại.")
            return
            
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        tier_name, discount, _ = get_user_tier(db, user)
        
        # Handle Partner Product Logic - Zero Latency Access
        original_price = product.price
        if product.is_partner:
            partner_data = partner_api.products_cache
            if partner_data and "products" in partner_data:
                p_info = next((p for p in partner_data["products"] if p["id"] == product.partner_id), None)
                if p_info:
                    available_count = p_info.get("stock", 0)
                    base_price = p_info.get("price", 0)
                    if product.price_mode == "auto":
                        original_price = base_price * (1 + (product.markup_percent or 0) / 100)
                    else:
                        original_price = product.manual_price if product.manual_price else base_price
                
        vip_price = original_price * (1 - discount / 100)
        
        product_text = (
            f"📦 <b>{product.name}</b>\n\n"
            f"📝 Mô tả: {product.description or 'Chưa có mô tả'}\n"
            f"💰 Giá gốc: <s>{original_price:,.0f}đ</s>\n"
            f"🌟 Giá {tier_name}: <b>{vip_price:,.0f}đ</b> (Giảm {discount}%)\n"
            f" Tồn kho: <b>{available_count}</b>\n\n"
            "<i>Nhấn nút bên dưới để tiến hành mua hàng.</i>"
        )
        await callback.message.edit_text(
            product_text, 
            reply_markup=get_product_detail_keyboard(product.id), 
            parse_mode="HTML"
        )

@dp.callback_query(F.data == "back_to_prods")
async def back_to_prods(callback: CallbackQuery):
    await shop_handler(callback.message)

@dp.callback_query(F.data == "back_to_cats")
async def back_to_cats_callback(callback: CallbackQuery):
    db: Session = SessionLocal()
    categories = db.query(Category).filter(Category.is_hidden == False).all()
    if len(categories) <= 1:
        # If 0 or 1 category, go back to main menu
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        await send_welcome_message(callback.message, user, db, edit=True)
        await callback.answer()
    else:
        await show_categories_callback(callback)
    db.close()

@dp.callback_query(F.data.startswith("direct_pay_"))
async def direct_pay_callback(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    db: Session = SessionLocal()
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        await callback.answer("Sản phẩm không tồn tại.")
        db.close()
        return
        
    # 1. Check stock & calculate price
    original_price = product.price
    available_count = 0
    
    if product.is_partner:
        # Check stock from partner API cache
        partner_data = partner_api.products_cache
        if not partner_data or "products" not in partner_data:
            db.close()
            await callback.answer("⚠️ Đang cập nhật dữ liệu, vui lòng đợi 1 giây...", show_alert=True)
            return
            
        p_info = next((p for p in partner_data["products"] if p["id"] == product.partner_id), None)
        if not p_info or p_info.get("stock", 0) <= 0:
            db.close()
            await callback.answer("⚠️ Xin lỗi, sản phẩm này hiện đã hết hàng!", show_alert=True)
            return
        
        available_count = p_info.get("stock", 0)
        base_price = p_info.get("price", 0)
        if product.price_mode == "auto":
            original_price = base_price * (1 + (product.markup_percent or 0) / 100)
        else:
            original_price = product.manual_price if product.manual_price else base_price
    else:
        # Check local stock
        available_count = db.query(Account).filter(Account.product_id == product_id, Account.is_sold == False).count()
        if available_count == 0:
            await callback.answer("Sản phẩm này hiện đang hết hàng.")
            db.close()
            return

    # 2. Get database user & Calculate VIP price
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if not user:
        await callback.answer("Vui lòng gõ /start để khởi tạo tài khoản.")
        db.close()
        return

    tier_name, discount, _ = get_user_tier(db, user)
    vip_price = original_price * (1 - discount / 100)

    # 3. Create a unique reference code for this specific purchase
    ref_code = f"BUY{product_id}U{callback.from_user.id}S{int(time.time()) % 10000}"
    
    # Create a pending transaction for this product
    transaction = Transaction(
        user_id=user.id,
        product_id=product_id,
        amount=vip_price,
        payment_method="SePay",
        reference_code=ref_code,
        status="pending"
    )
    db.add(transaction)
    db.commit()

    qr_url = f"https://qr.sepay.vn/img?bank=MBBank&acc=6124022005&template=compact&amount={int(vip_price)}&des={ref_code}"
    
    pay_text = (
        "🔗 <b>THANH TOÁN QR TRỰC TIẾP</b>\n\n"
        f"📦 Sản phẩm: <b>{product.name}</b>\n"
        f"👤 Hạng: <b>{tier_name}</b> (Giảm {discount}%)\n"
        f"💰 Tổng tiền: <b>{vip_price:,.0f}đ</b>\n"
        f"🔢 Nội dung chuyển khoản: <code>{ref_code}</code>\n\n"
        "ℹ️ <i>Vui lòng quét mã QR hoặc chuyển đúng số tiền và nội dung bên dưới. "
        "Hệ thống sẽ tự động giao hàng sau khi nhận được tiền.</i>"
    )
    
    sent_msg = await callback.message.answer_photo(
        photo=URLInputFile(qr_url),
        caption=pay_text,
        reply_markup=get_direct_payment_keyboard(),
        parse_mode="HTML"
    )
    
    transaction.qr_message_id = sent_msg.message_id
    db.commit()
    await callback.answer()
    db.close()

@dp.callback_query(F.data == "check_payment")
async def check_payment_callback(callback: CallbackQuery):
    await callback.answer("Hệ thống đang kiểm tra... Vui lòng đợi trong giây lát.")
    await callback.message.answer("Nếu bạn đã chuyển khoản, vui lòng đợi 1-3 phút để hệ thống xử lý tự động.")

@dp.callback_query(F.data.startswith("use_voucher_"))
async def use_voucher_callback(callback: CallbackQuery):
    prod_id = int(callback.data.split("_")[2])
    await callback.message.answer(f"Vui lòng nhập mã Voucher của bạn:\n(Gửi tin nhắn có nội dung: <code>CODE_{prod_id}_YOURCODE</code>)\n\nVD: <code>CODE_{prod_id}_GIAM20K</code>", parse_mode="HTML")
    await callback.answer()

@dp.message(F.text.startswith("CODE_"))
async def apply_voucher_handler(message: Message):
    parts = message.text.split("_")
    if len(parts) < 3: return
    
    prod_id = int(parts[1])
    code = parts[2].upper()
    
    db: Session = SessionLocal()
    voucher = db.query(Voucher).filter(Voucher.code == code, Voucher.is_active == True).first()
    product = db.query(Product).filter(Product.id == prod_id).first()
    
    if not voucher:
        await message.answer("❌ Mã Voucher không tồn tại hoặc đã hết hạn.")
        db.close()
        return
        
    new_price = max(0, product.price - voucher.discount_amount)
    await message.answer(
        f"🎟️ <b>Voucher được áp dụng!</b>\n\n"
        f"📦 Sản phẩm: {product.name}\n"
        f"💰 Giá gốc: {product.price:,.0f}đ\n"
        f"🎁 Giảm giá: {voucher.discount_amount:,.0f}đ\n"
        f"🔥 Giá mới: <b>{new_price:,.0f}đ</b>\n\n"
        f"<i>Vui lòng nạp đủ {new_price:,.0f}đ để mua hàng.</i>",
        reply_markup=get_product_detail_keyboard(product.id), # Show buy button again
        parse_mode="HTML"
    )
    db.close()

def get_user_tier(db: Session, user: User):
    total_spent = db.query(func.sum(Order.amount)).filter(Order.user_id == user.id, Order.status == "completed").scalar() or 0
    if total_spent >= 10000000: return "💎 Kim Cương", 15, total_spent
    if total_spent >= 2000000: return "🥇 Vàng", 10, total_spent
    if total_spent >= 500000: return "🥈 Bạc", 5, total_spent
    return "🥉 Thành Viên", 0, total_spent

def process_commission(db: Session, user: User, amount: float):
    if user.referred_by_id:
        referrer = db.query(User).filter(User.id == user.referred_by_id).first()
        if referrer:
            commission = amount * (config.AFFILIATE_PERCENT / 100)
            if commission > 0:
                referrer.balance += commission
                logger.info(f"Commission of {commission} credited to {referrer.username} for purchase by {user.username}")
                # Notify referrer
                asyncio.create_task(bot.send_message(
                    referrer.telegram_id, 
                    f"💰 <b>Hoa hồng mới!</b>\n\nBạn được cộng <b>{commission:,.0f}đ</b> từ đơn hàng của bạn bè.\nSố dư hiện tại: <b>{referrer.balance:,.0f}đ</b>", 
                    parse_mode="HTML"
                ))

def check_low_stock(prod_id: int):
    db: Session = SessionLocal()
    product = db.query(Product).filter(Product.id == prod_id).first()
    if not product:
        db.close()
        return
        
    stock = 0
    if product.is_partner:
        # Check stock from partner API cache
        partner_data = partner_api.products_cache
        if partner_data and "products" in partner_data:
            p_info = next((p for p in partner_data["products"] if p["id"] == product.partner_id), None)
            if p_info:
                stock = p_info.get("stock", 0)
    else:
        stock = db.query(Account).filter(Account.product_id == prod_id, Account.is_sold == False).count()
        
    if stock < 5:
        # Notify admins
        for admin_id in config.ADMIN_IDS:
             asyncio.create_task(bot.send_message(admin_id, f"⚠️ <b>CẢNH BÁO TỒN KHO</b>\n\nSản phẩm: <b>{product.name}</b>\nChỉ còn: <b>{stock}</b> tài khoản!", parse_mode="HTML"))
    db.close()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_handler(callback: CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    db: Session = SessionLocal()
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    product = db.query(Product).filter(Product.id == prod_id).first()
    
    # 1. Check stock & calculate price
    original_price = product.price
    
    if product.is_partner:
        # Check stock from partner API cache
        partner_data = partner_api.products_cache
        if not partner_data or "products" not in partner_data:
            db.close()
            await callback.answer("⚠️ Dữ liệu đang được đồng bộ, vui lòng thử lại sau 1 giây!", show_alert=True)
            return
            
        p_info = next((p for p in partner_data["products"] if p["id"] == product.partner_id), None)
        if not p_info or p_info.get("stock", 0) <= 0:
            db.close()
            await callback.answer("⚠️ Xin lỗi, sản phẩm này hiện đã hết hàng!", show_alert=True)
            return
            
        base_price = p_info.get("price", 0)
        if product.price_mode == "auto":
            original_price = base_price * (1 + (product.markup_percent or 0) / 100)
        else:
            original_price = product.manual_price if product.manual_price else base_price
    else:
        # Check local stock
        account = db.query(Account).filter(Account.product_id == prod_id, Account.is_sold == False).first()
        if not account:
            db.close()
            await callback.answer("⚠️ Xin lỗi, sản phẩm này hiện đã hết hàng!", show_alert=True)
            return
        
    # 2. Check balance
    tier_name, discount, _ = get_user_tier(db, user)
    vip_price = original_price * (1 - discount / 100)
    
    if user.balance < vip_price:
        needed = vip_price - user.balance
        db.close()
        await callback.message.answer(
            f"❌ Số dư không đủ!\n\n"
            f"💰 Bạn còn thiếu: <b>{needed:,.0f}đ</b>\n"
            f"Vui lòng nhấn 'Nạp Tiền' để tiếp tục.",
            parse_mode="HTML"
        )
        return

    # 3. Process order
    try:
        # Atomic transaction
        user.balance -= vip_price
        db.commit() # Deduct balance first
        
        credentials_list = []
        partner_order_code = None
        
        if product.is_partner:
            # Call partner API to buy
            buy_res = await partner_api.buy_product(product.partner_id, 1)
            if not buy_res or not buy_res.get("success"):
                # Refund
                user.balance += vip_price
                db.commit()
                err_msg = buy_res.get("error", "Lỗi không xác định") if buy_res else "Lỗi kết nối đối tác"
                await callback.answer(f"⚠️ Mua thất bại: {err_msg}", show_alert=True)
                return
                
            order_data = buy_res.get("order", {})
            credentials_list = order_data.get("accounts", [])
            partner_order_code = order_data.get("order_code")
            
            # Create a dummy account record to link to the order, or just store the credentials in the message
            # For simplicity, we can just save it as a sold account
            account = Account(
                product_id=product.id,
                credentials="\\n".join(credentials_list),
                is_sold=True,
                sold_at=datetime.now()
            )
            db.add(account)
            db.commit()
            db.refresh(account)
        else:
            account.is_sold = True
            account.sold_at = datetime.now()
            credentials_list = [account.credentials]
        
        order = Order(
            user_id=user.id,
            product_id=product.id,
            account_id=account.id,
            amount=vip_price,
            partner_order_code=partner_order_code,
            status="completed"
        )
        db.add(order)
        db.commit()
        
        # Affiliate commission
        process_commission(db, user, product.price)
        db.commit()
        
        import html
        await callback.message.answer(
            f"✅ <b>Mua hàng thành công!</b>\n\n"
            f"🏷️ Mã đơn hàng: <b>#{order.id}</b>\n"
            f"📦 Sản phẩm: <b>{html.escape(product.name)}</b>\n"
            f"🔑 Thông tin tài khoản:\n"
            f"<code>{html.escape(chr(10).join(credentials_list))}</code>\n\n"
            f"<i>Cảm ơn bạn đã ủng hộ shop!</i>",
            parse_mode="HTML"
        )
        await callback.answer("Giao hàng thành công!")
        check_low_stock(product.id)
    except Exception as e:
        db.rollback()
        logger.error(f"Purchase error: {e}")
        await callback.answer("Có lỗi xảy ra, vui lòng thử lại sau.", show_alert=True)
    finally:
        db.close()

@dp.message(F.text == "💰 Nạp Tiền")
async def deposit_handler(message: Message):
    db: Session = SessionLocal()
    user = db.query(User).filter(User.telegram_id == message.chat.id).first()
    
    # Generate reference code
    import random
    import string
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    ref_code = f"SHOP{user.id}{random_str}"
    
    # Save pending transaction
    new_trans = Transaction(
        user_id=user.id,
        amount=0,
        payment_method="SePay",
        reference_code=ref_code,
        status="pending"
    )
    db.add(new_trans)
    db.commit()
    db.close()
    
    qr_url = f"https://qr.sepay.vn/img?bank=MBBank&acc=6124022005&template=compact&amount=0&des={ref_code}"
    
    deposit_text = (
        "💳 <b>Nạp tiền tự động qua Ngân Hàng</b>\n\n"
        "Sử dụng App Ngân hàng quét mã QR dưới đây hoặc chuyển khoản theo thông tin:\n"
        "🏦 Ngân hàng: <b>MB Bank</b>\n"
        "👤 Chủ TK: <b>NGUYEN VAN QUYET</b>\n"
        "🔢 Số TK: <code>6124022005</code>\n"
        f"📝 Nội dung chuyển khoản: <code>{ref_code}</code>\n\n"
        "⚠️ <b>Lưu ý:</b> Phải chuyển đúng nội dung để được cộng tiền tự động sau 1-3 phút."
    )
    
    await message.answer_photo(
        photo=URLInputFile(qr_url),
        caption=deposit_text,
        parse_mode="HTML"
    )

@dp.message(F.text == "📜 Lịch Sử Nạp")
async def deposit_history_handler(message: Message):
    db: Session = SessionLocal()
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    trans = db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.status == "completed").order_by(Transaction.created_at.desc()).limit(10).all()
    
    if not trans:
        await message.answer("Bạn chưa có giao dịch nạp tiền nào.")
        db.close()
        return
        
    text = "📜 <b>Lịch sử 10 giao dịch nạp tiền gần nhất:</b>\n\n"
    for t in trans:
        text += f"➕ {t.amount:,.0f}đ - {t.payment_method}\n"
        text += f"⏰ {t.created_at.strftime('%d/%m/%Y %H:%M')}\n"
        text += f"📝 Nội dung: <code>{t.reference_code}</code>\n\n"
        
    await message.answer(text, parse_mode="HTML")
    db.close()

@dp.message(F.text == "📜 Lịch Sử Mua")
async def history_handler(message: Message):
    db: Session = SessionLocal()
    user = db.query(User).filter(User.telegram_id == message.chat.id).first()
    orders = db.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(10).all()
    
    if not orders:
        await message.answer("Bạn chưa có giao dịch nào.")
        db.close()
        return
        
    text = "📜 <b>Lịch sử 10 đơn hàng gần nhất:</b>\n\n"
    for o in orders:
        text += f"🔹 #{o.id} - {o.product.name} - {o.amount:,.0f}đ\n"
        text += f"⏰ {o.created_at.strftime('%d/%m/%Y %H:%M')}\n"
        text += f"🔑 <code>{o.account.credentials}</code>\n\n"
        
    await message.answer(text, parse_mode="HTML")
    db.close()

@dp.message(F.text == "👤 Cá Nhân")
@dp.message(Command("profile"))
async def profile_handler(message: Message):
    db: Session = SessionLocal()
    user = db.query(User).filter(User.telegram_id == message.chat.id).first()
    
    if not user:
        await message.answer("Vui lòng gõ /start để khởi tạo tài khoản.")
        db.close()
        return
    
    tier_name, discount, total_spent = get_user_tier(db, user)
    
    text = (
        f"👤 <b>Thông tin cá nhân</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"👤 Hạng: <b>{tier_name}</b> (Giảm {discount}%)\n"
        f"💰 Số dư: <b>{user.balance:,.0f}đ</b>\n"
        f"📊 Tổng chi tiêu: <b>{total_spent:,.0f}đ</b>\n"
        f"📅 Ngày tham gia: {user.created_at.strftime('%d/%m/%Y')}"
    )
    await message.answer(text, parse_mode="HTML")
    db.close()

@dp.message(F.text == "📞 Hỗ Trợ")
async def support_handler(message: Message):
    text = (
        "📞 <b>Hỗ trợ khách hàng</b>\n\n"
        "Nếu gặp vấn đề trong quá trình mua hàng hoặc nạp tiền, vui lòng liên hệ Admin:\n\n"
        f"👤 Telegram: @{config.SUPPORT_USERNAME}\n"
        f"🔗 Link: https://t.me/{config.SUPPORT_USERNAME}\n\n"
        "<i>Chúng tôi sẽ phản hồi sớm nhất có thể!</i>"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "ℹ️ Hướng Dẫn")
async def help_handler(message: Message):
    text = (
        "ℹ️ <b>Hướng dẫn sử dụng Bot</b>\n\n"
        "1. <b>Mua Tài Khoản</b>: Chọn danh mục -> Chọn sản phẩm -> Chọn hình thức thanh toán (Số dư hoặc QR trực tiếp).\n"
        "2. <b>Nạp Tiền</b>: Lấy mã QR nạp tiền, chuyển đúng nội dung. Tiền sẽ được cộng tự động.\n"
        "3. <b>Lịch sử</b>: Kiểm tra đơn hàng đã mua hoặc các giao dịch nạp tiền.\n"
        "4. <b>Voucher</b>: Nhập mã giảm giá trước khi thanh toán để tiết kiệm thêm.\n\n"
        "🌟 Chúc bạn có trải nghiệm mua sắm tuyệt vời!"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "🤝 Cộng Tác Viên")
async def affiliate_handler(message: Message):
    db: Session = SessionLocal()
    user = db.query(User).filter(User.telegram_id == message.chat.id).first()
    
    if not user:
        await message.answer("Vui lòng gõ /start để bắt đầu.")
        db.close()
        return
        
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user.referral_code}"
    
    # Count referrals
    ref_count = db.query(func.count(User.id)).filter(User.referred_by_id == user.id).scalar()
    
    text = (
        "🤝 <b>Chương trình Cộng tác viên</b>\n\n"
        "Kiếm tiền cực dễ bằng cách mời bạn bè sử dụng Bot!\n\n"
        f"💰 Hoa hồng: <b>{config.AFFILIATE_PERCENT}%</b> trên mỗi đơn hàng.\n"
        f"👥 Bạn đã mời: <b>{ref_count}</b> thành viên.\n\n"
        "🔗 <b>Link giới thiệu của bạn:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "<i>Gửi link này cho bạn bè, khi họ mua hàng bạn sẽ nhận được tiền cộng trực tiếp vào số dư!</i>"
    )
    await message.answer(text, parse_mode="HTML")
    db.close()

# --- WELCOME INLINE CALLBACKS ---
@dp.callback_query(F.data == "show_categories")
async def show_categories_callback(callback: CallbackQuery):
    db: Session = SessionLocal()
    categories = db.query(Category).filter(Category.is_hidden == False).all()
    
    if not categories:
        await callback.answer("Hiện tại shop chưa có danh mục sản phẩm nào.", show_alert=True)
        db.close()
        return
        
    if len(categories) == 1:
        # If only one category, show products directly to save a click
        cat = categories[0]
        products = db.query(Product).filter(Product.category_id == cat.id, Product.is_hidden == False).all()
        if not products:
            await callback.answer("Danh mục này hiện chưa có sản phẩm.", show_alert=True)
        else:
            await callback.message.edit_text(
                f"📂 Danh mục: <b>{cat.name}</b>\n\n<i>Vui lòng chọn sản phẩm bạn muốn mua:</i>", 
                reply_markup=get_products_keyboard(products), 
                parse_mode="HTML"
            )
    else:
        # If multiple categories, show category list by editing the message
        await callback.message.edit_text(
            "🛒 <b>Danh mục sản phẩm</b>\n\nVui lòng chọn danh mục bạn quan tâm:", 
            reply_markup=get_categories_keyboard(categories),
            parse_mode="HTML"
        )
    
    await callback.answer()
    db.close()

@dp.callback_query(F.data == "show_deposit")
async def show_deposit_callback(callback: CallbackQuery):
    await deposit_handler(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "show_history")
async def show_history_callback(callback: CallbackQuery):
    await history_handler(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "show_support")
async def show_support_callback(callback: CallbackQuery):
    await support_handler(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "show_api_key")
async def show_api_key_callback(callback: CallbackQuery):
    await callback.message.answer("📡 <b>API Key</b>\n\nTính năng này đang được phát triển. Vui lòng quay lại sau!", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "show_language")
async def show_language_callback(callback: CallbackQuery):
    await callback.message.answer("🌐 <b>Ngôn ngữ</b>\n\nHiện tại hệ thống chỉ hỗ trợ Tiếng Việt.", parse_mode="HTML")
    await callback.answer()

async def broadcast_restock_notification(restocked_products):
    if not restocked_products: return
    
    import html
    text = "🔔 <b>THÔNG BÁO VỪA CẬP NHẬT KHO HÀNG</b>\n\n"
    for p in restocked_products:
        text += f"📦 <b>{html.escape(p['name'])}</b>\n"
        text += f"✅ Vừa về thêm: <b>{p['added_count']}</b>\n"
        text += f"💰 Tồn kho hiện tại: <b>{p['current_stock']}</b>\n\n"
    
    text += "🛒 <i>Gõ /shop để mua ngay!</i>"
    
    with SessionLocal() as db:
        users = db.query(User).all()
        logger.info(f"Broadcasting restock to {len(users)} users...")
        for user in users:
            try:
                await bot.send_message(user.telegram_id, text, parse_mode="HTML")
                await asyncio.sleep(0.05) # Rate limit protection (20 msgs/sec)
            except Exception as e:
                logger.debug(f"Failed to send broadcast to {user.telegram_id}: {e}")

async def partner_prefetch_task():
    logger.info("Partner Prefetch Task Started")
    first_run = True
    while True:
        try:
            res = await partner_api.get_products(force=True)
            if res and res.get("success"):
                logger.info("Partner products cache refreshed")
                # Only notify if not the first run to prevent startup spam
                if not first_run:
                    restocked = res.get("restocked", [])
                    if restocked:
                        logger.info(f"Detected {len(restocked)} restocked products. Triggering broadcast...")
                        asyncio.create_task(broadcast_restock_notification(restocked))
                
                first_run = False
        except Exception as e:
            logger.error(f"Partner prefetch error: {e}")
        await asyncio.sleep(15)

async def sepay_polling_task():
    import aiohttp
    import html
    
    logger.info("SePay Polling Task Started")
    
    while True:
        await asyncio.sleep(10)
        if not config.SEPAY_API_KEY:
            logger.error("No SEPAY_API_KEY found. Polling stopped.")
            continue
            
        db: Session = SessionLocal()
        try:
            pending_transactions = db.query(Transaction).filter(Transaction.status == "pending").all()
            if not pending_transactions:
                continue
            
            logger.info(f"Found {len(pending_transactions)} pending transactions. Calling SePay API...")
            headers = {"Authorization": f"Bearer {config.SEPAY_API_KEY}"}
            async with aiohttp.ClientSession() as session:
                async with session.get("https://my.sepay.vn/userapi/transactions/list", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        transactions_api = data.get("transactions", [])
                    else:
                        error_text = await response.text()
                        logger.error(f"SePay API Error {response.status}: {error_text}. Please check your SEPAY_API_KEY.")
                        continue
                        
                    for pt in pending_transactions:
                        for api_tx in transactions_api:
                            content = api_tx.get("transaction_content", "")
                            if not content: continue
                            content = content.lower()
                            
                            ref_code = pt.reference_code.lower()
                            if ref_code in content:
                                logger.info(f"MATCH FOUND: {ref_code} in {content}")
                                amount = float(api_tx.get("amount_in", 0))
                                user = db.query(User).filter(User.id == pt.user_id).first()
                                if not user: continue
                                
                                user.balance += amount
                                pt.status = "completed"
                                
                                if pt.product_id:
                                    product = db.query(Product).filter(Product.id == pt.product_id).first()
                                    delivered = False
                                    order = None
                                    account_creds = ""

                                    if product and product.is_partner:
                                        # Call partner API to buy
                                        res = await partner_api.buy_product(product.partner_id, 1)
                                        if res and res.get("success"):
                                            order_data = res.get("order", {})
                                            accounts = order_data.get("accounts", [])
                                            account_creds = "\n".join(accounts) if accounts else "Không có dữ liệu tài khoản"
                                            
                                            # Deduct balance (price already paid via QR)
                                            user.balance -= pt.amount
                                            
                                            # Create placeholder account for order record
                                            new_acc = Account(
                                                product_id=product.id,
                                                credentials=account_creds,
                                                is_sold=True,
                                                sold_at=datetime.now()
                                            )
                                            db.add(new_acc)
                                            db.flush()
                                            
                                            order = Order(
                                                user_id=user.id,
                                                product_id=product.id,
                                                account_id=new_acc.id,
                                                amount=pt.amount,
                                                status="completed"
                                            )
                                            db.add(order)
                                            db.commit()
                                            delivered = True
                                    else:
                                        account = db.query(Account).filter(Account.product_id == pt.product_id, Account.is_sold == False).first()
                                        if account:
                                            user.balance -= pt.amount
                                            account.is_sold = True
                                            account.sold_at = datetime.now()
                                            account_creds = account.credentials
                                            
                                            order = Order(
                                                user_id=user.id,
                                                product_id=pt.product_id,
                                                account_id=account.id,
                                                amount=pt.amount,
                                                status="completed"
                                            )
                                            db.add(order)
                                            db.commit()
                                            delivered = True

                                    if delivered:
                                        # Commission logic
                                        if user.referred_by_id:
                                            referrer = db.query(User).filter(User.id == user.referred_by_id).first()
                                            if referrer:
                                                commission = pt.amount * (config.AFFILIATE_PERCENT / 100)
                                                if commission > 0:
                                                    referrer.balance += commission
                                                    db.commit()
                                                    try: await bot.send_message(referrer.telegram_id, f"💰 <b>Hoa hồng mới!</b>\n\nBạn được cộng <b>{commission:,.0f}đ</b> từ đơn hàng của bạn bè.", parse_mode="HTML")
                                                    except: pass

                                        msg = (
                                            "✅ <b>Thanh toán thành công!</b>\n\n"
                                            f"🏷️ Mã đơn hàng: <b>#{order.id if order else 'N/A'}</b>\n"
                                            f"📦 Sản phẩm: <b>{html.escape(product.name)}</b>\n"
                                            f"🔑 Thông tin tài khoản:\n<code>{html.escape(account_creds)}</code>\n\n"
                                            "Cảm ơn bạn đã mua hàng!"
                                        )
                                        try: await bot.send_message(user.telegram_id, msg, parse_mode="HTML")
                                        except: pass
                                        
                                        if pt.qr_message_id:
                                            try: await bot.delete_message(user.telegram_id, pt.qr_message_id)
                                            except: pass
                                    else:
                                        msg = (
                                            "⚠️ <b>Thanh toán thành công!</b>\n\n"
                                            "Tuy nhiên sản phẩm bạn định mua hiện đã <b>hết hàng</b>.\n"
                                            f"Số tiền <b>{amount:,.0f}đ</b> đã được cộng vào số dư của bạn.\n"
                                            f"💵 Số dư hiện tại: <b>{user.balance:,.0f}đ</b>\n\n"
                                            "<i>Bạn có thể dùng số dư này để mua các sản phẩm khác hoặc chờ shop nhập thêm hàng nhé.</i>"
                                        )
                                        try: await bot.send_message(user.telegram_id, msg, parse_mode="HTML")
                                        except: pass
                                else:
                                    msg = (
                                        "✅ <b>Nạp tiền thành công!</b>\n\n"
                                        f"💰 Số tiền nạp: <b>{amount:,.0f}đ</b>\n"
                                        f"💵 Số dư hiện tại: <b>{user.balance:,.0f}đ</b>\n\n"
                                        "<i>Cảm ơn bạn đã sử dụng dịch vụ!</i>"
                                    )
                                    try: await bot.send_message(user.telegram_id, msg, parse_mode="HTML")
                                    except: pass
                                
                                db.commit()
                                break
        except Exception as e:
            logger.error(f"SePay Polling Error: {e}")
        finally:
            db.close()

background_tasks = set()

async def main():
    print("Starting bot...")
    await set_commands()
    
    # Start background tasks
    prefetch_task = asyncio.create_task(partner_prefetch_task())
    polling_task = asyncio.create_task(sepay_polling_task())
    
    background_tasks.add(prefetch_task)
    background_tasks.add(polling_task)
    
    prefetch_task.add_done_callback(background_tasks.discard)
    polling_task.add_done_callback(background_tasks.discard)
    
    try:
        await dp.start_polling(bot)
    finally:
        await partner_api.close()

if __name__ == "__main__":
    asyncio.run(main())
