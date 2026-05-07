import logging
import os
import json
from datetime import datetime, timedelta
from telegram import (
Update,
ReplyKeyboardMarkup,
KeyboardButton,
InlineKeyboardMarkup,
InlineKeyboardButton,
ReplyKeyboardRemove,
)
from telegram.ext import (
Application,
CommandHandler,
MessageHandler,
CallbackQueryHandler,
ConversationHandler,
filters,
ContextTypes,
)

# ================================================================

# SOZLAMALAR

# ================================================================

TOKEN = os.getenv(“BOT_TOKEN”, “”)
ADMIN_ID = int(os.getenv(“ADMIN_ID”, “0”))
DATA_FILE = “data.json”

# ================================================================

# HOLATLAR

# ================================================================

(
REG_NAME,
REG_PHONE,
ORDER_ADDRESS,
MENU_BROWSE,
ADMIN_MENU_INPUT,
ADMIN_BROADCAST,
) = range(6)

# ================================================================

# GLOBAL MA’LUMOTLAR

# ================================================================

users = {}
menu = {}
orders = {}
order_counter = [0]
stats = {“total_orders”: 0, “total_revenue”: 0, “daily”: {}, “weekly”: {}}

logging.basicConfig(
format=”%(asctime)s [%(levelname)s] %(message)s”,
level=logging.INFO,
)
log = logging.getLogger(**name**)

# ================================================================

# SAQLASH / YUKLASH

# ================================================================

def save_data():
try:
payload = {
“users”: {str(k): v for k, v in users.items()},
“menu”: menu,
“orders”: {str(k): v for k, v in orders.items()},
“order_counter”: order_counter[0],
“stats”: stats,
}
with open(DATA_FILE, “w”, encoding=“utf-8”) as fh:
json.dump(payload, fh, ensure_ascii=False, indent=2)
except Exception as exc:
log.error(“save_data xatosi: %s”, exc)

def load_data():
global users, menu, orders, stats
if not os.path.exists(DATA_FILE):
return
try:
with open(DATA_FILE, “r”, encoding=“utf-8”) as fh:
payload = json.load(fh)
users = {int(k): v for k, v in payload.get(“users”, {}).items()}
menu = payload.get(“menu”, {})
orders = {int(k): v for k, v in payload.get(“orders”, {}).items()}
order_counter[0] = payload.get(“order_counter”, 0)
stats.update(payload.get(“stats”, {}))
log.info(“Yuklandi: %d mijoz, %d buyurtma”, len(users), len(orders))
except Exception as exc:
log.error(“load_data xatosi: %s”, exc)

# ================================================================

# YORDAMCHI

# ================================================================

def is_admin(uid):
return uid == ADMIN_ID

def today_str():
return datetime.now().strftime(”%d.%m.%Y”)

def week_key():
now = datetime.now()
return (now - timedelta(days=now.weekday())).strftime(”%d.%m.%Y”)

def gmap(lat, lon):
return “https://maps.google.com/?q=” + str(lat) + “,” + str(lon)

def item_price(item):
if isinstance(item, dict):
return int(item.get(“price”, 0))
return int(item)

def item_photo(item):
if isinstance(item, dict):
return item.get(“photo_id”) or None
return None

def admin_kb():
return ReplyKeyboardMarkup(
[
[“📋 Menyu kiritish”, “📦 Buyurtmalar”],
[“📢 Xabar yuborish”, “📊 Hisobot”],
[“👥 Mijozlar”],
],
resize_keyboard=True,
)

def user_kb():
return ReplyKeyboardMarkup(
[
[“🍽 Buyurtma berish”],
[“📦 Buyurtmalarim”, “👤 Profilim”],
],
resize_keyboard=True,
)

def main_kb(uid):
return admin_kb() if is_admin(uid) else user_kb()

def cart_total(cart):
total = 0
for name, qty in cart.items():
if name in menu:
total += qty * item_price(menu[name])
return total

def cart_summary(cart):
rows = []
for name, qty in cart.items():
if name in menu and qty > 0:
p = item_price(menu[name])
rows.append(”  - “ + name + “ x” + str(qty) + “ = “ + str(qty * p) + “ so’m”)
return “\n”.join(rows)

