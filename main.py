from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, Response
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
import os
from database.db import get_db, init_db
from database.models import Transaction, Order, User, Account, Product, Category, Voucher
from config import config
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from datetime import datetime

# Setup templates
templates = Jinja2Templates(directory="templates")

app = FastAPI(title="Telegram Sales Bot API")
# Mount static files if needed
# app.mount("/static", StaticFiles(directory="static"), name="static")

def get_current_admin(request: Request):
    admin_session = request.cookies.get("admin_session")
    if admin_session != config.WEB_ADMIN_PASSWORD: # Simple password-as-session for now
        return None
    return config.WEB_ADMIN_USERNAME

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/admin/dashboard")

# --- AUTH ROUTES ---
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...)):
    if username == config.WEB_ADMIN_USERNAME and password == config.WEB_ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="admin_session", value=password)
        return response
    return RedirectResponse(url="/login?error=1", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("admin_session")
    return response

# --- ADMIN ROUTES ---
@app.get("/admin")
async def admin_root():
    return RedirectResponse(url="/admin/dashboard")

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    
    # Stats calculation
    stats = {
        "revenue": db.query(func.sum(Order.amount)).filter(Order.status == "completed").scalar() or 0,
        "orders_count": db.query(Order).filter(Order.status == "completed").count(),
        "users_count": db.query(User).count(),
        "products_count": db.query(Product).count(),
    }
    
    # Recent orders (last 10)
    recent_orders = db.query(Order).order_by(Order.id.desc()).limit(10).all()
    
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "stats": stats, 
        "recent_orders": recent_orders,
        "active_page": "dashboard"
    })

