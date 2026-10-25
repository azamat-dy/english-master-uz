import asyncio, os, logging
import aiosqlite
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import (Message, InlineKeyboardMarkup as KB, InlineKeyboardButton as Btn,
                          WebAppInfo, MenuButtonWebApp)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
LEARN_URL = os.getenv("LEARN_URL", "https://english-master-uz.netlify.app/")   # 1-sahifa: darslar
AI_URL = os.getenv("AI_URL", "https://azamat-ai.netlify.app/")               # 2-sahifa: AI Ustoz
MUSIC_URL = os.getenv("MUSIC_URL", "https://www.youtube.com/")               # 3-sahifa: English Master Music
r = Router()


def menu():
    return KB(inline_keyboard=[
        [Btn(text="📚 English Master", web_app=WebAppInfo(url=LEARN_URL))],
        [Btn(text="🤖 AI Ustoz", web_app=WebAppInfo(url=AI_URL))],
        [Btn(text="🎵 English Master Music", web_app=WebAppInfo(url=MUSIC_URL))],
    ])


async def save_user(m: Message):
    """Foydalanuvchini jimgina bazaga yozib qo'yadi (keyinchalik statistika uchun)."""
    async with aiosqlite.connect("progress.db") as d:
        await d.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,xp INTEGER DEFAULT 0)")
        await d.execute("INSERT OR IGNORE INTO users(id,name) VALUES(?,?)", (m.from_user.id, m.from_user.full_name))
        await d.commit()


@r.message(CommandStart())
async def start(m: Message):
    await save_user(m)
    s = await m.answer("🎓")
    for f in ["🎓 E", "🎓 English", "🎓 English Master ✨"]:
        await asyncio.sleep(0.4)
        try: await s.edit_text(f)
        except Exception: pass
    await m.answer(f"Salom, {m.from_user.first_name}! 👋\n\nIngliz tilini Beginner'dan Advanced'gacha o'rganing 👇",
                   reply_markup=menu())


@r.message(Command("menu"))
async def show_menu(m: Message):
    await m.answer("Tanlang 👇", reply_markup=menu())


@r.message()
async def other(m: Message):
    await m.answer("Quyidagi tugmalardan birini tanlang 👇", reply_markup=menu())


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN)
    try:   # chat pastidagi "Open" tugmasi ham darslar sahifasini ochadi
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="📚 Ochish", web_app=WebAppInfo(url=LEARN_URL)))
    except Exception as e:
        logging.warning("Menu tugmasi o'rnatilmadi: %s", e)
    dp = Dispatcher(); dp.include_router(r)
    print("Bot ishga tushdi. Darslar:", LEARN_URL, "| AI:", AI_URL, "| Music:", MUSIC_URL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