def order_text_for_admin(order, user):
lines = “\n”.join(
“  - “ + i[“name”] + “ x” + str(i[“qty”]) + “ = “ + str(i[“qty”] * i[“price”]) + “ so’m”
for i in order[“items”]
)
statuses = {
“new”: “Yangi”,
“cooking”: “Tayyorlanmoqda”,
“delivering”: “Yetkazilmoqda”,
“delivered”: “Yetkazildi”,
“cancelled”: “Bekor”,
}
status = statuses.get(order.get(“status”, “new”), “Yangi”)
lat = user.get(“lat”)
lon = user.get(“lon”)
if lat and lon:
loc = “Manzil: “ + user.get(“address”, “?”) + “\nXarita: “ + gmap(lat, lon)
else:
loc = “Manzil: “ + user.get(“address”, “Noma’lum”)
return (
“🔔 Buyurtma #” + str(order[“id”]) + “\n\n”
+ “👤 “ + user.get(“name”, “?”) + “\n”
+ “📞 “ + user.get(“phone”, “?”) + “\n”
+ loc + “\n\n”
+ “Tarkib:\n” + lines + “\n\n”
+ “💰 Jami: “ + str(order[“total”]) + “ so’m\n”
+ “📌 Holat: “ + status + “\n”
+ “🕐 “ + order[“time”]
)

# ================================================================

# /start

# ================================================================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id

```
if is_admin(uid):
    await update.message.reply_text(
        "Salom Admin! Boshqaruv paneliga xush kelibsiz.",
        reply_markup=admin_kb(),
    )
    return ConversationHandler.END

# Ro'yxatdan o'tgan mijoz
if uid in users:
    u = users[uid]
    if menu:
        mlines = "\n".join(
            "  - " + n + ": " + str(item_price(v)) + " so'm"
            for n, v in menu.items()
        )
        msg = "Bugungi menyu:\n" + mlines
    else:
        msg = "Bugungi menyu hali tayyor emas."
    await update.message.reply_text(
        "Qaytib keldingiz, " + u["name"] + "!\n\n" + msg,
        reply_markup=user_kb(),
    )
    return ConversationHandler.END

# Yangi mijoz
await update.message.reply_text(
    "Gulcha Taom botiga xush kelibsiz!\n\n"
    "Toshkentdagi eng mazali tushliklar eshigingizgacha!\n\n"
    "Ismingizni kiriting:",
    reply_markup=ReplyKeyboardRemove(),
)
return REG_NAME
```

# ================================================================

# RO’YXATDAN O’TISH — faqat ism va telefon

# ================================================================

async def reg_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
ctx.user_data[“reg_name”] = update.message.text.strip()
kb = [[KeyboardButton(“📱 Telefon raqamni yuborish”, request_contact=True)]]
await update.message.reply_text(
“Telefon raqamingizni yuboring:”,
reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
)
return REG_PHONE

async def reg_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if update.message.contact:
phone = update.message.contact.phone_number
if not phone.startswith(”+”):
phone = “+” + phone
else:
phone = update.message.text.strip()

```
uid = update.effective_user.id
users[uid] = {
    "name": ctx.user_data["reg_name"],
    "phone": phone,
    "address": None,
    "lat": None,
    "lon": None,
    "joined": today_str(),
    "orders": [],
    "total_spent": 0,
    "order_count": 0,
    "favorite_items": {},
    "vip": False,
    "last_order": None,
}
save_data()

await update.message.reply_text(
    "Royxatdan otdingiz!\n\n"
    "Ism: " + users[uid]["name"] + "\n"
    "Tel: " + phone + "\n\n"
    "Endi buyurtma berishingiz mumkin!",
    reply_markup=user_kb(),
)
return ConversationHandler.END
```

# ================================================================

# BUYURTMA BERISH

# ================================================================

async def order_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
if uid not in users:
await update.message.reply_text(“Avval /start bosing.”)
return ConversationHandler.END
if not menu:
await update.message.reply_text(“Bugungi menyu hali tayyor emas.”)
return ConversationHandler.END

```
ctx.user_data["cart"] = {}
ctx.user_data["menu_keys"] = list(menu.keys())
ctx.user_data["menu_idx"] = 0
return await show_item(update, ctx, is_cb=False)
```

