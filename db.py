import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Atlas connection
class LibraryDatabase:
    def __init__(self):
        # Get MongoDB connection string from environment variable
        # Format: mongodb+srv://username:password@cluster0.mongodb.net/library
        connection_string = os.getenv("MONGODB_URI")
        
        if not connection_string:
            raise ValueError("MongoDB connection string not found in environment variables")
        
        # Connect to MongoDB
        self.client = MongoClient(connection_string)
        
        # Create or access the library database
        self.db = self.client.library
        
        # Create collections if they don't exist
        if "users" not in self.db.list_collection_names():
            self.db.create_collection("users")
        
        if "books" not in self.db.list_collection_names():
            self.db.create_collection("books")
        
        if "orders" not in self.db.list_collection_names():
            self.db.create_collection("orders")
        
        # Create references to collections
        self.users = self.db.users
        self.books = self.db.books
        self.orders = self.db.orders
        
        # Create indexes
        self.users.create_index([("email", pymongo.ASCENDING)], unique=True)
        self.books.create_index([("isbn", pymongo.ASCENDING)], unique=True)
        self.orders.create_index([("user_id", pymongo.ASCENDING), ("book_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)])
    
    # User methods
    def create_user(self, name, email, address, phone, membership_status="active"):
        """Create a new user in the database"""
        try:
            user = {
                "name": name,
                "email": email,
                "address": address,
                "phone": phone,
                "membership_status": membership_status,
                "created_at": datetime.now()
            }
            result = self.users.insert_one(user)
            return str(result.inserted_id)
        except pymongo.errors.DuplicateKeyError:
            return None
    
    def get_user(self, user_id=None, email=None):
        """Retrieve a user by ID or email"""
        if user_id:
            return self.users.find_one({"_id": ObjectId(user_id)})
        elif email:
            return self.users.find_one({"email": email})
        return None
    
    def update_user(self, user_id, updates):
        """Update user information"""
        return self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": updates}
        ).modified_count
    
    def delete_user(self, user_id):
        """Delete a user from the database"""
        # Check if user has active orders
        active_orders = self.orders.count_documents({
            "user_id": user_id,
            "status": {"$in": ["checked_out", "overdue"]}
        })
        
        if active_orders > 0:
            return False
        
        # Delete user
        result = self.users.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0
    
    # Book methods
    def add_book(self, title, author, genre, isbn, publication_year, quantity=1, location=""):
        """Add a new book to the database"""
        try:
            book = {
                "title": title,
                "author": author,
                "genre": genre,
                "isbn": isbn,
                "publication_year": publication_year,
                "quantity_available": quantity,
                "location": location,
                "added_at": datetime.now()
            }
            result = self.books.insert_one(book)
            return str(result.inserted_id)
        except pymongo.errors.DuplicateKeyError:
            return None
    
    def get_book(self, book_id=None, isbn=None):
        """Retrieve a book by ID or ISBN"""
        if book_id:
            return self.books.find_one({"_id": ObjectId(book_id)})
        elif isbn:
            return self.books.find_one({"isbn": isbn})
        return None
    
    def search_books(self, query, limit=10):
        """Search books by title, author, or genre"""
        return list(self.books.find({
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"author": {"$regex": query, "$options": "i"}},
                {"genre": {"$regex": query, "$options": "i"}}
            ]
        }).limit(limit))
    
    def update_book(self, book_id, updates):
        """Update book information"""
        return self.books.update_one(
            {"_id": ObjectId(book_id)},
            {"$set": updates}
        ).modified_count
    
    def delete_book(self, book_id):
        """Delete a book from the database"""
        # Check if book has active orders
        active_orders = self.orders.count_documents({
            "book_id": book_id,
            "status": {"$in": ["checked_out", "overdue"]}
        })
        
        if active_orders > 0:
            return False
        
        # Delete book
        result = self.books.delete_one({"_id": ObjectId(book_id)})
        return result.deleted_count > 0
    
    # Order methods
    def checkout_book(self, user_id, book_id, days=14):
        """Check out a book to a user"""
        # Check if book is available
        book = self.books.find_one({"_id": ObjectId(book_id)})
        if not book or book["quantity_available"] <= 0:
            return None
        
        # Check if user exists and is active
        user = self.users.find_one({
            "_id": ObjectId(user_id),
            "membership_status": "active"
        })
        if not user:
            return None
        
        # Create order
        checkout_date = datetime.now()
        due_date = checkout_date + timedelta(days=days)
        
        order = {
            "user_id": str(user["_id"]),
            "book_id": str(book["_id"]),
            "checkout_date": checkout_date,
            "due_date": due_date,
            "return_date": None,
            "status": "checked_out"
        }
        
        result = self.orders.insert_one(order)
        
        # Update book quantity
        self.books.update_one(
            {"_id": ObjectId(book_id)},
            {"$inc": {"quantity_available": -1}}
        )
        
        return str(result.inserted_id)
    
    def return_book(self, order_id):
        """Return a book to the library"""
        order = self.orders.find_one({"_id": ObjectId(order_id)})
        if not order or order["status"] == "returned":
            return False
        
        # Update order
        return_date = datetime.now()
        
        self.orders.update_one(
            {"_id": ObjectId(order_id)},
            {
                "$set": {
                    "return_date": return_date,
                    "status": "returned"
                }
            }
        )
        
        # Update book quantity
        self.books.update_one(
            {"_id": ObjectId(order["book_id"])},
            {"$inc": {"quantity_available": 1}}
        )
        
        return True
    
    def get_user_orders(self, user_id, status=None):
        """Get all orders for a user, optionally filtered by status"""
        query = {"user_id": str(user_id)}
        if status:
            query["status"] = status
        
        return list(self.orders.find(query))
    
    def get_overdue_orders(self):
        """Get all overdue orders"""
        now = datetime.now()
        
        # Find checked out orders that are past due date
        self.orders.update_many(
            {
                "status": "checked_out",
                "due_date": {"$lt": now}
            },
            {"$set": {"status": "overdue"}}
        )
        
        # Return all overdue orders
        return list(self.orders.find({"status": "overdue"}))
    
    def close_connection(self):
        """Close MongoDB connection"""
        self.client.close()


# Example usage
if __name__ == "__main__":
    # Initialize database
    db = LibraryDatabase()
    
    # Create test data
    user_id = db.create_user(
        "John Doe", 
        "john@example.com", 
        "123 Main St", 
        "555-1234"
    )
    
    book_id = db.add_book(
        "The Great Gatsby",
        "F. Scott Fitzgerald",
        "Fiction",
        "9780743273565",
        1925,
        5,
        "Fiction Section, Shelf 3"
    )
    
    # Check out a book
    order_id = db.checkout_book(user_id, book_id)
    
    # Print book availability
    book = db.get_book(book_id=book_id)
    print(f"Book '{book['title']}' has {book['quantity_available']} copies available")
    
    # Return book
    db.return_book(order_id)
    
    # Check updated availability
    book = db.get_book(book_id=book_id)
    print(f"After return, book '{book['title']}' has {book['quantity_available']} copies available")
    
    # Close connection
    db.close_connection()