import asyncio, os, logging
import aiosqlite
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup as KB, InlineKeyboardButton as Btn,
                          WebAppInfo, MenuButtonWebApp)
from aiohttp import web

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
LEARN_URL = os.getenv("LEARN_URL", "https://english-master-uz.netlify.app/")   # 1-sahifa: darslar
AI_URL = os.getenv("AI_URL", "https://azamat-ai.netlify.app/")               # 2-sahifa: AI Ustoz
MUSIC_URL = os.getenv("MUSIC_URL", "https://www.youtube.com/")               # 3-sahifa: English Master Music

# Majburiy obuna qilinishi kerak bo'lgan kanallar ro'yxati
CHANNELS = ["@English_Master_uz"]

r = Router()


def menu():
    return KB(inline_keyboard=[
        [Btn(text="📚 English Master", web_app=WebAppInfo(url=LEARN_URL))],
        [Btn(text="🤖 AI Ustoz", web_app=WebAppInfo(url=AI_URL))],
        [Btn(text="🎵 English Master Music", web_app=WebAppInfo(url=MUSIC_URL))],
    ])


def check_sub_markup():
    keyboard = []
    for ch in CHANNELS:
        channel_link = f"https://t.me/{ch.replace('@', '')}"
        keyboard.append([Btn(text="➕ Obuna bo'lish", url=channel_link)])
    
    keyboard.append([Btn(text="✅ Tekshirish", callback_data="check_subscription")])
    return KB(inline_keyboard=keyboard)


async def check_user_channels(bot: Bot, user_id: int) -> bool:
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True


async def save_user(m: Message):
    async with aiosqlite.connect("progress.db") as d:
        await d.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,xp INTEGER DEFAULT 0)")
        await d.execute("INSERT OR IGNORE INTO users(id,name) VALUES(?,?)", (m.from_user.id, m.from_user.full_name))
        await d.commit()


@r.message(CommandStart())
async def start(m: Message, bot: Bot):
    await save_user(m)
    
    is_subscribed = await check_user_channels(bot, m.from_user.id)
    if not is_subscribed:
        await m.answer(
            "Botdan foydalanish uchun quyidagi kanallarimizga obuna bo'ling 👇",
            reply_markup=check_sub_markup()
        )
        return

    s = await m.answer("🎓")
    for f in ["🎓 E", "🎓 English", "🎓 English Master ✨"]:
        await asyncio.sleep(0.4)
        try: await s.edit_text(f)
        except Exception: pass
    await m.answer(f"Salom, {m.from_user.first_name}! 👋\n\nIngliz tilini Beginner'dan Advanced'gacha o'rganing 👇",
                   reply_markup=menu())


@r.callback_query(F.data == "check_subscription")
async def verify_subscription(call: CallbackQuery, bot: Bot):
    is_subscribed = await check_user_channels(bot, call.from_user.id)
    if not is_subscribed:
        await call.answer("❌ Siz hali hamma kanalga obuna bo'lmadingiz!", show_alert=True)
        return
    
    await call.message.delete()
    await call.answer("Rahmat, obuna tasdiqlandi! ✅")
    
    await call.message.answer(
        f"Salom, {call.from_user.first_name}! 👋\n\nIngliz tilini Beginner'dan Advanced'gacha o'rganing 👇",
        reply_markup=menu()
    )


@r.message(Command("menu"))
async def show_menu(m: Message, bot: Bot):
    is_subscribed = await check_user_channels(bot, m.from_user.id)
    if not is_subscribed:
        await m.answer(
            "Botdan foydalanish uchun avval quyidagi kanallarga obuna bo'ling 👇",
            reply_markup=check_sub_markup()
        )
        return
    await m.answer("Tanlang 👇", reply_markup=menu())


@r.message()
async def other(m: Message, bot: Bot):
    is_subscribed = await check_user_channels(bot, m.from_user.id)
    if not is_subscribed:
        await m.answer(
            "Botdan foydalanish uchun avval quyidagi kanallarga obuna bo'ling 👇",
            reply_markup=check_sub_markup()
        )
        return
    await m.answer("Quyidagi tugmalardan birini tanlang 👇", reply_markup=menu())


# Render port talabini qondirish uchun veb-server
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server started on port {port}")


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN)
    try:
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="📚 Ochish", web_app=WebAppInfo(url=LEARN_URL)))
    except Exception as e:
        logging.warning("Menu tugmasi o'rnatilmadi: %s", e)
        
    dp = Dispatcher(); dp.include_router(r)
    
    # Render uchun portni ochamiz
    await start_web_server()
    
    print("Bot ishga tushdi. Darslar:", LEARN_URL, "| AI:", AI_URL, "| Music:", MUSIC_URL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
