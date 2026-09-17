from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash

from db import get_connection, init_db

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

LOAN_DAYS = 14
FINE_PER_DAY = 5  # rupees per day after due date


@app.route("/")
def dashboard():
    conn = get_connection()
    cur = conn.cursor()

    total_books = cur.execute("SELECT COALESCE(SUM(total_copies), 0) AS c FROM books").fetchone()["c"]
    available_books = cur.execute("SELECT COALESCE(SUM(available_copies), 0) AS c FROM books").fetchone()["c"]
    total_members = cur.execute("SELECT COUNT(*) AS c FROM members").fetchone()["c"]
    issued_count = cur.execute("SELECT COUNT(*) AS c FROM transactions WHERE return_date IS NULL").fetchone()["c"]

    overdue = cur.execute("""
        SELECT t.txn_id, b.title, m.name, t.due_date
        FROM transactions t
        JOIN books b ON t.book_id = b.book_id
        JOIN members m ON t.member_id = m.member_id
        WHERE t.return_date IS NULL AND t.due_date < ?
        ORDER BY t.due_date
    """, (datetime.now().strftime("%Y-%m-%d"),)).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_books=total_books,
        available_books=available_books,
        total_members=total_members,
        issued_count=issued_count,
        overdue=overdue,
    )


# ---------- Books ----------

@app.route("/books")
def books():
    conn = get_connection()
    q = request.args.get("q", "").strip()
    if q:
        rows = conn.execute(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ? ORDER BY title",
            (f"%{q}%", f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books ORDER BY title").fetchall()
    conn.close()
    return render_template("books.html", books=rows, q=q)


@app.route("/books/add", methods=["POST"])
def add_book():
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    isbn = request.form.get("isbn", "").strip() or None
    copies = request.form.get("copies", "1").strip()
    copies = int(copies) if copies.isdigit() and int(copies) > 0 else 1

    if not title or not author:
        flash("Title and author are required.", "error")
        return redirect(url_for("books"))

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO books (title, author, isbn, total_copies, available_copies) VALUES (?, ?, ?, ?, ?)",
            (title, author, isbn, copies, copies)
        )
        conn.commit()
        flash(f"'{title}' added to the catalog.", "success")
    except Exception as e:
        flash(f"Couldn't add book: {e}", "error")
    finally:
        conn.close()

    return redirect(url_for("books"))


@app.route("/books/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    conn = get_connection()
    conn.execute("DELETE FROM books WHERE book_id = ?", (book_id,))
    conn.commit()
    conn.close()
    flash("Book removed.", "success")
    return redirect(url_for("books"))


# ---------- Members ----------

@app.route("/members")
def members():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM members ORDER BY name").fetchall()
    conn.close()
    return render_template("members.html", members=rows)


@app.route("/members/add", methods=["POST"])
def add_member():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip() or None
    phone = request.form.get("phone", "").strip() or None

    if not name:
        flash("Member name is required.", "error")
        return redirect(url_for("members"))

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO members (name, email, phone) VALUES (?, ?, ?)",
            (name, email, phone)
        )
        conn.commit()
        flash(f"'{name}' registered as a member.", "success")
    except Exception as e:
        flash(f"Couldn't register member: {e}", "error")
    finally:
        conn.close()

    return redirect(url_for("members"))


@app.route("/members/delete/<int:member_id>", methods=["POST"])
def delete_member(member_id):
    conn = get_connection()
    conn.execute("DELETE FROM members WHERE member_id = ?", (member_id,))
    conn.commit()
    conn.close()
    flash("Member removed.", "success")
    return redirect(url_for("members"))


# ---------- Issue / Return ----------

@app.route("/issue")
def issue_page():
    conn = get_connection()
    available_books = conn.execute(
        "SELECT * FROM books WHERE available_copies > 0 ORDER BY title"
    ).fetchall()
    all_members = conn.execute("SELECT * FROM members ORDER BY name").fetchall()

    issued = conn.execute("""
        SELECT t.txn_id, b.title, m.name, t.issue_date, t.due_date
        FROM transactions t
        JOIN books b ON t.book_id = b.book_id
        JOIN members m ON t.member_id = m.member_id
        WHERE t.return_date IS NULL
        ORDER BY t.due_date
    """).fetchall()

    conn.close()
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "issue.html",
        available_books=available_books,
        all_members=all_members,
        issued=issued,
        today=today,
    )


@app.route("/issue", methods=["POST"])
def issue_book():
    book_id = request.form.get("book_id")
    member_id = request.form.get("member_id")

    if not book_id or not member_id:
        flash("Pick a book and a member.", "error")
        return redirect(url_for("issue_page"))

    conn = get_connection()
    book = conn.execute("SELECT available_copies FROM books WHERE book_id = ?", (book_id,)).fetchone()

    if not book or book["available_copies"] <= 0:
        flash("That book isn't available right now.", "error")
        conn.close()
        return redirect(url_for("issue_page"))

    issue_date = datetime.now()
    due_date = issue_date + timedelta(days=LOAN_DAYS)

    conn.execute(
        "INSERT INTO transactions (book_id, member_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
        (book_id, member_id, issue_date.strftime("%Y-%m-%d"), due_date.strftime("%Y-%m-%d"))
    )
    conn.execute(
        "UPDATE books SET available_copies = available_copies - 1 WHERE book_id = ?",
        (book_id,)
    )
    conn.commit()
    conn.close()

    flash(f"Book issued. Due back by {due_date.strftime('%Y-%m-%d')}.", "success")
    return redirect(url_for("issue_page"))


@app.route("/return/<int:txn_id>", methods=["POST"])
def return_book(txn_id):
    conn = get_connection()
    txn = conn.execute("SELECT * FROM transactions WHERE txn_id = ?", (txn_id,)).fetchone()

    if not txn or txn["return_date"]:
        flash("Nothing to return here.", "error")
        conn.close()
        return redirect(url_for("issue_page"))

    today = datetime.now()
    due_date = datetime.strptime(txn["due_date"], "%Y-%m-%d")
    days_late = (today - due_date).days
    fine = max(0, days_late) * FINE_PER_DAY

    conn.execute(
        "UPDATE transactions SET return_date = ?, fine = ? WHERE txn_id = ?",
        (today.strftime("%Y-%m-%d"), fine, txn_id)
    )
    conn.execute(
        "UPDATE books SET available_copies = available_copies + 1 WHERE book_id = ?",
        (txn["book_id"],)
    )
    conn.commit()
    conn.close()

    if fine > 0:
        flash(f"Returned, {days_late} day(s) late. Fine: Rs. {fine}", "error")
    else:
        flash("Returned on time, no fine.", "success")

    return redirect(url_for("issue_page"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
