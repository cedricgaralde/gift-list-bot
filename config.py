import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_IDS = {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}
DB_PATH = os.getenv("DB_PATH", "gifts.db")
# Fuzzy matching threshold (0–1). 0.75 is a good balance.
FUZZY_CUTOFF = float(os.getenv("FUZZY_CUTOFF", "0.75"))