def make_item_kb(name, qty, cart, idx, total_items):
nav = []
if idx > 0:
nav.append(InlineKeyboardButton(“◀️”, callback_data=“m_prev”))
nav.append(InlineKeyboardButton(
str(idx + 1) + “/” + str(total_items), callback_data=“m_noop”
))
if idx < total_items - 1:
nav.append(InlineKeyboardButton(“▶️”, callback_data=“m_next”))

```
qty_row = [
    InlineKeyboardButton("➖", callback_data="m_minus"),
    InlineKeyboardButton(str(qty) + " ta", callback_data="m_noop"),
    InlineKeyboardButton("➕", callback_data="m_plus"),
]

rows = [nav, qty_row]

if cart:
    t = cart_total(cart)
    rows.append([InlineKeyboardButton(
        "✅ Buyurtma berish — " + str(t) + " so'm",
        callback_data="m_order",
    )])

return InlineKeyboardMarkup(rows)
```

async def show_item(update, ctx, is_cb=True):
cart = ctx.user_data.get(“cart”, {})
keys = ctx.user_data.get(“menu_keys”, [])
idx = ctx.user_data.get(“menu_idx”, 0)

```
if not keys or idx >= len(keys):
    return MENU_BROWSE

name = keys[idx]
if name not in menu:
    return MENU_BROWSE

m = menu[name]
price = item_price(m)
photo = item_photo(m)
qty = cart.get(name, 0)

# Savatcha
cart_info = ""
if cart:
    s = cart_summary(cart)
    t = cart_total(cart)
    cart_info = "\n\n🛒 Savatcha:\n" + s + "\nJami: " + str(t) + " so'm"

text = "🍽 " + name + "\n💰 " + str(price) + " so'm" + cart_info
kb = make_item_kb(name, qty, cart, idx, len(keys))

if is_cb:
    query = update.callback_query
    if photo:
        try:
            await query.message.delete()
        except Exception:
            pass
        await ctx.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=photo,
            caption=text,
            reply_markup=kb,
        )
    else:
        try:
            await query.edit_message_text(text, reply_markup=kb)
        except Exception:
            await ctx.bot.send_message(
                chat_id=query.message.chat_id,
                text=text,
                reply_markup=kb,
            )
else:
    if photo:
        await update.message.reply_photo(
            photo=photo, caption=text, reply_markup=kb
        )
    else:
        await update.message.reply_text(text, reply_markup=kb)

return MENU_BROWSE
```

async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
data = query.data
cart = ctx.user_data.get(“cart”, {})
keys = ctx.user_data.get(“menu_keys”, [])
idx = ctx.user_data.get(“menu_idx”, 0)

```
if data == "m_noop":
    return MENU_BROWSE

if data == "m_next":
    if idx < len(keys) - 1:
        ctx.user_data["menu_idx"] = idx + 1
    return await show_item(update, ctx, is_cb=True)

if data == "m_prev":
    if idx > 0:
        ctx.user_data["menu_idx"] = idx - 1
    return await show_item(update, ctx, is_cb=True)

if data == "m_plus":
    name = keys[idx]
    cart[name] = cart.get(name, 0) + 1
    ctx.user_data["cart"] = cart
    return await show_item(update, ctx, is_cb=True)

if data == "m_minus":
    name = keys[idx]
    if cart.get(name, 0) > 0:
        cart[name] -= 1
        if cart[name] == 0:
            del cart[name]
    ctx.user_data["cart"] = cart
    return await show_item(update, ctx, is_cb=True)

if data == "m_order":
    if not cart:
        await query.answer("Savatcha bo'sh!", show_alert=True)
        return MENU_BROWSE
    # Manzil so'rash
    return await ask_address(update, ctx)

return MENU_BROWSE
```

# ================================================================

# MANZIL SO’RASH (buyurtma vaqtida)

# ================================================================

async def ask_address(update, ctx):
uid = update.effective_user.id
u = users.get(uid, {})

```
# Oldingi manzil bor — qayta so'ramaymiz
if u.get("address"):
    return await place_order(update, ctx, use_saved=True)

# Birinchi marta — manzil so'raymiz
kb = [
    [KeyboardButton("📍 Lokatsiyamni yuborish", request_location=True)],
    [KeyboardButton("✏️ Manzilni matn bilan kiriting")],
]
query = update.callback_query
await ctx.bot.send_message(
    chat_id=query.message.chat_id,
    text=(
        "Yetkazib berish manzilingizni yuboring.\n\n"
        "📍 Lokatsiya yuborsangiz kuryer aniq topadi.\n"
        "Yoki ko'cha nomi, uy raqamini matn bilan yozing."
    ),
    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
)
return ORDER_ADDRESS
```

