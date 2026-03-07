import sqlite3
import csv
import os

DB_PATH = 'movies.db'
CSV_PATH = 'movies.csv'

def clean_row(row: dict) -> dict:
    """Clean & normalis csv row (dict) before inserting"""

    # strip whitespace from values
    row = {k.strip(): v.strip() for k, v in row.items()}

    # Clean the worldwide_gross field by removing $ and commas, and spaces
    worldwide_gross = row.get("Worldwide Gross", "0")
    worldwide_gross = worldwide_gross.replace("$", "")
    row["Worldwide Gross"] = float(worldwide_gross) or 0.0

    # Clean numeric columns
    row["Audience score %"] = int(row["Audience score %"] or 0)
    row["Profitability"] = float(row["Profitability"] or 0.0)
    row["Rotten Tomatoes %"] = int(row["Rotten Tomatoes %"] or 0)
    row["Year"] = int(row["Year"] or 0)

    # normalise genre to title case
    row["Genre"] = row.get("Genre", "").title()
    return row

def create_schema(conn: sqlite3.Connection):
    """Create movies table if it doesnt exist"""
    conn.execute("""
                 CREATE TABLE IF NOT EXISTS movies (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 film TEXT NOT NULL,
                 genre TEXT,
                 lead_studio TEXT,
                 audience_score INTEGER,
                 profitability REAL,
                 rotten_tomatoes INTEGER,
                 worldwide_gross REAL,
                 year INTEGER
                 )
                 """)
    conn.commit()   # make the change permanent

def seed_database(conn: sqlite3.Connection):
    """Load csv rows into the movies table"""
    
    # dont re-seed if data already exists
    existing = conn.execute("SELECT COUNT(*) FROM movies").fetchone()
    existing = existing[0]
    if existing > 0:
        print(f"DB already has {existing} rows, skipping seeding")
        return
    
    rows_loaded = 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)  # converts each row into a dict with the column name as the key
        for row in reader:
            row = clean_row(row)
            # pass the values as parameters to prevent SQL injection
            conn.execute("""
                         INSERT INTO movies
                         (film, genre, lead_studio, audience_score, profitability, rotten_tomatoes, worldwide_gross, year)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                         """, (
                             row["Film"],
                             row["Genre"],
                             row["Lead Studio"],
                             row["Audience score %"],
                             row["Profitability"],
                             row["Rotten Tomatoes %"],
                             row["Worldwide Gross"],
                             row["Year"]
                         ))
            rows_loaded += 1
    
    conn.commit()   # make the change permanent
    print(f"Seeded database with {rows_loaded} rows")

def get_db_connection() -> sqlite3.Connection:
    """Get connection to to the db. Creates and seeds db on 1st run"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows you to access columns by name instead of index
    create_schema(conn)
    seed_database(conn)
    return conn

if __name__ == "__main__":
    conn = get_db_connection()
    conn.close()    # close the connection when done so it doesnt lock the db file