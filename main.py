from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from math import ceil
app = FastAPI(title="City Public Library API")
# In-memory data (Day 1)
books = [
    {"id": 1, "title": "The Time Machine", "author": "H. G. Wells", "genre": "Fiction", "is_available": True},
    {"id": 2, "title": "Clean Code", "author": "Robert C. Martin", "genre": "Tech", "is_available": True},
    {"id": 3, "title": "A Brief History of Time", "author": "Stephen Hawking", "genre": "Science", "is_available": True},
    {"id": 4, "title": "Sapiens", "author": "Yuval Noah Harari", "genre": "History", "is_available": True},
    {"id": 5, "title": "The Pragmatic Programmer", "author": "Andrew Hunt", "genre": "Tech", "is_available": True},
    {"id": 6, "title": "1984", "author": "George Orwell", "genre": "Fiction", "is_available": True},
]
borrow_records: List[Dict[str, Any]] = []
record_counter = 1
queue: List[Dict[str, Any]] = []  # each entry: {"member_name": str, "book_id": int}
# Helper functions (Day 3)
def find_book(book_id: int) -> Optional[Dict[str, Any]]:
    """Return book dict by id or None."""
    for b in books:
        if b["id"] == book_id:
            return b
    return None
def calculate_due_date(borrow_days: int, member_type: str = "regular") -> str:
    """
    Simple due date message generator.
    Business rule: regular max 30 days, premium max 60 days.
    For demonstration we return a string like 'Return by: Day X' where X is base 15 + borrow_days.
    """
    max_days = 60 if member_type == "premium" else 30
    if borrow_days > max_days:
        raise ValueError(f"borrow_days exceeds allowed maximum for {member_type} members ({max_days})")
    # Simple illustrative calculation
    base_day = 15
    return f"Return by: Day {base_day + borrow_days}"