async def receive_address(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id

```
if update.message.location:
    lat = update.message.location.latitude
    lon = update.message.location.longitude
    address = str(round(lat, 5)) + ", " + str(round(lon, 5))
else:
    lat, lon = None, None
    address = update.message.text.strip()

# Manzilni saqlash
users[uid]["address"] = address
users[uid]["lat"] = lat
users[uid]["lon"] = lon
save_data()

return await place_order(update, ctx, use_saved=False)
```

# ================================================================

# BUYURTMANI JOYLASH

# ================================================================

async def place_order(update, ctx, use_saved=True):
uid = update.callback_query.from_user.id if hasattr(update, ‘callback_query’) and update.callback_query else update.effective_user.id
user = users[uid]
cart = ctx.user_data.get(“cart”, {})

```
total = cart_total(cart)
items = [
    {"name": n, "qty": q, "price": item_price(menu[n]) if n in menu else 0}
    for n, q in cart.items() if q > 0
]

order_counter[0] += 1
oid = order_counter[0]
now = datetime.now().strftime("%d.%m.%Y %H:%M")
td = today_str()
wk = week_key()

order = {
    "id": oid,
    "user_id": uid,
    "items": items,
    "payment": "cash",
    "total": total,
    "time": now,
    "status": "new",
    "rated": False,
    "rating": 0,
}
orders[oid] = order

# CRM yangilash
users[uid].setdefault("orders", []).append(oid)
users[uid]["total_spent"] = users[uid].get("total_spent", 0) + total
users[uid]["order_count"] = users[uid].get("order_count", 0) + 1
users[uid]["last_order"] = now
fav = users[uid].setdefault("favorite_items", {})
for it in items:
    fav[it["name"]] = fav.get(it["name"], 0) + it["qty"]
if users[uid]["order_count"] >= 5 or users[uid]["total_spent"] >= 500000:
    users[uid]["vip"] = True

# Statistika
stats["total_orders"] += 1
stats["total_revenue"] += total
stats["daily"][td] = stats["daily"].get(td, 0) + 1
stats["weekly"][wk] = stats["weekly"].get(wk, 0) + 1
save_data()

# Mijozga tasdiqlash
confirm_text = (
    "✅ Buyurtmangiz qabul qilindi!\n\n"
    "Buyurtma #" + str(oid) + "\n"
    "Jami: " + str(total) + " so'm\n"
    "Tolov: Naqd (yetkazganda)\n"
    "Manzil: " + user.get("address", "?") + "\n\n"
    "🚚 Tez orada yetkazib boramiz!"
)

# Xabar yuborish usuli
if hasattr(update, 'callback_query') and update.callback_query:
    chat_id = update.callback_query.message.chat_id
    await ctx.bot.send_message(chat_id=chat_id, text=confirm_text, reply_markup=user_kb())
else:
    await update.message.reply_text(confirm_text, reply_markup=user_kb())

# Adminga xabar
if ADMIN_ID:
    try:
        lat = user.get("lat")
        lon = user.get("lon")
        if lat and lon:
            await ctx.bot.send_location(
                chat_id=ADMIN_ID, latitude=lat, longitude=lon
            )
        admin_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("👨‍🍳 Tayyorlanmoqda", callback_data="st_" + str(oid) + "_cooking")],
            [InlineKeyboardButton("🚚 Yetkazilmoqda", callback_data="st_" + str(oid) + "_delivering")],
            [InlineKeyboardButton("✅ Yetkazildi", callback_data="st_" + str(oid) + "_delivered")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="st_" + str(oid) + "_cancelled")],
        ])
        await ctx.bot.send_message(
            chat_id=ADMIN_ID,
            text=order_text_for_admin(order, user),
            reply_markup=admin_buttons,
        )
    except Exception as exc:
        log.error("Admin xabari yuborilmadi: %s", exc)

ctx.user_data["cart"] = {}
return ConversationHandler.END
```

# ================================================================

# BUYURTMA HOLATI (ADMIN)

# ================================================================

async def status_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()

```
if not is_admin(update.effective_user.id):
    return

parts = query.data.split("_")
oid = int(parts[1])
new_status = parts[2]

if oid not in orders:
    return

orders[oid]["status"] = new_status
save_data()

user = users.get(orders[oid]["user_id"], {})
try:
    await query.edit_message_text(order_text_for_admin(orders[oid], user))
except Exception:
    pass

uid = orders[oid]["user_id"]
msgs = {
    "cooking": "Buyurtma #" + str(oid) + " tayyorlanmoqda!",
    "delivering": "🚚 Buyurtma #" + str(oid) + " yolda! Tez orada yetkazamiz!",
    "cancelled": "❌ Buyurtma #" + str(oid) + " bekor qilindi. Kechirasiz!",
}

if new_status == "delivered":
    rate_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("1⭐", callback_data="rate_" + str(oid) + "_1"),
        InlineKeyboardButton("2⭐", callback_data="rate_" + str(oid) + "_2"),
        InlineKeyboardButton("3⭐", callback_data="rate_" + str(oid) + "_3"),
        InlineKeyboardButton("4⭐", callback_data="rate_" + str(oid) + "_4"),
        InlineKeyboardButton("5⭐", callback_data="rate_" + str(oid) + "_5"),
    ]])
    try:
        await ctx.bot.send_message(
            uid,
            "✅ Buyurtma #" + str(oid) + " yetkazildi!\nIltimos, taomni baholang:",
            reply_markup=rate_kb,
        )
    except Exception:
        pass
elif new_status in msgs:
    try:
        await ctx.bot.send_message(uid, msgs[new_status])
    except Exception:
        pass
```

# ================================================================

# BAHOLASH

# ================================================================

async def rate_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()

```
parts = query.data.split("_")
oid = int(parts[1])
rating = int(parts[2])

if oid in orders and not orders[oid].get("rated"):
    orders[oid]["rating"] = rating
    orders[oid]["rated"] = True
    save_data()

try:
    await query.edit_message_text(
        "Rahmat! " + str(rating) + "/5\nBahoingiz qabul qilindi!"
    )
except Exception:
    pass

if ADMIN_ID:
    try:
        u = users.get(orders[oid]["user_id"], {})
        await ctx.bot.send_message(
            ADMIN_ID,
            "Baho: Buyurtma #" + str(oid) + " - " + u.get("name", "?") + " - " + str(rating) + "/5",
        )
    except Exception:
        pass
```

# ================================================================

# MENING BUYURTMALARIM

# ================================================================

async def my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
if uid not in users:
await update.message.reply_text(“Avval /start bosing.”)
return

```
oids = users[uid].get("orders", [])
if not oids:
    await update.message.reply_text("Siz hali buyurtma bermagansiz.")
    return

status_names = {
    "new": "Yangi",
    "cooking": "Tayyorlanmoqda",
    "delivering": "Yolda",
    "delivered": "Yetkazildi",
    "cancelled": "Bekor",
}
text = "Oxirgi buyurtmalaringiz:\n\n"
for oid in reversed(oids[-5:]):
    if oid in orders:
        o = orders[oid]
        items_str = ", ".join(
            i["name"] + " x" + str(i["qty"]) for i in o["items"]
        )
        st = status_names.get(o.get("status", "new"), "Yangi")
        rating_str = " | " + str(o["rating"]) + "/5" if o.get("rated") else ""
        text += (
            "#" + str(oid) + " | " + o["time"] + "\n"
            + items_str + "\n"
            + str(o["total"]) + " som | " + st + rating_str + "\n\n"
        )
await update.message.reply_text(text)
```

# ================================================================

# PROFIL

# ================================================================

async def my_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
if uid not in users:
await update.message.reply_text(“Avval /start bosing.”)
return

```
u = users[uid]
fav_items = u.get("favorite_items", {})
fav = max(fav_items, key=fav_items.get) if fav_items else "-"
vip = "👑 VIP" if u.get("vip") else "Oddiy"
lat = u.get("lat")
lon = u.get("lon")
map_url = "\nXarita: " + gmap(lat, lon) if lat and lon else ""

text = (
    "Profilingiz:\n\n"
    "Ism: " + u["name"] + "\n"
    "Tel: " + u["phone"] + "\n"
    "Manzil: " + (u.get("address") or "Kiritilmagan") + map_url + "\n"
    "Royxat: " + u.get("joined", "?") + "\n\n"
    "Statistika:\n"
    "Buyurtmalar: " + str(u.get("order_count", 0)) + " ta\n"
    "Jami xarid: " + str(u.get("total_spent", 0)) + " so'm\n"
    "Sevimli taom: " + fav + "\n"
    "Status: " + vip
)

# Manzil yangilash tugmasi
kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("📍 Manzilni yangilash", callback_data="update_address")]
])
await update.message.reply_text(text, reply_markup=kb)
```

async def update_address_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
kb = [
[KeyboardButton(“📍 Lokatsiyamni yuborish”, request_location=True)],
[KeyboardButton(“✏️ Matn bilan kiriting”)],
]
await ctx.bot.send_message(
chat_id=query.message.chat_id,
text=“Yangi manzilingizni yuboring:”,
reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
)
ctx.user_data[“updating_address”] = True
return

async def address_text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
if not ctx.user_data.get(“updating_address”):
return

```
if update.message.location:
    lat = update.message.location.latitude
    lon = update.message.location.longitude
    address = str(round(lat, 5)) + ", " + str(round(lon, 5))
else:
    lat, lon = None, None
    address = update.message.text.strip()

if uid in users:
    users[uid]["address"] = address
    users[uid]["lat"] = lat
    users[uid]["lon"] = lon
    save_data()

ctx.user_data["updating_address"] = False
msg = "Manzil yangilandi!\n" + address
if lat and lon:
    msg += "\nXarita: " + gmap(lat, lon)
await update.message.reply_text(msg, reply_markup=user_kb())
```

# ================================================================

# ADMIN: MENYU KIRITISH

# ================================================================

async def admin_menu_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return ConversationHandler.END
menu.clear()
ctx.user_data[“menu_active”] = True
await update.message.reply_text(
“Bugungi menyuni kiriting.\n\n”
“Har bir taom uchun:\n”
“Rasmsiz: Taom nomi - narx\n”
“Rasmli: Rasmni yuboring, caption da: Taom nomi - narx\n\n”
“Masalan: Osh - 25000\n\n”
“Tugagach /done yuboring.”
)
return ADMIN_MENU_INPUT

async def admin_menu_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not ctx.user_data.get(“menu_active”):
return ConversationHandler.END

```
raw = update.message.text.strip()
if " - " not in raw:
    await update.message.reply_text("Format notogri. Masalan: Osh - 25000")
    return ADMIN_MENU_INPUT

name, price_str = raw.split(" - ", 1)
name = name.strip()
price_str = price_str.strip().replace(",", "").replace(" ", "")
if not price_str.isdigit():
    await update.message.reply_text("Narx faqat raqam bolishi kerak.")
    return ADMIN_MENU_INPUT

price = int(price_str)
menu[name] = {"price": price, "photo_id": None}
await update.message.reply_text(name + " - " + str(price) + " so'm qoshildi.")
return ADMIN_MENU_INPUT
```

async def admin_menu_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not ctx.user_data.get(“menu_active”):
return ConversationHandler.END

```
caption = (update.message.caption or "").strip()
if " - " not in caption:
    await update.message.reply_text("Caption: Taom nomi - narx")
    return ADMIN_MENU_INPUT

name, price_str = caption.split(" - ", 1)
name = name.strip()
price_str = price_str.strip().replace(",", "").replace(" ", "")
if not price_str.isdigit():
    await update.message.reply_text("Narx faqat raqam bolishi kerak.")
    return ADMIN_MENU_INPUT

price = int(price_str)
photo_id = update.message.photo[-1].file_id
menu[name] = {"price": price, "photo_id": photo_id}
await update.message.reply_text(name + " - " + str(price) + " so'm (rasmli) qoshildi.")
return ADMIN_MENU_INPUT
```

async def admin_menu_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
ctx.user_data[“menu_active”] = False
if not menu:
await update.message.reply_text(“Hech narsa kiritilmadi.”)
return ConversationHandler.END

```
save_data()
lines = []
for n, v in menu.items():
    icon = "[rasm] " if isinstance(v, dict) and v.get("photo_id") else ""
    lines.append(icon + n + " - " + str(item_price(v)) + " so'm")

await update.message.reply_text(
    "Menyu saqlandi (" + str(len(menu)) + " ta taom):\n\n" + "\n".join(lines)
)
return ConversationHandler.END
```

# ================================================================

# ADMIN: BUYURTMALAR

# ================================================================

async def admin_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return

```
td = today_str()
today_orders = [o for o in orders.values() if o["time"].startswith(td)]

if not today_orders:
    await update.message.reply_text("Bugun hali buyurtma yoq.")
    return

revenue = sum(o["total"] for o in today_orders)
status_names = {
    "new": "[yangi]",
    "cooking": "[pishiryapti]",
    "delivering": "[yolda]",
    "delivered": "[yetkazildi]",
    "cancelled": "[bekor]",
}
text = "Bugungi buyurtmalar (" + str(len(today_orders)) + " ta):\n\n"
for o in today_orders:
    u = users.get(o["user_id"], {})
    items_str = ", ".join(
        i["name"] + " x" + str(i["qty"]) for i in o["items"]
    )
    st = status_names.get(o.get("status", "new"), "[yangi]")
    text += (
        st + " #" + str(o["id"]) + " | " + u.get("name", "?")
        + " | " + items_str + " | " + str(o["total"]) + " so'm\n"
    )
text += "\nJami: " + str(revenue) + " so'm"
await update.message.reply_text(text)
```

# ================================================================

# ADMIN: MIJOZLAR

# ================================================================

async def admin_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return

```
if not users:
    await update.message.reply_text("Hali mijoz yoq.")
    return

td = today_str()
vip_count = sum(1 for u in users.values() if u.get("vip"))
active = len({o["user_id"] for o in orders.values() if o["time"].startswith(td)})

text = (
    "Mijozlar bazasi\n\n"
    "Jami: " + str(len(users)) + " ta\n"
    "VIP: " + str(vip_count) + " ta\n"
    "Bugun faol: " + str(active) + " ta\n\n"
    "-------------------------\n\n"
)

for uid, u in users.items():
    icon = "[VIP] " if u.get("vip") else ""
    lat = u.get("lat")
    lon = u.get("lon")
    map_link = "\n" + gmap(lat, lon) if lat and lon else ""
    last = u.get("last_order") or u.get("joined", "?")
    text += (
        icon + u["name"] + "\n"
        + u["phone"] + map_link + "\n"
        + str(u.get("order_count", 0)) + " buyurtma | " + str(u.get("total_spent", 0)) + " so'm\n"
        + "Oxirgi: " + last + "\n\n"
    )
    if len(text) > 3500:
        await update.message.reply_text(text)
        text = ""

if text:
    await update.message.reply_text(text)
```

# ================================================================

# ADMIN: XABAR YUBORISH

# ================================================================

async def admin_broadcast_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return ConversationHandler.END
await update.message.reply_text(
“Barcha “ + str(len(users)) + “ ta mijozga xabar yozing:\n(/cancel - bekor)”
)
return ADMIN_BROADCAST

async def admin_broadcast_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
text = update.message.text
sent = failed = 0
for uid in users:
try:
await ctx.bot.send_message(uid, text)
sent += 1
except Exception:
failed += 1
await update.message.reply_text(
“Xabar yuborildi!\nYuborildi: “ + str(sent) + “\nYuborilmadi: “ + str(failed)
)
return ConversationHandler.END

# ================================================================

# ADMIN: HISOBOT

# ================================================================

async def admin_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return

```
td = today_str()
today_orders = [o for o in orders.values() if o["time"].startswith(td)]
today_rev = sum(o["total"] for o in today_orders)

wk = week_key()
week_count = stats["weekly"].get(wk, 0)

rated = [o for o in orders.values() if o.get("rated")]
avg_rating = sum(o["rating"] for o in rated) / len(rated) if rated else 0

best_day = max(stats["daily"], key=stats["daily"].get) if stats["daily"] else "-"
best_count = stats["daily"].get(best_day, 0)
avg_check = stats["total_revenue"] // stats["total_orders"] if stats["total_orders"] else 0
vip_count = sum(1 for u in users.values() if u.get("vip"))

item_counts = {}
for o in orders.values():
    for i in o["items"]:
        item_counts[i["name"]] = item_counts.get(i["name"], 0) + i["qty"]
top = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:3]
top_text = "\n".join(
    str(i + 1) + ". " + n + " - " + str(c) + " ta"
    for i, (n, c) in enumerate(top)
) or "-"

text = (
    "To'liq hisobot\n\n"
    "Bugun (" + td + "):\n"
    "  Buyurtmalar: " + str(len(today_orders)) + " ta\n"
    "  Tushum: " + str(today_rev) + " so'm\n\n"
    "Bu hafta: " + str(week_count) + " ta\n\n"
    "Jami:\n"
    "  Buyurtmalar: " + str(stats["total_orders"]) + " ta\n"
    "  Tushum: " + str(stats["total_revenue"]) + " so'm\n"
    "  Ortacha chek: " + str(avg_check) + " so'm\n"
    "  Mijozlar: " + str(len(users)) + " ta\n"
    "  VIP: " + str(vip_count) + " ta\n"
    "  Ortacha baho: " + str(round(avg_rating, 1)) + "/5\n"
    "  Eng faol kun: " + best_day + " (" + str(best_count) + " ta)\n\n"
    "Top mahsulotlar:\n" + top_text
)
await update.message.reply_text(text)
```

# ================================================================

# CANCEL

# ================================================================

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
ctx.user_data.clear()
await update.message.reply_text(
“Bekor qilindi.”,
reply_markup=main_kb(update.effective_user.id),
)
return ConversationHandler.END

# ================================================================

# MAIN

# ================================================================

def main():
load_data()

```
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable ornatilmagan!")

app = Application.builder().token(TOKEN).build()

# Ro'yxatdan o'tish
reg_conv = ConversationHandler(
    entry_points=[CommandHandler("start", cmd_start)],
    states={
        REG_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)
        ],
        REG_PHONE: [
            MessageHandler(filters.CONTACT, reg_phone),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
)

# Buyurtma + manzil
order_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^Buyurtma berish$"), order_start)
    ],
    states={
        MENU_BROWSE: [
            CallbackQueryHandler(menu_callback)
        ],
        ORDER_ADDRESS: [
            MessageHandler(filters.LOCATION, receive_address),
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Menyu kiritish
menu_conv = ConversationHandler(
    entry_points=[
        CommandHandler("menyu", admin_menu_start),
        MessageHandler(filters.Regex("^Menyu kiritish$"), admin_menu_start),
    ],
    states={
        ADMIN_MENU_INPUT: [
            MessageHandler(filters.PHOTO, admin_menu_photo),
            CommandHandler("done", admin_menu_done),
            MessageHandler(filters.TEXT & ~filters.COMMAND, admin_menu_text),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Broadcast
broadcast_conv = ConversationHandler(
    entry_points=[
        CommandHandler("xabar", admin_broadcast_start),
        MessageHandler(filters.Regex("^Xabar yuborish$"), admin_broadcast_start),
    ],
    states={
        ADMIN_BROADCAST: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_send)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(reg_conv)
app.add_handler(order_conv)
app.add_handler(menu_conv)
app.add_handler(broadcast_conv)

# Callback handlerlar
app.add_handler(CallbackQueryHandler(status_callback, pattern="^st_"))
app.add_handler(CallbackQueryHandler(rate_callback, pattern="^rate_"))
app.add_handler(CallbackQueryHandler(update_address_callback, pattern="^update_address$"))

# Admin tugmalar
app.add_handler(MessageHandler(filters.Regex("^Buyurtmalar$"), admin_orders))
app.add_handler(MessageHandler(filters.Regex("^Hisobot$"), admin_report))
app.add_handler(MessageHandler(filters.Regex("^Mijozlar$"), admin_users))

# Foydalanuvchi tugmalar
app.add_handler(MessageHandler(filters.Regex("^Buyurtmalarim$"), my_orders))
app.add_handler(MessageHandler(filters.Regex("^Profilim$"), my_profile))

# Manzil yangilash (profil orqali)
app.add_handler(MessageHandler(
    (filters.LOCATION | filters.TEXT) & ~filters.COMMAND,
    address_text_handler
))

print("Bot ishga tushdi!")
app.run_polling(drop_pending_updates=True)
```

if **name** == “**main**”:
main()
