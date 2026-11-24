import re
from difflib import get_close_matches
from config import FUZZY_CUTOFF
from models import gift_names

def resolve_gift_name(raw: str) -> tuple[str | None, str | None]:
    """
    Fuzzy-match the user's input to an actual gift in the DB.
    Returns (resolved_name, None) on success,
            (None, suggestion) on a single close match we should confirm,
            (None, None) if nothing close enough.
    """
    raw = raw.strip().strip("?").strip()
    names = gift_names()
    if not names:
        return None, None

    # exact case-insensitive
    for n in names:
        if n.lower() == raw.lower():
            return n, None

    matches = get_close_matches(raw, names, n=2, cutoff=FUZZY_CUTOFF)
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        # ambiguous — ask
        return None, "ambiguous:" + "|".join(matches)
    return None, None

def parse(message: str) -> dict:
    text = message.strip()
    low = text.lower()

    if re.match(r"^(hi|hello|hey|start|help)\b", low):
        return {"intent": "help"}

    if low in ("list", "gifts", "show list", "available", "gift list"):
        return {"intent": "list"}

    if re.match(r"^(my reservations?|mine|what did i reserve)\b", low):
        return {"intent": "mine"}

    # unreserve / release
    m = re.match(r"^(unreserve|release|cancel|give back)\s+(.+)$", low)
    if m:
        return {"intent": "unreserve", "gift": m.group(2).strip()}

    # check availability
    m = re.match(
        r"^(is|check|do you have|have you got|still have)\s+(.+?)(\s+available)?\?*$",
        low,
    )
    if m:
        return {"intent": "check", "gift": m.group(2).strip()}

    # reserve
    m = re.match(r"^(reserve|claim|take|buy|i'?ll take|i want|i'd like)\s+(.+)$", low)
    if m:
        return {"intent": "reserve", "gift": m.group(2).strip()}

    # admin
    m = re.match(r"^add\s+(.+)$", low)
    if m:
        return {"intent": "admin_add", "gift": m.group(1).strip()}

    m = re.match(r"^(remove|delete)\s+(.+)$", low)
    if m:
        return {"intent": "admin_remove", "gift": m.group(2).strip()}

    m = re.match(r"^admin list$", low)
    if m:
        return {"intent": "admin_list"}

    return {"intent": "unknown", "text": text}