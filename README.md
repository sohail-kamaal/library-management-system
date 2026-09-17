# Library Management System (Browser Version)

A Library Management System that runs in your browser, built with Flask and SQLite.

## Features
- Dashboard with live stats (total books, available copies, members, overdue items)
- Add, search, and delete books
- Register and remove members
- Issue books to members (14-day loan period) and mark them returned
- Automatic fine calculation for late returns (Rs. 5/day)
- Clean, responsive UI - no page reload frameworks, just Flask + Jinja templates

## Requirements
- Python 3.8+
- Flask (`pip install flask`)

## How to run in VS Code

1. Put these files in one folder, keeping the structure below.
2. Open the folder in VS Code (`File > Open Folder`).
3. Open a terminal (`` Ctrl+` ``) and install Flask:

   ```bash
   pip install flask
   ```

   (On Mac, if `pip` isn't found, use `pip3 install flask`.)

4. Run the app:

   ```bash
   python3 app.py
   ```

5. Open your browser and go to:

   ```
   http://127.0.0.1:5000
   ```

   The app auto-reloads while `debug=True` is set in `app.py`, so any code changes refresh automatically.

## Project Structure
```
library-web/
│
├── app.py               # Flask app - all routes and logic
├── db.py                # Database connection and table setup
├── library.db            # Created automatically on first run
├── templates/
│   ├── base.html         # Shared layout, nav bar, flash messages
│   ├── dashboard.html    # Home page with stats
│   ├── books.html        # Book catalog, search, add/delete
│   ├── members.html      # Member list, add/delete
│   └── issue.html        # Issue and return books
└── static/
    └── style.css         # All styling
```

## Notes
- To reset all data, delete `library.db` and restart the app.
- Loan period and fine rate can be changed at the top of `app.py` (`LOAN_DAYS`, `FINE_PER_DAY`).
- Change `app.secret_key` in `app.py` before deploying this anywhere public - it's currently a placeholder.
