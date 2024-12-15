from flask import Flask, flash, redirect, render_template, request
from datetime import datetime
import calendar
import os
import sqlite3

# Configure application
app = Flask(__name__)

# Set the secret key for session management. Needed for flash messages
app.secret_key = os.urandom(24)  # Generates a random 24-byte key.

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure SQLite3 database
DATABASE = 'birthdays.db'


def get_db():
    """Open a new database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
def index():
    this_year = datetime.now().year  # Get the current year
    current_date = datetime.now()  # Get today's date

    # Get user data with server-side validation
    if request.method == "POST":

        # Get form values
        name, year, month, day = request.form.get("name"), request.form.get(
            "year"), request.form.get("month"), request.form.get("day")

        # Validate input
        invalid_name = not name
        invalid_year = not year.isdigit() or int(year) < 1900 or int(year) > this_year
        invalid_month = not month.isdigit() or int(month) < 1 or int(month) > 12
        invalid_day = not day.isdigit() or int(day) < 1 or int(
            day) > 31  # Initial check for day (to ensure number is valid)

        if invalid_name:
            flash("Name is required.")
            return redirect("/")
        elif invalid_year:
            flash("Year must be a valid number between 1900 and the current year.")
            return redirect("/")
        elif invalid_month:
            flash("Month must be a valid number between 1 and 12.")
            return redirect("/")
        elif invalid_day:
            flash("Day must be a valid number based on the selected month.")
            return redirect("/")

        # Only check the month range after validating the month is valid
        if invalid_month:
            flash("Invalid month number. Please enter a number between 1 and 12.")
            return redirect("/")

        # Validate day for the specific month (after checking month and year validity)
        try:
            max_days = calendar.monthrange(int(year), int(month))[1]
            if int(day) < 1 or int(day) > max_days:
                flash(
                    f"Invalid day number for the selected month. The {month}. month has a maximum of {max_days} days.")
                return redirect("/")
        except calendar.IllegalMonthError:
            flash("Invalid month. Please enter a number between 1 and 12.")
            return redirect("/")

        # Convert to integers
        year, month, day = int(year), int(month), int(day)

        # Insert the user's information into the database
        conn = get_db()
        conn.execute("INSERT INTO birthdays (name, year, month, day) VALUES (?, ?, ?, ?)",
                     (name, year, month, day))
        conn.commit()
        conn.close()

        # Flash success message
        flash("Birthday added successfully!", category="success")

        # Ensure POST request is followed by a GET request
        return redirect("/")

    else:
        # Get all birthday entries from the database
        conn = get_db()
        birthdays = conn.execute("SELECT * FROM birthdays").fetchall()
        conn.close()

        # Initiate list to keep tuples containing:
        # 1) Entry dictionary with person's details (name, year, month, day)
        # 2) Days until the birthday
        # Example: ({"name": "Harry Potter", "year": 1980, "month": 7, "day": 31}, 248)
        upcoming_birthdays = []

        for birthday in birthdays:
            # Convert sqlite3.Row to a dictionary
            birthday_dict = dict(birthday)  # Convert Row to dictionary

            # Create a datetime object for the birthday this year
            birthday_this_year = datetime(
                this_year, birthday_dict["month"], birthday_dict["day"])

            # Calculate the person's age based on the year of birth
            age = this_year - birthday_dict["year"]
            if current_date < birthday_this_year:
                age -= 1  # Subtract a year if today's date is before birthday
            birthday_dict["age"] = age

            # Calculate days until the next birthday
            try:
                if current_date < birthday_this_year:
                    # Birthday this year hasn't happened yet
                    next_birthday = birthday_this_year
                else:
                    # Birthday has passed, calculate for the next year
                    next_birthday = datetime(
                        this_year + 1, birthday_dict["month"], birthday_dict["day"])
            except ValueError:
                # Handle invalid dates like 29/02 for non-leap years
                if birthday_dict["month"] == 2 and birthday_dict["day"] == 29:
                    next_birthday = datetime(
                        this_year + 1, 2, 28)  # Adjust to Feb 28
                else:
                    raise  # Re-raise other invalid date errors

            # Calculate the number of days until the next birthday
            days_until_birthday = (next_birthday - current_date).days

            # Add the calculated days to the birthday data
            birthday_dict["days_until_birthday"] = days_until_birthday

            # Adds the processed birthday entry, including calculated days until the next birthday, to the list of upcoming birthdays.
            upcoming_birthdays.append(birthday_dict)

        # Sort the upcoming birthdays by the number of days until each birthday
        upcoming_birthdays.sort(key=lambda x: x["days_until_birthday"])

        # Return the sorted list of birthdays to the template
        return render_template("index.html", birthdays=upcoming_birthdays)


@app.route("/remove", methods=["POST"])
def remove():
    # Get the ID of the birthday entry to remove
    birthday_id = request.form.get("id")

    # Ensure the ID is valid (if needed, depending on your database design)
    if birthday_id:
        conn = get_db()
        conn.execute("DELETE FROM birthdays WHERE id = ?", (birthday_id,))
        conn.commit()
        conn.close()

    # Flash success message
    flash("Birthday successfully deleted!", category="success")

    # Redirect back to the main page
    return redirect("/")
