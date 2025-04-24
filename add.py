from db import LibraryDatabase  # Assuming the class is in a file named library_database.py

if __name__ == "__main__":
    # Initialize the database
    db = LibraryDatabase()

    # Add users
    user1_id = db.create_user("John Doe", "john@example.com", "123 Main St", "555-1234")
    if user1_id:
        print(f"Added user 'John Doe' with ID: {user1_id}")
    else:
        print("Failed to add user 'John Doe', possibly duplicate email")

    user2_id = db.create_user("Jane Smith", "jane@example.com", "456 Elm St", "555-5678")
    if user2_id:
        print(f"Added user 'Jane Smith' with ID: {user2_id}")
    else:
        print("Failed to add user 'Jane Smith', possibly duplicate email")

    user3_id = db.create_user("Alice Johnson", "alice@example.com", "789 Oak St", "555-9012")
    if user3_id:
        print(f"Added user 'Alice Johnson' with ID: {user3_id}")
    else:
        print("Failed to add user 'Alice Johnson', possibly duplicate email")

    # Add books
    book1_id = db.add_book("The Great Gatsby", "F. Scott Fitzgerald", "Fiction", "9780743273565", 1925, 5, "Fiction Section, Shelf 3")
    if book1_id:
        print(f"Added book 'The Great Gatsby' with ID: {book1_id}")
    else:
        print("Failed to add book 'The Great Gatsby', possibly duplicate ISBN")

    book2_id = db.add_book("To Kill a Mockingbird", "Harper Lee", "Fiction", "9780446310789", 1960, 3, "Fiction Section, Shelf 4")
    if book2_id:
        print(f"Added book 'To Kill a Mockingbird' with ID: {book2_id}")
    else:
        print("Failed to add book 'To Kill a Mockingbird', possibly duplicate ISBN")

    book3_id = db.add_book("1984", "George Orwell", "Dystopian", "9780451524935", 1949, 2, "Fiction Section, Shelf 1")
    if book3_id:
        print(f"Added book '1984' with ID: {book3_id}")
    else:
        print("Failed to add book '1984', possibly duplicate ISBN")

    # Optionally, check out some books
    if user1_id and book1_id:
        order1_id = db.checkout_book(user1_id, book1_id)
        if order1_id:
            print(f"Checked out 'The Great Gatsby' to 'John Doe' with order ID: {order1_id}")
        else:
            print("Failed to check out 'The Great Gatsby' to 'John Doe'")

    if user2_id and book2_id:
        order2_id = db.checkout_book(user2_id, book2_id)
        if order2_id:
            print(f"Checked out 'To Kill a Mockingbird' to 'Jane Smith' with order ID: {order2_id}")
        else:
            print("Failed to check out 'To Kill a Mockingbird' to 'Jane Smith'")

    # Close the connection
    db.close_connection()