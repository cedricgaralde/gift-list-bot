import sqlite3
from contextlib import contextmanager
from config import DB_PATH

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                reserved INTEGER DEFAULT 0,
                reserved_by TEXT,
                reserved_at TEXT
            )
        """)

# ---------- queries ----------

def all_gifts():
    with get_db() as db:
        return db.execute(
            "SELECT name, reserved, reserved_by FROM gifts ORDER BY name"
        ).fetchall()

def gift_names():
    with get_db() as db:
        return [r["name"] for r in db.execute("SELECT name FROM gifts")]

def get_gift(name: str):
    with get_db() as db:
        return db.execute(
            "SELECT * FROM gifts WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()

def my_reservations(user_id: str):
    with get_db() as db:
        return db.execute(
            "SELECT name FROM gifts WHERE reserved_by = ? ORDER BY name",
            (user_id,),
        ).fetchall()

# ---------- mutations ----------

def add_gift(name: str) -> bool:
    with get_db() as db:
        try:
            db.execute("INSERT INTO gifts (name) VALUES (?)", (name.strip(),))
            return True
        except sqlite3.IntegrityError:
            return False

def remove_gift(name: str) -> bool:
    with get_db() as db:
        cur = db.execute("DELETE FROM gifts WHERE LOWER(name) = LOWER(?)", (name,))
        return cur.rowcount == 1

def reserve_gift(gift_name: str, user_id: str) -> tuple[bool, str]:
    """Atomic reservation: only succeeds if the gift exists AND is unreserved."""
    with get_db() as db:
        cur = db.execute(
            """UPDATE gifts
               SET reserved = 1, reserved_by = ?, reserved_at = datetime('now')
               WHERE LOWER(name) = LOWER(?) AND reserved = 0""",
            (user_id, gift_name),
        )
        if cur.rowcount == 1:
            return True, f"✅ Reserved **{gift_name}** for you!"

        row = db.execute(
            "SELECT reserved, reserved_by FROM gifts WHERE LOWER(name) = LOWER(?)",
            (gift_name,),
        ).fetchone()
        if row is None:
            return False, f"❌ No gift called **{gift_name}** on the list."
        if row["reserved_by"] == user_id:
            return False, "You already reserved that one. 😊"
        return False, f"❌ **{gift_name}** is already reserved."

def unreserve_gift(gift_name: str, user_id: str, is_admin: bool = False) -> tuple[bool, str]:
    with get_db() as db:
        if is_admin:
            cur = db.execute(
                "UPDATE gifts SET reserved=0, reserved_by=NULL, reserved_at=NULL "
                "WHERE LOWER(name)=LOWER(?) AND reserved=1",
                (gift_name,),
            )
        else:
            cur = db.execute(
                "UPDATE gifts SET reserved=0, reserved_by=NULL, reserved_at=NULL "
                "WHERE LOWER(name)=LOWER(?) AND reserved_by=?",
                (gift_name, user_id),
            )
        if cur.rowcount == 1:
            return True, f"✅ **{gift_name}** is now available again."
        return False, f"❌ You can't unreserve **{gift_name}** (not yours, or not reserved)."

def clear_all_gifts() -> int:
    """Delete every gift. Returns how many were removed."""
    with get_db() as db:
        cur = db.execute("DELETE FROM gifts")
        return cur.rowcount