def filter_books_logic(genre: Optional[str] = None, author: Optional[str] = None, is_available: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Filter books using is not None checks for optional params."""
    results = []
    for b in books:
        if genre is not None and b["genre"].lower() != genre.lower():
            continue
        if author is not None and b["author"].lower() != author.lower():
            continue
        if is_available is not None and b["is_available"] != is_available:
            continue
        results.append(b)
    return results
# Pydantic models (Day 2 & 4)
class BorrowRequest(BaseModel):
    member_name: str = Field(..., min_length=2)
    book_id: int = Field(..., gt=0)
    borrow_days: int = Field(..., gt=0, le=60)  # upper bound will be validated by member_type logic
    member_id: str = Field(..., min_length=4)
    member_type: str = Field("regular")  # 'regular' or 'premium'
    @validator("member_type")
    def validate_member_type(cls, v):
        if v not in ("regular", "premium"):
            raise ValueError("member_type must be 'regular' or 'premium'")
        return v
    @validator("borrow_days")
    def validate_borrow_days(cls, v):
        if v <= 0:
            raise ValueError("borrow_days must be greater than 0")
        return v
class NewBook(BaseModel):
    title: str = Field(..., min_length=2)
    author: str = Field(..., min_length=2)
    genre: str = Field(..., min_length=2)
    is_available: bool = True
# Q1: Home route
@app.get("/", tags=["Home"])
def home():
    """
    Q1: Home route
    Returns a welcome message.
    """
    return {"message": "Welcome to City Public Library"}
# Q2: GET /books (list all) and counts
@app.get("/books", tags=["Books"])
def get_books():
    """
    Q2: Return all books, total count, and available_count.
    """
    total = len(books)
    available_count = sum(1 for b in books if b["is_available"])
    return {"total": total, "available_count": available_count, "books": books}
# Q5: Summary endpoint (must be above variable routes)
@app.get("/books/summary", tags=["Books"])
def books_summary():
    """
    Q5: Summary: total books, available, borrowed, breakdown per genre.
    """
    total = len(books)
    available = sum(1 for b in books if b["is_available"])
    borrowed = total - available
    genre_breakdown: Dict[str, int] = {}
    for b in books:
        genre_breakdown[b["genre"]] = genre_breakdown.get(b["genre"], 0) + 1
    return {
        "total_books": total,
        "available_count": available,
        "borrowed_count": borrowed,
        "genre_breakdown": genre_breakdown,
    }
# Q3: GET /books/{book_id} (variable route)
@app.get("/books/{book_id}", tags=["Books"])
def get_book_by_id(book_id: int):
    """
    Q3: Return book by ID or error message.
    """
    b = find_book(book_id)
    if not b:
        raise HTTPException(status_code=404, detail={"error": "Book not found"})
    return b
# Q4: Borrow records list
@app.get("/borrow-records", tags=["Borrow Records"])
def get_borrow_records():
    """
    Q4: Return all borrow records and total count.
    """
    return {"total_records": len(borrow_records), "borrow_records": borrow_records}
# Q6: BorrowRequest model validation is above
# Q7: Helper functions are above (find_book, calculate_due_date, filter_books_logic)
# Q8 & Q9: POST /borrow
@app.post("/borrow", tags=["Borrow"], status_code=status.HTTP_201_CREATED)
def borrow_book(request: BorrowRequest):
    """
    Q8: Borrow a book using BorrowRequest.
    - Check book exists
    - Check availability
    - Mark unavailable and append borrow record
    - Use calculate_due_date (modified by member_type)
    """
    global record_counter
    book = find_book(request.book_id)
    if not book:
        raise HTTPException(status_code=404, detail={"error": "Book not found"})
    if not book["is_available"]:
        raise HTTPException(status_code=400, detail={"error": "Book is currently not available"})
    # Validate borrow_days against member_type (Q9)
    try:
        due_msg = calculate_due_date(request.borrow_days, request.member_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    # Mark book as borrowed
    book["is_available"] = False
    # Create borrow record
    record = {
        "record_id": record_counter,
        "member_name": request.member_name,
        "member_id": request.member_id,
        "member_type": request.member_type,
        "book_id": request.book_id,
        "book_title": book["title"],
        "borrow_days": request.borrow_days,
        "due_message": due_msg,
    }
    borrow_records.append(record)
    record_counter += 1
    return {"message": "Borrow confirmed", "borrow_record": record}
# Q10: GET /books/filter
@app.get("/books/filter", tags=["Books"])
def filter_books(
    genre: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    is_available: Optional[bool] = Query(None),
):
    """
    Q10: Filter books by optional genre, author, is_available.
    Uses filter_books_logic helper.
    """
    results = filter_books_logic(genre=genre, author=author, is_available=is_available)
    return {"count": len(results), "results": results}
# Q11: POST /books (create new book) - reject duplicate titles (case-insensitive)
@app.post("/books", tags=["Books"], status_code=status.HTTP_201_CREATED)
def create_book(new_book: NewBook):
    """
    Q11: Add a new book. Reject duplicate titles (case-insensitive).
    Assign a new id.
    """
    # Duplicate title check
    for b in books:
        if b["title"].strip().lower() == new_book.title.strip().lower():
            raise HTTPException(status_code=400, detail={"error": "Book with this title already exists"})
    new_id = max((b["id"] for b in books), default=0) + 1
    book_entry = {
        "id": new_id,
        "title": new_book.title.strip(),
        "author": new_book.author.strip(),
        "genre": new_book.genre.strip(),
        "is_available": new_book.is_available,
    }
    books.append(book_entry)
    return {"message": "Book added", "book": book_entry}
# Q12: PUT /books/{book_id} with optional query params
@app.put("/books/{book_id}", tags=["Books"])
def update_book(book_id: int, genre: Optional[str] = Query(None), is_available: Optional[bool] = Query(None)):
    """
    Q12: Update only non-None fields (genre, is_available). Return 404 if not found.
    """
    book = find_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail={"error": "Book not found"})
    if genre is not None:
        book["genre"] = genre
    if is_available is not None:
        book["is_available"] = is_available
    return {"message": "Book updated", "book": book}
# Q13: DELETE /books/{book_id}
@app.delete("/books/{book_id}", tags=["Books"])
def delete_book(book_id: int):
    """
    Q13: Delete a book. 404 if not found.
    Business rule: cannot delete if book is currently borrowed (is_available == False).
    """
    for i, b in enumerate(books):
        if b["id"] == book_id:
            if not b["is_available"]:
                raise HTTPException(status_code=400, detail={"error": "Cannot delete a book that is currently borrowed"})
            deleted_title = b["title"]
            books.pop(i)
            return {"message": f"Deleted book: {deleted_title}"}
    raise HTTPException(status_code=404, detail={"error": "Book not found"})
# Q14: Borrow queue - POST /queue/add and GET /queue
@app.post("/queue/add", tags=["Queue"])
def add_to_queue(member_name: str = Query(..., min_length=2), book_id: int = Query(..., gt=0)):
    """
    Q14: Add a member to the waitlist for a book only if the book is currently unavailable.
    """
    book = find_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail={"error": "Book not found"})
    if book["is_available"]:
        raise HTTPException(status_code=400, detail={"error": "Book is available; no need to join queue"})
    # Add to queue
    queue.append({"member_name": member_name, "book_id": book_id})
    return {"message": "Added to queue", "queue_position": len(queue)}
@app.get("/queue", tags=["Queue"])
def get_queue():
    """
    Q14: Return current waitlist.
    """
    return {"queue_length": len(queue), "queue": queue}
# Q15: POST /return/{book_id} - return and reassign if queued
@app.post("/return/{book_id}", tags=["Borrow"])
def return_book(book_id: int):
    """
    Q15: Return a book. If someone is waiting in queue for that book, auto-assign to first in line.
    """
    global record_counter
    book = find_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail={"error": "Book not found"})
    # Mark returned
    book["is_available"] = True
    # Check queue for first person waiting for this book
    for idx, q in enumerate(queue):
        if q["book_id"] == book_id:
            # Assign to this member
            member_name = q["member_name"]
            # Create a borrow record with default borrow_days (e.g., 14) and member_type regular
            borrow_days = 14
            try:
                due_msg = calculate_due_date(borrow_days, "regular")
            except ValueError:
                due_msg = calculate_due_date(14, "regular")
            # Mark book as borrowed again
            book["is_available"] = False
            record = {
                "record_id": record_counter,
                "member_name": member_name,
                "member_id": f"auto_{record_counter}",
                "member_type": "regular",
                "book_id": book_id,
                "book_title": book["title"],
                "borrow_days": borrow_days,
                "due_message": due_msg,
                "assigned_from_queue": True,
            }
            borrow_records.append(record)
            record_counter += 1
            # Remove from queue
            queue.pop(idx)
            return {"message": "returned and re-assigned", "assigned_to": member_name, "borrow_record": record}
    return {"message": "returned and available", "book": book}
# Q16: GET /books/search (required param keyword)
@app.get("/books/search", tags=["Books"])
def search_books(keyword: str = Query(..., min_length=1)):
    """
    Q16: Case-insensitive search across title and author.
    """
    kw = keyword.lower()
    results = [b for b in books if kw in b["title"].lower() or kw in b["author"].lower()]
    if not results:
        return {"message": "No books found matching the keyword", "total_found": 0, "results": []}
    return {"total_found": len(results), "results": results}
# Q17: GET /books/sort
@app.get("/books/sort", tags=["Books"])
def sort_books(sort_by: str = Query("title"), order: str = Query("asc")):
    """
    Q17: Sort books by title, author, or genre. Validate params.
    """
    allowed_sort = {"title", "author", "genre"}
    if sort_by not in allowed_sort:
        raise HTTPException(status_code=400, detail={"error": f"Invalid sort_by. Allowed: {', '.join(allowed_sort)}"})
    if order not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail={"error": "Invalid order. Allowed: asc, desc"})
    reverse = order == "desc"
    sorted_books = sorted(books, key=lambda x: x[sort_by].lower(), reverse=reverse)
    return {"sort_by": sort_by, "order": order, "results": sorted_books}
# Q18: GET /books/page (pagination)
@app.get("/books/page", tags=["Books"])
def books_page(page: int = Query(1, ge=1), limit: int = Query(3, ge=1)):
    """
    Q18: Paginate books list.
    """
    total = len(books)
    total_pages = ceil(total / limit) if limit else 1
    if page > total_pages and total_pages != 0:
        raise HTTPException(status_code=400, detail={"error": "Page number out of range"})
    start = (page - 1) * limit
    end = start + limit
    sliced = books[start:end]
    return {
        "total": total,
        "total_pages": total_pages,
        "page": page,
        "limit": limit,
        "results": sliced,
    }
# Q19: Borrow-records search and pagination (place above variable routes)
@app.get("/borrow-records/search", tags=["Borrow Records"])
def borrow_records_search(member_name: str = Query(..., min_length=1)):
    """
    Q19: Search borrow records by member_name (case-insensitive).
    """
    kw = member_name.lower()
    results = [r for r in borrow_records if kw in r["member_name"].lower()]
    return {"total_found": len(results), "results": results}
@app.get("/borrow-records/page", tags=["Borrow Records"])
def borrow_records_page(page: int = Query(1, ge=1), limit: int = Query(5, ge=1)):
    """
    Q19: Paginate borrow records.
    """
    total = len(borrow_records)
    total_pages = ceil(total / limit) if limit else 1
    if page > total_pages and total_pages != 0:
        raise HTTPException(status_code=400, detail={"error": "Page number out of range"})
    start = (page - 1) * limit
    end = start + limit
    sliced = borrow_records[start:end]
    return {
        "total": total,
        "total_pages": total_pages,
        "page": page,
        "limit": limit,
        "results": sliced,
    }
# Q20: GET /books/browse (combined filter -> sort -> paginate)
@app.get("/books/browse", tags=["Books"])
def browse_books(
    keyword: Optional[str] = Query(None),
    sort_by: str = Query("title"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(3, ge=1),
):
    """
    Q20: Combined browsing endpoint.
    Steps:
      1. Filter by keyword across title and author (if provided)
      2. Sort by sort_by and order
      3. Paginate results
    Returns metadata and results.
    """
    # 1. Filter
    filtered = books
    if keyword:
        kw = keyword.lower()
        filtered = [b for b in filtered if kw in b["title"].lower() or kw in b["author"].lower()]
    # 2. Sort validation and sort
    allowed_sort = {"title", "author", "genre"}
    if sort_by not in allowed_sort:
        raise HTTPException(status_code=400, detail={"error": f"Invalid sort_by. Allowed: {', '.join(allowed_sort)}"})
    if order not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail={"error": "Invalid order. Allowed: asc, desc"})
    reverse = order == "desc"
    filtered_sorted = sorted(filtered, key=lambda x: x[sort_by].lower(), reverse=reverse)
    # 3. Paginate
    total = len(filtered_sorted)
    total_pages = ceil(total / limit) if limit else 1
    if page > total_pages and total_pages != 0:
        raise HTTPException(status_code=400, detail={"error": "Page number out of range"})
    start = (page - 1) * limit
    end = start + limit
    results = filtered_sorted[start:end]
    return {
        "keyword": keyword,
        "sort_by": sort_by,
        "order": order,
        "pagination": {"total": total, "total_pages": total_pages, "page": page, "limit": limit},
        "results": results,
    }
