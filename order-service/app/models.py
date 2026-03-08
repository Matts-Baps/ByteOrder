import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String, nullable=False, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    kitchen_id = Column(String, nullable=False, index=True)
    order_number = Column(String, unique=True, nullable=False)
    customer_name = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, in_progress, ready, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    menu_item_id = Column(Integer, nullable=False)
    menu_item_name = Column(String, nullable=False)
    order = relationship("Order", back_populates="items")
    ingredients = relationship("OrderItemIngredient", back_populates="order_item", cascade="all, delete-orphan")
    options = relationship("OrderItemOption", back_populates="order_item", cascade="all, delete-orphan")


class OrderItemIngredient(Base):
    __tablename__ = "order_item_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    ingredient_id = Column(Integer, nullable=False)
    ingredient_name = Column(String, nullable=False)
    included = Column(Boolean, default=True)
    order_item = relationship("OrderItem", back_populates="ingredients")


class OrderItemOption(Base):
    __tablename__ = "order_item_options"
    id = Column(Integer, primary_key=True, index=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    option_id = Column(Integer, nullable=False)
    option_name = Column(String, nullable=False)
    group_name = Column(String, nullable=False)
    order_item = relationship("OrderItem", back_populates="options")