# --- CATEGORY ROUTES ---
@app.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(request: Request, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    categories = db.query(Category).all()
    return templates.TemplateResponse(request=request, name="categories.html", context={"categories": categories, "active_page": "categories"})

@app.post("/admin/categories")
async def add_category(name: str = Form(...), description: str = Form(None), db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    cat = Category(name=name, description=description)
    db.add(cat)
    db.commit()
    return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/categories/{category_id}/edit")
async def edit_category(
    category_id: int, 
    name: str = Form(...), 
    description: str = Form(None), 
    db: Session = Depends(get_db), 
    admin = Depends(get_current_admin)
):
    if not admin: return RedirectResponse(url="/login")
    cat = db.query(Category).filter(Category.id == category_id).first()
    if cat:
        cat.name = name
        cat.description = description
        db.commit()
    return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/categories/{category_id}/toggle-visibility")
async def toggle_category_visibility(
    category_id: int, 
    db: Session = Depends(get_db), 
    admin = Depends(get_current_admin)
):
    if not admin: return RedirectResponse(url="/login")
    cat = db.query(Category).filter(Category.id == category_id).first()
    if cat:
        cat.is_hidden = not cat.is_hidden
        db.commit()
    return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)

# --- PRODUCT ROUTES ---
@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products(request: Request, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    products = db.query(Product).all()
    categories = db.query(Category).all()
    return templates.TemplateResponse(request=request, name="products.html", context={"products": products, "categories": categories, "active_page": "products"})

@app.post("/admin/products/{product_id}/edit")
async def edit_product(
    product_id: int, 
    request: Request, 
    name: str = Form(...), 
    category_id: int = Form(...), 
    price: float = Form(...), 
    description: str = Form(None),
    price_mode: str = Form("auto"),
    markup_percent: float = Form(10.0),
    manual_price: float = Form(None),
    db: Session = Depends(get_db), 
    admin = Depends(get_current_admin)
):
    if not admin: return RedirectResponse(url="/login")
    prod = db.query(Product).filter(Product.id == product_id).first()
    if prod:
        prod.name = name
        prod.category_id = category_id
        prod.price = price
        prod.description = description
        if prod.is_partner:
            prod.price_mode = price_mode
            prod.markup_percent = markup_percent
            prod.manual_price = manual_price
        db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/products/{product_id}/toggle-visibility")
async def toggle_product_visibility(product_id: int, request: Request, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    prod = db.query(Product).filter(Product.id == product_id).first()
    if prod:
        prod.is_hidden = not prod.is_hidden
        db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)

# --- VOUCHER MANAGEMENT ---
@app.get("/admin/vouchers")
async def admin_vouchers(request: Request, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    vouchers = db.query(Voucher).all()
    return templates.TemplateResponse(request=request, name="vouchers.html", context={"vouchers": vouchers, "active_page": "vouchers"})

@app.post("/admin/vouchers/add")
async def admin_add_voucher(request: Request, code: str = Form(...), discount: float = Form(...), db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    new_v = Voucher(code=code.upper(), discount_amount=discount)
    db.add(new_v)
    db.commit()
    return RedirectResponse(url="/admin/vouchers", status_code=303)

@app.get("/admin/vouchers/delete/{v_id}")
async def admin_delete_voucher(v_id: int, request: Request, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    v = db.query(Voucher).filter(Voucher.id == v_id).first()
    if v:
        db.delete(v)
        db.commit()
    return RedirectResponse(url="/admin/vouchers", status_code=303)

# --- BROADCAST ---
@app.get("/admin/broadcast")
async def admin_broadcast_ui(request: Request, admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="broadcast.html", context={"active_page": "broadcast"})

@app.post("/admin/broadcast")
async def admin_send_broadcast(request: Request, message: str = Form(...), db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    users = db.query(User).all()
    
    from aiogram import Bot
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    
    success = 0
    fail = 0
    for user in users:
        try:
            await bot.send_message(user.telegram_id, message, parse_mode="HTML")
            success += 1
        except Exception:
            fail += 1
            
    await bot.session.close()
    return templates.TemplateResponse(request=request, name="broadcast.html", context={"msg": f"Đã gửi: {success}, Thất bại: {fail}", "active_page": "broadcast"})

@app.post("/admin/products")
async def add_product(
    name: str = Form(...), 
    description: str = Form(None), 
    price: float = Form(...), 
    category_id: int = Form(...), 
    db: Session = Depends(get_db), 
    admin = Depends(get_current_admin)
):
    if not admin: return RedirectResponse(url="/login")
    prod = Product(name=name, description=description, price=price, category_id=category_id)
    db.add(prod)
    db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)

    db.add(prod)
    db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)

# --- ACCOUNT ROUTES ---
@app.get("/admin/accounts", response_class=HTMLResponse)
async def admin_accounts(request: Request, q: str = None, product_id: int = None, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    
    query = db.query(Account)
    if product_id:
        query = query.filter(Account.product_id == product_id)
    if q:
        query = query.filter(Account.credentials.like(f"%{q}%"))
    
    accounts = query.order_by(Account.id.desc()).limit(100).all()
    products = db.query(Product).all()
    
    return templates.TemplateResponse(request=request, name="accounts.html", context={
        "accounts": accounts, 
        "products": products, 
        "selected_product_id": product_id,
        "q": q,
        "active_page": "accounts"
    })

@app.post("/admin/accounts/upload")
async def upload_accounts(
    product_id: int = Form(...), 
    data: str = Form(...), 
    db: Session = Depends(get_db), 
    admin = Depends(get_current_admin)
):
    if not admin: return RedirectResponse(url="/login")
    
    unique_lines = list(set([line.strip() for line in data.split("\n") if line.strip()]))
    added_count = 0
    
    for line in unique_lines:
        exists = db.query(Account).filter(Account.product_id == product_id, Account.credentials == line).first()
        if not exists:
            acc = Account(product_id=product_id, credentials=line)
            db.add(acc)
            added_count += 1
    
    if added_count == 0:
        return RedirectResponse(url=f"/admin/accounts?product_id={product_id}", status_code=status.HTTP_303_SEE_OTHER)
        
    db.commit()
    
    # Notify updates
    try:
        from aiogram import Bot
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        product = db.query(Product).filter(Product.id == product_id).first()
        total_stock = db.query(Account).filter(Account.product_id == product_id, Account.is_sold == False).count()
        
        import html
        msg = (
            f"🔄 <b>CẬP NHẬT KHO HÀNG</b>\n\n"
            f"📦 Sản phẩm: <b>{html.escape(product.name)}</b>\n"
            f"💰 Giá bán: <b>{product.price:,.0f}đ</b>\n"
            f"✅ Thêm mới: <b>{added_count}</b>\n"
            f"🛒 Tổng tồn kho: <b>{total_stock}</b>\n\n"
            f"<i>Truy cập Menu bot để mua hàng ngay!</i>"
        )
        users = db.query(User).all()
        for user in users:
            try: await bot.send_message(user.telegram_id, msg, parse_mode="HTML")
            except: pass
        await bot.session.close()
    except Exception as e:
        logger.error(f"Error sending stock update notification: {e}")

    return RedirectResponse(url=f"/admin/accounts?product_id={product_id}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/accounts/clear")
async def clear_accounts(
    product_id: int = Form(...), 
    db: Session = Depends(get_db), 
    admin = Depends(get_current_admin)
):
    if not admin: return RedirectResponse(url="/login")
    
    # Delete only unsold accounts
    db.query(Account).filter(Account.product_id == product_id, Account.is_sold == False).delete()
    db.commit()
    
    return RedirectResponse(url=f"/admin/accounts?product_id={product_id}", status_code=status.HTTP_303_SEE_OTHER)

# --- ORDER ROUTES ---
@app.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders(request: Request, q: str = None, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    
    query = db.query(Order).join(Account, Order.account_id == Account.id, isouter=True)
    if q:
        search_pattern = f"%{q}%"
        if q.isdigit():
            query = query.filter(
                (Order.id == int(q)) |
                (Account.credentials.like(search_pattern))
            )
        else:
            # Search in account credentials
            query = query.filter(Account.credentials.like(search_pattern))

    orders = query.order_by(Order.id.desc()).all()
    return templates.TemplateResponse(request=request, name="orders.html", context={"orders": orders, "q": q, "active_page": "orders"})

# --- USER ROUTES ---
@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    if not admin: return RedirectResponse(url="/login")
    users = db.query(User).order_by(User.id.desc()).all()
    return templates.TemplateResponse(request=request, name="users.html", context={"users": users, "active_page": "users"})

@app.post("/admin/users/topup")
async def topup_user(
    user_id: int = Form(...), 
    amount: float = Form(...), 
    db: Session = Depends(get_db), 
    admin = Depends(get_current_admin)
):
    if not admin: return RedirectResponse(url="/login")
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.balance += amount
        db.commit()
        
        # Notify user via bot
        try:
            from aiogram import Bot
            bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
            msg = (
                f"💰 <b>THÔNG BÁO NẠP TIỀN</b>\n\n"
                f"Admin đã cộng cho bạn: <b>{amount:,.0f}đ</b>\n"
                f"Số dư hiện tại: <b>{user.balance:,.0f}đ</b>\n\n"
                f"<i>Cảm ơn bạn đã sử dụng dịch vụ!</i>"
            )
            await bot.send_message(user.telegram_id, msg, parse_mode="HTML")
            await bot.session.close()
        except Exception as e:
            logger.error(f"Error notifying topup: {e}")
            
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/webhook/sepay")
async def sepay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle SePay Webhook with Header Security
    """
    # 1. Verify Authorization Header
    auth_header = request.headers.get("Authorization")
    expected_auth = f"Apikey {config.SEPAY_WEBHOOK_KEY}"
    
    if config.SEPAY_WEBHOOK_KEY and auth_header != expected_auth:
        logger.warning(f"Unauthorized webhook attempt. Header: {auth_header}")
        return JSONResponse(content={"success": False, "message": "Unauthorized"}, status_code=401)
    
    try:
        data = await request.json()
        logger.info(f"Received SePay Webhook: {data}")
        
        content = data.get("content", "")
        amount = float(data.get("transferAmount", 0))
        
        # 1. Find transaction by reference code (Improved: Match if code is in content)
        # Fetch all pending transactions to check against the content
        pending_transactions = db.query(Transaction).filter(Transaction.status == "pending").all()
        transaction = None
        for pt in pending_transactions:
            if pt.reference_code.lower() in content.lower():
                transaction = pt
                break
        
        if not transaction:
            logger.warning(f"No pending transaction found matching content: {content}")
            return JSONResponse(content={"success": False, "message": "Transaction not found"}, status_code=200)

        # Update user balance
        user = db.query(User).filter(User.id == transaction.user_id).first()
        if not user:
            logger.error(f"User not found for transaction id: {transaction.id}")
            return JSONResponse(content={"success": False, "message": "User not found"}, status_code=200)

        user.balance += amount
        transaction.status = "completed"
        
        # Check if this transaction is linked to a direct purchase intent
        if transaction.product_id:
            logger.info(f"Direct purchase attempt for product_id: {transaction.product_id}")
            # Try to get an available account
            account = db.query(Account).filter(Account.product_id == transaction.product_id, Account.is_sold == False).first()
            if account:
                # Process the purchase
                user.balance -= transaction.amount
                account.is_sold = True
                account.sold_at = datetime.utcnow()
                
                order = Order(
                    user_id=user.id,
                    product_id=transaction.product_id,
                    account_id=account.id,
                    amount=transaction.amount,
                    status="completed"
                )
                db.add(order)
                db.commit()
                
                # Affiliate commission for direct purchase
                if user.referred_by_id:
                    referrer = db.query(User).filter(User.id == user.referred_by_id).first()
                    if referrer:
                        commission = transaction.amount * (config.AFFILIATE_PERCENT / 100)
                        if commission > 0:
                            referrer.balance += commission
                            db.commit()
                            # Notify referrer via bot (it will be used below)
                
                # Notify user via bot
                try:
                    from aiogram import Bot
                    # Use global config instance
                    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
                    import html
                    msg = (
                        "✅ <b>Thanh toán thành công!</b>\n\n"
                        f"📦 Đơn hàng cho: <b>{html.escape(account.product.name)}</b>\n"
                        f"🔑 Thông tin tài khoản:\n<code>{html.escape(account.credentials)}</code>\n\n"
                        "Cảm ơn bạn đã mua hàng!"
                    )
                    await bot.send_message(user.telegram_id, msg, parse_mode="HTML")
                    
                    # Notify referrer if applicable
                    if user.referred_by_id:
                        referrer = db.query(User).filter(User.id == user.referred_by_id).first()
                        if referrer:
                            commission = transaction.amount * (config.AFFILIATE_PERCENT / 100)
                            try:
                                await bot.send_message(
                                    referrer.telegram_id, 
                                    f"💰 <b>Hoa hồng mới!</b>\n\nBạn được cộng <b>{commission:,.0f}đ</b> từ đơn hàng của bạn bè.\nSố dư hiện tại: <b>{referrer.balance:,.0f}đ</b>", 
                                    parse_mode="HTML"
                                )
                            except: pass

                    # Delete QR message if exists
                    if transaction.qr_message_id:
                        try:
                            await bot.delete_message(user.telegram_id, transaction.qr_message_id)
                        except: pass
                    
                    # Low stock check
                    stock_count = db.query(Account).filter(Account.product_id == transaction.product_id, Account.is_sold == False).count()
                    if stock_count < 5:
                        for admin_id in config.ADMIN_IDS:
                            try:
                                await bot.send_message(admin_id, f"⚠️ <b>CẢNH BÁO TỒN KHO</b>\n\nSản phẩm: <b>{account.product.name}</b>\nChỉ còn: <b>{stock_count}</b> tài khoản!", parse_mode="HTML")
                            except: pass
                    
                    await bot.session.close()
                except Exception as e:
                    logger.error(f"Error sending direct buy notification: {e}")
            else:
                logger.warning(f"No stock available for direct purchase product_id: {transaction.product_id}")
                # Money is still added to user balance, they can buy later or buy something else
                try:
                    from aiogram import Bot
                    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
                    msg = (
                        "⚠️ <b>Thanh toán thành công!</b>\n\n"
                        "Tuy nhiên sản phẩm bạn định mua hiện đã <b>hết hàng</b>.\n"
                        f"Số tiền <b>{amount:,.0f}đ</b> đã được cộng vào số dư của bạn.\n"
                        f"💵 Số dư hiện tại: <b>{user.balance:,.0f}đ</b>\n\n"
                        "<i>Bạn có thể dùng số dư này để mua các sản phẩm khác hoặc chờ shop nhập thêm hàng nhé.</i>"
                    )
                    await bot.send_message(user.telegram_id, msg, parse_mode="HTML")
                    await bot.session.close()
                except Exception as e:
                    logger.error(f"Error sending out of stock notification: {e}")
        else:
            # Notify user for topup via bot
            try:
                from aiogram import Bot
                bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
                msg = (
                    "✅ <b>Nạp tiền thành công!</b>\n\n"
                    f"💰 Số tiền nạp: <b>{amount:,.0f}đ</b>\n"
                    f"💵 Số dư hiện tại: <b>{user.balance:,.0f}đ</b>\n\n"
                    "<i>Cảm ơn bạn đã sử dụng dịch vụ!</i>"
                )
                await bot.send_message(user.telegram_id, msg, parse_mode="HTML")
                await bot.session.close()
            except Exception as e:
                logger.error(f"Error sending topup notification: {e}")
        
        db.commit()
        
        return {"success": True, "message": "Balance updated and order processed if applicable"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)

# Add more API routes for Web Admin here
