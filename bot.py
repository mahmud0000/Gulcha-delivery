import logging
import os
import json
import sys
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

# ==============================================================
# SOZLAMALAR
# ==============================================================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATA_FILE = "data.json"

# CONVERSATION STATES
(
    REG_NAME, REG_PHONE, REG_LOCATION, MENU_BROWSE, UPSELL,
    CONFIRM, ADMIN_MENU_INPUT, ADMIN_BROADCAST, CHANGE_LOCATION,
) = range(9)

# GLOBAL MA'LUMOTLAR
users = {}
menu = {}
orders = {}
order_counter = [0]
stats = {"total_orders": 0, "total_revenue": 0, "daily": {}, "weekly": {}}

UPSELL_ITEMS = [
    {"name": "🥤 Cola", "price": 8000},
    {"name": "🍞 Non", "price": 3000},
    {"name": "🥗 Salat", "price": 12000},
]

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO, stream=sys.stdout)
log = logging.getLogger(__name__)

# ==============================================================
# DATA FUNCTIONS
# ==============================================================
def save_data():
    try:
        payload = {
            "users": {str(k): v for k, v in users.items()},
            "menu": menu,
            "orders": {str(k): v for k, v in orders.items()},
            "order_counter": order_counter[0],
            "stats": stats,
        }
        with open(DATA_FILE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("save_data xatosi: %s", exc)

def load_data():
    global users, menu, orders, stats
    if not os.path.exists(DATA_FILE): return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
            users = {int(k): v for k, v in payload.get("users", {}).items()}
            menu = payload.get("menu", {})
            orders = {int(k): v for k, v in payload.get("orders", {}).items()}
            order_counter[0] = payload.get("order_counter", 0)
            stats.update(payload.get("stats", {}))
    except Exception as exc:
        log.error("load_data xatosi: %s", exc)

# ==============================================================
# KEYBOARDS & HELPERS
# ==============================================================
def is_admin(uid): return uid == ADMIN_ID
def today_str(): return datetime.now().strftime("%d.%m.%Y")
def gmap(lat, lon): return f"https://www.google.com/maps?q={lat},{lon}"

def admin_keyboard():
    return ReplyKeyboardMarkup([["📋 Menyu kiritish", "📦 Buyurtmalar"], ["📢 Xabar yuborish", "📊 Hisobot"], ["👥 Mijozlar bazasi"]], resize_keyboard=True)

def user_keyboard():
    return ReplyKeyboardMarkup([["🍽 Buyurtma berish"], ["📦 Buyurtmalarim", "👤 Profilim"], ["📍 Manzilni yangilash"]], resize_keyboard=True)

def cart_total(cart):
    return sum(qty * menu[name]["price"] for name, qty in cart.items() if name in menu)

def cart_lines(cart):
    return "\n".join(f"  • {n} x{q} — {q * menu[n]['price']:,} so'm" for n, q in cart.items() if n in menu)

# ==============================================================
# HANDLERS (USER SIDE)
# ==============================================================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_admin(uid):
        await update.message.reply_text("👋 Salom, Admin!", reply_markup=admin_keyboard())
        return ConversationHandler.END
    if uid in users:
        await update.message.reply_text(f"👋 Qaytib keldingiz, {users[uid]['name']}!", reply_markup=user_keyboard())
        return ConversationHandler.END
    await update.message.reply_text("👋 Gulcha Taom botiga xush kelibsiz!\nIsmingizni kiriting:", reply_markup=ReplyKeyboardRemove())
    return REG_NAME

async def reg_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["reg_name"] = update.message.text
    kb = [[KeyboardButton("📱 Telefonni yuborish", request_contact=True)]]
    await update.message.reply_text("📱 Telefon raqamingizni yuboring:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return REG_PHONE

async def reg_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["reg_phone"] = update.message.contact.phone_number if update.message.contact else update.message.text
    kb = [[KeyboardButton("📍 Lokatsiyamni yuborish", request_location=True)]]
    await update.message.reply_text("📍 Yetkazib berish manzilini yuboring:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return REG_LOCATION

async def reg_location(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    loc = update.message.location
    users[uid] = {
        "name": ctx.user_data["reg_name"], "phone": ctx.user_data["reg_phone"],
        "address": f"{loc.latitude}, {loc.longitude}" if loc else update.message.text,
        "lat": loc.latitude if loc else None, "lon": loc.longitude if loc else None,
        "joined": today_str(), "orders": [], "total_spent": 0, "order_count": 0, "favorite_items": {}
    }
    save_data()
    await update.message.reply_text("✅ Ro'yxatdan o'tdingiz!", reply_markup=user_keyboard())
    return ConversationHandler.END

async def order_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not menu:
        await update.message.reply_text("⏳ Menyu hali tayyor emas.")
        return ConversationHandler.END
    ctx.user_data["cart"] = {}
    ctx.user_data["menu_keys"] = list(menu.keys())
    ctx.user_data["menu_idx"] = 0
    return await send_menu_card(update, ctx, False)

async def send_menu_card(update, ctx, from_callback=True):
    keys = ctx.user_data["menu_keys"]
    idx = ctx.user_data["menu_idx"]
    name = keys[idx]
    qty = ctx.user_data["cart"].get(name, 0)
    
    cart_info = f"\n\n🛒 Savatchada:\n{cart_lines(ctx.user_data['cart'])}\n💰 Jami: {cart_total(ctx.user_data['cart']):,} so'm" if ctx.user_data["cart"] else ""
    text = f"🍽 *{name}*\n💰 Narxi: {menu[name]['price']:,} so'm{cart_info}"
    
    kb_rows = [
        [InlineKeyboardButton("➖", callback_data="m_minus"), InlineKeyboardButton(f"{qty} ta", callback_data="none"), InlineKeyboardButton("➕", callback_data="m_plus")],
        [InlineKeyboardButton("◀️ Oldingi", callback_data="m_prev"), InlineKeyboardButton("Keyingi ▶️", callback_data="m_next")]
    ]
    if ctx.user_data["cart"]:
        kb_rows.append([InlineKeyboardButton(f"✅ Buyurtmani tasdiqlash", callback_data="m_checkout")])
    
    kb = InlineKeyboardMarkup(kb_rows)
    if from_callback:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")
    return MENU_BROWSE

async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    idx = ctx.user_data["menu_idx"]
    keys = ctx.user_data["menu_keys"]
    name = keys[idx]

    if data == "m_next" and idx < len(keys)-1: ctx.user_data["menu_idx"] += 1
    elif data == "m_prev" and idx > 0: ctx.user_data["menu_idx"] -= 1
    elif data == "m_plus": ctx.user_data["cart"][name] = ctx.user_data["cart"].get(name, 0) + 1
    elif data == "m_minus" and name in ctx.user_data["cart"]:
        ctx.user_data["cart"][name] -= 1
        if ctx.user_data["cart"][name] == 0: del ctx.user_data["cart"][name]
    elif data == "m_checkout": return await confirm_order(update, ctx)
    
    return await send_menu_card(update, ctx)

async def confirm_order(update, ctx):
    total = cart_total(ctx.user_data["cart"])
    text = f"🛒 *Buyurtmangiz tarkibi:*\n{cart_lines(ctx.user_data['cart'])}\n\n💰 *Jami: {total:,} so'm*\n\nTo'lov turi: 💵 Naqd\n\nBuyurtmani tasdiqlaysizmi?"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Ha, tasdiqlayman", callback_data="cf_yes"), InlineKeyboardButton("❌ Yo'q", callback_data="cf_no")]])
    await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return CONFIRM

async def confirm_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cf_no":
        await query.edit_message_text("Buyurtma bekor qilindi.")
        return ConversationHandler.END

    uid = update.effective_user.id
    order_counter[0] += 1
    oid = order_counter[0]
    total = cart_total(ctx.user_data["cart"])
    
    order = {"id": oid, "user_id": uid, "items": ctx.user_data["cart"], "status": "new", "total": total, "time": today_str()}
    orders[oid] = order
    save_data()

    await query.edit_message_text(f"✅ Rahmat! Buyurtmangiz qabul qilindi.\n📦 *Buyurtma raqami: #{oid}*\n💰 To'lov: {total:,} so'm (naqd)")
    
    if ADMIN_ID:
        try:
            u = users[uid]
            admin_msg = f"🆕 *Yangi buyurtma #{oid}*\n👤 Mijoz: {u['name']}\n📞 Tel: {u['phone']}\n💰 Summa: {total:,} so'm\n\n🍽 Tarkib:\n{cart_lines(ctx.user_data['cart'])}"
            await ctx.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
        except: pass
    return ConversationHandler.END

# ==============================================================
# ADMIN FUNCTIONS
# ==============================================================
async def admin_menu_start(update, ctx):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("📋 Bugungi menyuni kiriting (Format: Taom - Narx):\nTugatish uchun /done bosing.")
    return ADMIN_MENU_INPUT

async def admin_menu_text(update, ctx):
    try:
        name, price = update.message.text.split("-")
        menu[name.strip()] = {"price": int(price.strip().replace(" ","")), "photo_id": None}
        save_data()
        await update.message.reply_text(f"✅ {name.strip()} qo'shildi.")
    except:
        await update.message.reply_text("❌ Xato! Format: Osh - 25000")
    return ADMIN_MENU_INPUT

async def cancel(update, ctx):
    await update.message.reply_text("Bekor qilindi.", reply_markup=user_keyboard())
    return ConversationHandler.END

# ==============================================================
# MAIN
# ==============================================================
def main():
    load_data()
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()

    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, reg_phone)],
            REG_LOCATION: [MessageHandler(filters.LOCATION | filters.TEXT, reg_location)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    order_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🍽 Buyurtma berish$"), order_start)],
        states={
            MENU_BROWSE: [CallbackQueryHandler(menu_callback)],
            CONFIRM: [CallbackQueryHandler(confirm_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    menu_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Menyu kiritish$"), admin_menu_start)],
        states={ADMIN_MENU_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_menu_text), CommandHandler("done", cancel)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(reg_handler)
    app.add_handler(order_handler)
    app.add_handler(menu_handler)
    
    print("🚀 Bot ishga tushdi (Faqat naqd to'lov)")
    app.run_polling()

if __name__ == "__main__":
    main()
