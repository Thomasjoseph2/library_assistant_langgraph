from pydantic import BaseModel, Field
from langchain.tools import tool
from datetime import datetime
from bson.objectid import ObjectId
from typing import List, Dict, Optional
from db import LibraryDatabase  # Assuming your LibraryDatabase class is in db.py

# Initialize database (assuming environment variables are set)
db = LibraryDatabase()

# Schema for book search input
class BookSearchInput(BaseModel):
    query: str = Field(description="Search query for book title, author, or genre")
    limit: int = Field(default=10, description="Maximum number of results to return")

@tool("search_books", args_schema=BookSearchInput)
def search_books(query: str, limit: int = 10) -> List[Dict]:
    """Search for books by title, author, or genre."""
    books = db.search_books(query, limit)
    return [
        {
            "title": book["title"],
            "author": book["author"],
            "genre": book["genre"],
            "isbn": book["isbn"],
            "quantity_available": book["quantity_available"],
            "location": book["location"]
        } for book in books
    ]

# Schema for user lookup input
class UserLookupInput(BaseModel):
    email: str = Field(description="User's email address")

@tool("get_user_info", args_schema=UserLookupInput)
def get_user_info(email: str) -> Optional[Dict]:
    """Retrieve user information by email."""
    user = db.get_user(email=email)
    if not user:
        return None
    return {
        "name": user["name"],
        "email": user["email"],
        "address": user["address"],
        "phone": user["phone"],
        "membership_status": user["membership_status"],
        "created_at": user["created_at"].isoformat()
    }

# Schema for checkout input
class CheckoutInput(BaseModel):
    user_email: str = Field(description="User's email address")
    book_isbn: str = Field(description="ISBN of the book to check out")

@tool("checkout_book", args_schema=CheckoutInput)
def checkout_book(user_email: str, book_isbn: str) -> str:
    """Check out a book to a user by email and book ISBN."""
    user = db.get_user(email=user_email)
    book = db.get_book(isbn=book_isbn)
    if not user or not book:
        return "User or book not found."
    if book["quantity_available"] <= 0:
        return "No copies available."
    order_id = db.checkout_book(str(user["_id"]), str(book["_id"]))
    if order_id:
        return f"Book checked out successfully. Order ID: {order_id}"
    return "Checkout failed. Please check user status or book availability."

# Schema for return input
class ReturnInput(BaseModel):
    order_id: str = Field(description="Order ID of the book to return")

@tool("return_book", args_schema=ReturnInput)
def return_book(order_id: str) -> str:
    """Return a book to the library by order ID."""
    success = db.return_book(order_id)
    if success:
        return "Book returned successfully."
    return "Return failed. Invalid order ID or book already returned."

# Schema for user orders input
class UserOrdersInput(BaseModel):
    user_email: str = Field(description="User's email address")
    status: Optional[str] = Field(default=None, description="Optional status filter (checked_out, overdue, returned)")

@tool("get_user_orders", args_schema=UserOrdersInput)
def get_user_orders(user_email: str, status: Optional[str] = None) -> List[Dict]:
    """Get all orders for a user, optionally filtered by status."""
    user = db.get_user(email=user_email)
    if not user:
        return []
    orders = db.get_user_orders(str(user["_id"]), status)
    return [
        {
            "order_id": str(order["_id"]),
            "book_id": order["book_id"],
            "checkout_date": order["checkout_date"].isoformat(),
            "due_date": order["due_date"].isoformat(),
            "return_date": order["return_date"].isoformat() if order["return_date"] else None,
            "status": order["status"]
        } for order in orders
    ]

# Schema for total orders input (no parameters needed)
class TotalOrdersInput(BaseModel):
    pass  # No input parameters required

@tool("get_total_orders", args_schema=TotalOrdersInput)
def get_total_orders() -> int:
    """Get the total number of orders in the library database."""
    return db.orders.count_documents({})

# Schema for total users input (no parameters needed)
class TotalUsersInput(BaseModel):
    pass  # No input parameters required

@tool("get_total_users", args_schema=TotalUsersInput)
def get_total_users() -> int:
    """Get the total number of users in the library database."""
    return db.users.count_documents({})