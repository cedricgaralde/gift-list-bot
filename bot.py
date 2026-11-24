import discord
from discord.ext import commands

import config
from models import (
    init_db, all_gifts, my_reservations, add_gift, remove_gift,
    reserve_gift, unreserve_gift, get_gift, clear_all_gifts,
)
from intents import parse, resolve_gift_name

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

HELP_TEXT = (
    "👋 **Gift List Bot** — here's what I can do:\n"
    "• `list` — show all gifts\n"
    "• `is <gift> available?` — check one\n"
    "• `reserve <gift>` — claim a gift\n"
    "• `unreserve <gift>` — release one you reserved\n"
    "• `my reservations` — your claims\n"
    "Admins: `add <gift>`, `remove <gift>`, `admin list`, `clear`"
)

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

def format_list() -> str:
    rows = all_gifts()
    if not rows:
        return "The list is empty right now. (Admins: use `add <gift>`.)"
    lines = []
    for r in rows:
        if r["reserved"]:
            lines.append(f"🔒 {r['name']} — reserved")
        else:
            lines.append(f"🟢 {r['name']} — available")
    return "**Gift list**\n" + "\n".join(lines)

def handle_message(user_id: str, message: str) -> str:
    p = parse(message)
    intent = p["intent"]

    if intent == "help":
        return HELP_TEXT

    if intent == "list":
        return format_list()

    if intent == "mine":
        rows = my_reservations(user_id)
        if not rows:
            return "You haven't reserved anything yet."
        return "**Your reservations:**\n" + "\n".join(f"• {r['name']}" for r in rows)

    if intent in ("check", "reserve", "unreserve"):
        raw = p["gift"]
        resolved, hint = resolve_gift_name(raw)

        # ambiguous fuzzy match
        if resolved is None and hint and hint.startswith("ambiguous:"):
            opts = hint.split(":", 1)[1].split("|")
            return (
                f"That matches more than one gift: {', '.join('**'+o+'**' for o in opts)}. "
                "Which did you mean?"
            )

        # no match at all
        if resolved is None:
            return (
                f"❌ I couldn't find anything like **{raw}**. "
                "Try `list` to see the exact names."
            )

        # friendly note if we auto-corrected
        note = ""
        if resolved.lower() != raw.strip().strip('?').lower():
            note = f"(matched **{resolved}**)\n"

        if intent == "check":
            row = get_gift(resolved)
            if row["reserved"]:
                return note + f"🔒 **{resolved}** is already reserved."
            return note + f"🟢 **{resolved}** is available! Reply `reserve {resolved}` to claim it."

        if intent == "reserve":
            ok, msg = reserve_gift(resolved, user_id)
            return note + msg

        if intent == "unreserve":
            ok, msg = unreserve_gift(resolved, user_id, is_admin=is_admin(int(user_id)))
            return note + msg

    # ---- admin ----
    if intent in ("admin_add", "admin_remove", "admin_list"):
        if not is_admin(int(user_id)):
            return "🚫 That command is for admins only."

        if intent == "admin_add":
            ok = add_gift(p["gift"])
            return f"✅ Added **{p['gift']}**." if ok else f"⚠️ **{p['gift']}** already exists."

        if intent == "admin_remove":
            resolved, _ = resolve_gift_name(p["gift"])
            if not resolved:
                return f"❌ No gift like **{p['gift']}**."
            ok = remove_gift(resolved)
            return f"🗑️ Removed **{resolved}**." if ok else "Failed to remove."

        if intent == "admin_clear":
            if not is_admin(int(user_id)):
                return "🚫 That command is for admins only."
            n=clear_all_gifts()
            return f"🗑️ Cleared the list. Removed {n} gifts."
        

        if intent == "admin_list":
            rows = all_gifts()
            if not rows:
                return "List is empty."
            out = ["**Admin view (all gifts)**"]
            for r in rows:
                if r["reserved"]:
                    out.append(f"🔒 {r['name']} — by <@{r['reserved_by']}>")
                else:
                    out.append(f"🟢 {r['name']} — available")
            return "\n".join(out)

    return "I didn't understand that. Try `help`."

# ---------- Discord wiring ----------

@bot.event
async def on_ready():
    init_db()
    print(f"Logged in as {bot.user} (id={bot.user.id})")

@bot.event
async def on_message(msg: discord.Message):
    if msg.author.bot:
        return
    if not msg.content.strip():
        return
    reply = handle_message(str(msg.author.id), msg.content)
    # Discord messages cap at 2000 chars; chunk if needed
    for i in range(0, len(reply), 1900):
        await msg.channel.send(reply[i:i + 1900])

if __name__ == "__main__":
    init_db()
    bot.run(config.TOKEN)