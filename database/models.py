from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    balance = Column(Float, default=0.0)
    is_admin = Column(Boolean, default=False)
    referral_code = Column(String, unique=True, nullable=True)
    referred_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    orders = relationship("Order", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(Text, nullable=True)
    is_hidden = Column(Boolean, default=False)

    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    name = Column(String)
    description = Column(Text, nullable=True)
    price = Column(Float)
    image_url = Column(String, nullable=True)
    is_hidden = Column(Boolean, default=False)
    
    # Reseller fields
    is_partner = Column(Boolean, default=False)
    partner_id = Column(String, nullable=True)
    price_mode = Column(String, default="auto") # "auto" or "manual"
    markup_percent = Column(Float, default=10.0)
    manual_price = Column(Float, nullable=True)

    category = relationship("Category", back_populates="products")
    accounts = relationship("Account", back_populates="product")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    credentials = Column(Text)  # Store username|password or code
    is_sold = Column(Boolean, default=False)
    sold_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="accounts")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    amount = Column(Float)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=True)
    status = Column(String, default="pending")  # pending, completed, cancelled
    partner_order_code = Column(String, nullable=True) # Reseller order code
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="orders")
    product = relationship("Product")
    account = relationship("Account")
    voucher = relationship("Voucher")

class Voucher(Base):
    __tablename__ = "vouchers"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, index=True)
    discount_amount = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True) # For direct buy
    amount = Column(Float)
    payment_method = Column(String)  # SePay
    reference_code = Column(String, unique=True) # Payment content for SePay
    status = Column(String, default="pending")
    completed_at = Column(DateTime, nullable=True)
    qr_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="transactions")
