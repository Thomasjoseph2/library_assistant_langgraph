from db import LibraryDatabase
from library_tools import search_books, get_user_info, checkout_book, return_book, get_user_orders
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize database
db = LibraryDatabase()

def setup_test_data():
    """Set up test user and book in the database."""
    # Create a test user
    user_id = db.create_user(
        name="Test User",
        email="testuser@example.com",
        address="123 Test St",
        phone="555-9876"
    )
    if user_id:
        print(f"Created test user with ID: {user_id}")
    else:
        print("User already exists or creation failed.")

    # Add a test book
    book_id = db.add_book(
        title="Test Book",
        author="Test Author",
        genre="Fiction",
        isbn="1234567890123",
        publication_year=2020,
        quantity=2,
        location="Fiction Section"
    )
    if book_id:
        print(f"Created test book with ID: {book_id}")
    else:
        print("Book already exists or creation failed.")

    return user_id, book_id

def test_tools():
    """Test each tool with sample inputs."""
    # Set up test data
    user_id, book_id = setup_test_data()

    # Test 1: Search for books
    print("\nTesting search_books tool...")
    result = search_books.invoke({"query": "Test", "limit": 5})
    print("Search results:", result)

    # Test 2: Get user info
    print("\nTesting get_user_info tool...")
    result = get_user_info.invoke({"email": "testuser@example.com"})
    print("User info:", result)

    # Test 3: Checkout a book
    print("\nTesting checkout_book tool...")
    result = checkout_book.invoke({"user_email": "testuser@example.com", "book_isbn": "1234567890123"})
    print("Checkout result:", result)
    # Extract order ID from result (assuming success)
    order_id = result.split("Order ID: ")[-1] if "Order ID" in result else None

    # Test 4: Get user orders
    print("\nTesting get_user_orders tool...")
    result = get_user_orders.invoke({"user_email": "testuser@example.com", "status": "checked_out"})
    print("User orders:", result)

    # Test 5: Return a book (if checkout was successful)
    if order_id:
        print("\nTesting return_book tool...")
        result = return_book.invoke({"order_id": order_id})
        print("Return result:", result)
    else:
        print("\nSkipping return_book test due to failed checkout.")

    # Verify book quantity after return
    book = db.get_book(isbn="1234567890123")
    print(f"\nBook quantity after tests: {book['quantity_available']}")

def cleanup():
    """Clean up test data."""
    # Delete test user and book (only if no active orders)
    user = db.get_user(email="testuser@example.com")
    if user:
        if db.delete_user(str(user["_id"])):
            print("Cleaned up test user.")
        else:
            print("Could not delete user due to active orders.")
    
    book = db.get_book(isbn="1234567890123")
    if book:
        if db.delete_book(str(book["_id"])):
            print("Cleaned up test book.")
        else:
            print("Could not delete book due to active orders.")
    
    db.close_connection()

if __name__ == "__main__":
    try:
        test_tools()
    finally:
        cleanup()