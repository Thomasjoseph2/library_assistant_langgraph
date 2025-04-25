from pydantic import BaseModel, Field
from langchain.tools import tool
from typing import List, Dict, Optional
from db import LibraryDatabase 

# Initialize database 
db = LibraryDatabase()

from pydantic import BaseModel, Field
from typing import List, Dict

class BookSearchInput(BaseModel):
    query: str = Field(
        default="", 
        description="Search terms (title/author/genre) or empty for all books"
    )
    limit: int = Field(
        default=100,  # Increased default for "show all" cases
        description="Number of results (use higher values when listing all books)"
    )

def get_all_available_books(limit: int = 100) -> List[Dict]:
    """
    Retrieve all available books from the database where quantity_available > 0.

    Args:
        limit (int): Maximum number of books to return (default: 100).

    Returns:
        List[Dict]: List of book documents with title, author, genre, isbn, 
                   quantity_available, location, and publication_year.
    """
    try:
        books = db.books.find(
            {"quantity_available": {"$gt": 0}},
            {
                "title": 1,
                "author": 1,
                "genre": 1,
                "isbn": 1,
                "quantity_available": 1,
                "location": 1,
                "publication_year": 1,
                "_id": 0  # Exclude MongoDB's _id field
            }
        ).limit(limit)
        return list(books)
    except Exception as e:
        return [{"error": f"Failed to retrieve books: {str(e)}"}]

@tool("search_books", args_schema=BookSearchInput)
def search_books(query: str = "", limit: int = 100) -> List[Dict]:
    """
    Search books by criteria or list all available books when no query is provided.
    
    Args:
        query (str): Search terms (title, author, or genre). Empty string returns all available books.
        limit (int): Maximum number of results to return (default: 100).

    Returns:
        List[Dict]: List of formatted book dictionaries.
    """
    try:
        if not query.strip():
            books = get_all_available_books(limit)
        else:
            # Assuming db.search_books is implemented in LibraryDatabase
            books = db.search_books(query, limit)
        return format_books(books)
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]

def format_books(books: List[Dict]) -> List[Dict]:
    """
    Standardized formatting for book results.

    Args:
        books (List[Dict]): List of book documents from the database.

    Returns:
        List[Dict]: Formatted list of book dictionaries.
    """
    try:
        return [
            {
                "title": book.get("title", "Unknown Title"),
                "author": book.get("author", "Unknown Author"),
                "genre": book.get("genre", "Unknown Genre"),
                "isbn": book.get("isbn", "Unknown ISBN"),
                "available": book.get("quantity_available", 0) > 0,
                "location": book.get("location", "Unknown Location"),
                "publication_year": book.get("publication_year", "Unknown Year")
            }
            for book in books
        ]
    except Exception as e:
        return [{"error": f"Formatting failed: {str(e)}"}]

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

from pydantic import BaseModel, Field
from typing import Optional

class PlaceOrderInput(BaseModel):
    title: str = Field(description="Title of the book")
    author: str = Field(description="Author of the book")
    phone_number: str = Field(description="User's phone number")
    email: str = Field(description="User's email address")

@tool("place_order", args_schema=PlaceOrderInput)
def place_order(title: str, author: str, phone_number: str, email: str) -> Dict:
    """
    Place an order for a book with cash-on-delivery (COD).

    Args:
        title (str): Title of the book.
        author (str): Author of the book.
        phone_number (str): User's phone number.
        email (str): User's email address.

    Returns:
        Dict: Confirmation message or error details.
    """
    try:
        # Check if the book is available in the database
        book = db.books.find_one({"title": title, "author": author, "quantity_available": {"$gt": 0}})
        if not book:
            return {"error": "Book not found or out of stock."}

        # Create an order record in the database
        order = {
            "book_id": book["_id"],
            "title": title,
            "author": author,
            "user_email": email,
            "phone_number": phone_number,
            "status": "pending",
            "payment_method": "cash_on_delivery"
        }
        db.orders.insert_one(order)

        # Decrease the quantity_available by 1
        db.books.update_one({"_id": book["_id"]}, {"$inc": {"quantity_available": -1}})

        return {"message": f"Order placed successfully for '{title}' by {author}. COD payment confirmed."}
    except Exception as e:
        return {"error": f"Failed to place order: {str(e)}"}