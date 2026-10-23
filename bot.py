import asyncio, os, logging
import aiosqlite
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup as KB,
                           InlineKeyboardButton as Btn, BufferedInputFile, WebAppInfo)

load_dotenv()
BOT_TOKEN, WEBAPP_URL = os.getenv("BOT_TOKEN"), os.getenv("WEBAPP_URL")
DB = "progress.db"

# ───────────────────────── AI USTOZ (Claude) ─────────────────────────
try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None
import aiohttp, io, base64
from datetime import date
AI_KEY = os.getenv("ANTHROPIC_API_KEY")
AI = AsyncAnthropic(api_key=AI_KEY) if (AI_KEY and AsyncAnthropic) else None
GKEY = os.getenv("GEMINI_API_KEY")                       # BEPUL: aistudio.google.com/app/apikey
GMODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
AI_MODEL = os.getenv("AI_MODEL", "claude-haiku-5-5")
AI_LIMIT = int(os.getenv("AI_DAILY_LIMIT", "15"))          # bepul foydalanuvchi uchun kunlik savollar
PREMIUM = {int(x) for x in os.getenv("PREMIUM_IDS", "").split(",") if x.strip()}  # cheksiz foydalanuvchilar ID si
HIST, USED = {}, {}
SYS = ("You are 'English Master AI', a friendly, patient English tutor inside a Telegram bot for learners "
       "from Beginner (A1) to Elementary (A2). ALWAYS reply in the language the student writes in "
       "(Uzbek, Russian, English, Turkish, Arabic or any other). If unclear, use Uzbek. "
       "Explain English lessons (grammar, vocabulary, pronunciation, reading, speaking) in simple words, "
       "with short examples and translation into the student's language. Correct mistakes gently and show "
       "the correct version. Keep answers concise (under ~200 words) and use simple A1-A2 English in examples. "
       "You may help with other topics too, but steer back to learning English when natural. "
       "Never invent facts; if unsure, say so.")
PRESET = {
 "ai_tutor": "Hi! Introduce yourself briefly in Uzbek and ask what I want to learn today.",
 "ai_grammar": "Explain Present Simple for a beginner in Uzbek with 5 short examples and translations, then give 3 practice sentences.",
 "ai_words": "Teach me 10 useful English words for beginners with Uzbek translations and one example sentence each.",
 "ai_speak": "Start a simple A1 English speaking practice with me. Ask one short question in English with its Uzbek translation and wait for my answer.",
 "ai_fix": "Explain in Uzbek that I can send you my English sentences and you will correct my mistakes. Show 2 examples of corrections.",
 "ai_translate": "Explain in Uzbek that I can send any sentence in Uzbek, Russian or English and you will translate it and explain it. Show 2 examples.",
}
r = Router()

# ───────────────────────── DARS MAZMUNI (A1 → A2) ─────────────────────────
# quiz: (savol, [variantlar], to'g'ri_indeks, izoh)
UNITS = [
 {"t": "1. Alphabet & Greetings", "lv": "A1",
  "lesson": "👋 *Salomlashish*\n\nHello / Hi — Salom\nGood morning — Xayrli tong\nGood afternoon — Xayrli kun\nGood evening — Xayrli kech\nGoodbye / Bye — Xayr\n\n❓ How are you? — Ishlaringiz qalay?\n✅ I'm fine, thank you. And you?\n\n🔤 Alifbo: A B C D E F G H I J K L M N O P Q R S T U V W X Y Z (26 harf: 5 unli — A E I O U)",
  "words": [("hello","salom"),("goodbye","xayr"),("please","iltimos"),("thank you","rahmat"),("sorry","kechirasiz"),("yes / no","ha / yo'q")],
  "quiz": [("'Xayrli tong' inglizcha?",["Good night","Good morning","Good evening"],1,"Morning = ertalab."),
           ("How are you? ga javob:",["I'm fine, thanks","My name Ali","Goodbye"],0,"Holatni so'rasa, 'I'm fine' deymiz."),
           ("English alifbosida nechta harf bor?",["24","26","28"],1,"A dan Z gacha 26 ta.")],
  "speak": ["Hello! How are you?","Good morning, nice to meet you.","I'm fine, thank you."]},
 {"t": "2. Verb 'to be' (am/is/are)", "lv": "A1",
  "lesson": "🧩 *To be — bo'lmoq*\n\nI *am* — Men ...man\nYou *are* — Sen/Siz ...siz\nHe / She / It *is*\nWe / You / They *are*\n\n✅ I am a student.\n❌ I am not (I'm not) a teacher.\n❓ Are you from Uzbekistan? — Yes, I am. / No, I'm not.\n\n📌 Qisqartma: I'm, you're, he's, she's, we're, they're",
  "words": [("student","talaba"),("teacher","o'qituvchi"),("doctor","shifokor"),("happy","xursand"),("from","...dan"),("name","ism")],
  "quiz": [("She ___ a doctor.",["am","is","are"],1,"She/He/It → is."),
           ("They ___ students.",["is","am","are"],2,"They → are."),
           ("'I am not' qisqartmasi:",["I amn't","I'm not","I not"],1,"I'm not — to'g'ri shakl.")],
  "speak": ["I am a student.","She is my teacher.","We are from Uzbekistan."]},
 {"t": "3. Numbers, Colours, Days", "lv": "A1",
  "lesson": "🔢 *Sonlar*\n1 one · 2 two · 3 three · 4 four · 5 five · 6 six · 7 seven · 8 eight · 9 nine · 10 ten\n11 eleven · 12 twelve · 13 thirteen · 20 twenty · 100 a hundred\n\n🎨 *Ranglar*\nred · blue · green · yellow · black · white\n\n📅 *Hafta kunlari*\nMonday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday",
  "words": [("red","qizil"),("blue","ko'k"),("green","yashil"),("Monday","dushanba"),("Sunday","yakshanba"),("twenty","yigirma")],
  "quiz": [("'Seven' nechchi?",["6","7","8"],1,"seven = 7."),
           ("Yashil rang:",["green","yellow","blue"],0,"green = yashil."),
           ("Dushanbadan keyingi kun:",["Sunday","Tuesday","Friday"],1,"Monday → Tuesday.")],
  "speak": ["I have five books.","My favourite colour is blue.","Today is Monday."]},
 {"t": "4. Family & Possessives", "lv": "A1",
  "lesson": "👨‍👩‍👧 *Oila*\nmother (mum), father (dad), brother, sister, grandmother, grandfather, son, daughter\n\n🔑 *Egalik*\nmy — mening · your — sening · his — uning (erkak) · her — uning (ayol) · our — bizning · their — ularning\n\n✅ This is my sister. Her name is Dilya.\n📌 Ega + 's: Ali's book — Alining kitobi",
  "words": [("mother","ona"),("father","ota"),("brother","aka/uka"),("sister","opa/singil"),("family","oila"),("friend","do'st")],
  "quiz": [("This is Anna. ___ brother is Tom.",["His","Her","My"],1,"Anna — ayol → her."),
           ("'Grandfather' —",["bobo","amaki","aka"],0,"grandfather = bobo."),
           ("Alining kitobi:",["Ali book","Ali's book","Ali is book"],1,"'s egalikni bildiradi.")],
  "speak": ["This is my family.","My father is a doctor.","Her name is Dilya."]},
 {"t": "5. Present Simple", "lv": "A1",
  "lesson": "⏰ *Present Simple — odatiy ishlar*\n\nI/You/We/They + fe'l: *I work*\nHe/She/It + fe'l+*s*: *She works*\n\n❌ Inkor: I *don't* work / She *doesn't* work\n❓ So'roq: *Do* you work? / *Does* she work?\n\n🕒 Payt so'zlari: always, usually, often, sometimes, never, every day",
  "words": [("wake up","uyg'onmoq"),("eat","yemoq"),("study","o'qimoq"),("work","ishlamoq"),("sleep","uxlamoq"),("every day","har kuni")],
  "quiz": [("He ___ English every day.",["study","studies","studying"],1,"he + study → studies."),
           ("She ___ like coffee.",["don't","doesn't","isn't"],1,"she → doesn't."),
           ("___ you work here?",["Do","Does","Are"],0,"you → Do.")],
  "speak": ["I wake up at seven.","She studies English every day.","Do you like tea?"]},
 {"t": "6. Food, There is/are, Can", "lv": "A1+",
  "lesson": "🍎 *Ovqat*: bread, rice, meat, fish, apple, water, tea, milk\n\n*There is* + birlik: There is an apple.\n*There are* + ko'plik: There are two apples.\n\n💪 *Can — qila olmoq*\nI can swim. / I can't swim. / Can you swim? — Yes, I can.\n\n🛒 How much is it? — Bu qancha turadi?",
  "words": [("bread","non"),("rice","guruch"),("water","suv"),("apple","olma"),("hungry","och"),("thirsty","chanqagan")],
  "quiz": [("There ___ three books.",["is","are","am"],1,"Ko'plik → are."),
           ("I ___ swim. (qila olaman)",["can","am","do"],0,"can + fe'l."),
           ("'Bu qancha turadi?'",["How old is it?","How much is it?","How many is it?"],1,"Narx — How much.")],
  "speak": ["I'm hungry. Can I have some bread?","How much is this apple?","I can swim."]},
 {"t": "7. Past Simple (Elementary A2)", "lv": "A2",
  "lesson": "⏪ *Past Simple — o'tgan zamon*\n\nTo'g'ri fe'llar: +ed → work*ed*, play*ed*, study → stud*ied*\nNoto'g'ri: go→*went*, eat→*ate*, see→*saw*, have→*had*, buy→*bought*, be→*was/were*\n\n❌ I *didn't* go.   ❓ *Did* you go?\n\n🕒 yesterday, last week, two days ago, in 2020",
  "words": [("went","bordi"),("ate","yedi"),("saw","ko'rdi"),("bought","sotib oldi"),("yesterday","kecha"),("ago","avval")],
  "quiz": [("Yesterday I ___ to school.",["go","went","goed"],1,"go → went."),
           ("She ___ TV last night.",["watched","watch","watching"],0,"+ed."),
           ("___ you eat breakfast?",["Do","Did","Were"],1,"O'tgan zamon so'rog'i — Did.")],
  "speak": ["Yesterday I went to the market.","We watched a film last night.","Did you eat breakfast?"]},
 {"t": "8. Future, Comparatives, Travel", "lv": "A2",
  "lesson": "🔮 *Kelasi zamon*\nwill: I *will* call you. · going to: I'm *going to* travel.\n\n⚖️ *Taqqoslash*\nqisqa so'z +er: tall → tall*er* than\nuzun so'z more: *more* expensive than\nEng: tall*est*, *the most* beautiful\nNoto'g'ri: good → better → best\n\n✈️ airport, ticket, hotel, passport, luggage",
  "words": [("ticket","chipta"),("hotel","mehmonxona"),("passport","pasport"),("cheap","arzon"),("expensive","qimmat"),("tomorrow","ertaga")],
  "quiz": [("Tashkent is ___ than my village.",["big","bigger","biggest"],1,"than → -er."),
           ("I ___ visit Samarkand tomorrow.",["am going to","went","was"],0,"Reja → going to."),
           ("good — better — ?",["goodest","best","most good"],1,"Noto'g'ri shakl: best.")],
  "speak": ["I'm going to visit Samarkand tomorrow.","This hotel is cheaper than that one.","Where is the airport?"]},
]

TEXTBOOKS = [("📘 British Council LearnEnglish (A1–A2)","https://learnenglish.britishcouncil.org/skills"),
             ("📗 Cambridge English — A1/A2 materials","https://www.cambridgeenglish.org/learning-english/"),
             ("📙 BBC Learning English — Basic","https://www.bbc.co.uk/learningenglish/english/course/lower-intermediate"),
             ("🎧 Oxford Online English","https://www.oxfordonlineenglish.com/free-english-lessons")]

# ───────────────────────── BAZA ─────────────────────────
async def db_init():
    async with aiosqlite.connect(DB) as d:
        await d.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,xp INTEGER DEFAULT 0)")
        await d.execute("CREATE TABLE IF NOT EXISTS done(uid INTEGER,unit INTEGER,kind TEXT,score INTEGER DEFAULT 0,PRIMARY KEY(uid,unit,kind))")
        await d.commit()

async def add_xp(uid, name, xp):
    async with aiosqlite.connect(DB) as d:
        await d.execute("INSERT INTO users(id,name,xp) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET xp=xp+?,name=?", (uid,name,xp,xp,name))
        await d.commit()

async def mark(uid, unit, kind, score=0):
    async with aiosqlite.connect(DB) as d:
        await d.execute("INSERT OR REPLACE INTO done VALUES(?,?,?,?)", (uid,unit,kind,score)); await d.commit()

async def get_progress(uid):
    async with aiosqlite.connect(DB) as d:
        xp = (await (await d.execute("SELECT xp FROM users WHERE id=?", (uid,))).fetchone() or [0])[0]
        rows = await (await d.execute("SELECT unit,kind,score FROM done WHERE uid=?", (uid,))).fetchall()
        top = await (await d.execute("SELECT name,xp FROM users ORDER BY xp DESC LIMIT 5")).fetchall()
    return xp, rows, top

# ───────────────────────── MENYU ─────────────────────────
def main_menu():
    rows = [[Btn(text="📚 Darslar", callback_data="units")],
            [Btn(text="🤖 AI ustoz (barcha tilda)", callback_data="ai")],
            [Btn(text="📝 Testlar", callback_data="tests"), Btn(text="🎤 Speaking", callback_data="speaks")],
            [Btn(text="📖 Darsliklar", callback_data="books"), Btn(text="🏆 Natijam", callback_data="me")]]
    if WEBAPP_URL: rows.insert(0, [Btn(text="✨ Mini App (animatsiyali)", web_app=WebAppInfo(url=WEBAPP_URL))])
    return KB(inline_keyboard=rows)

async def typing_anim(msg: Message, frames):
    for f in frames:
        await asyncio.sleep(0.45)
        try: await msg.edit_text(f)
        except Exception: pass

GMODELS = list(dict.fromkeys([GMODEL, "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]))

async def gcall(body):
    last = "noma'lum xato"
    async with aiohttp.ClientSession() as ses:
        for mdl in GMODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mdl}:generateContent"
            async with ses.post(url, json=body, headers={"x-goog-api-key": GKEY}, timeout=aiohttp.ClientTimeout(total=90)) as r:
                data = await r.json()
                if r.status == 200:
                    parts = data["candidates"][0]["content"]["parts"]
                    return "".join(p.get("text", "") for p in parts).strip()
                last = f"{mdl}: {r.status} {data.get('error', {}).get('message', '')}"
                logging.warning("Gemini xato: %s", last)
                if r.status not in (400, 404):      # 429 limit yoki 403 — boshqa model yordam bermaydi
                    break
    raise RuntimeError(last)

async def gemini(h):
    body = {"system_instruction": {"parts": [{"text": SYS}]},
            "contents": [{"role": "user" if x["role"] == "user" else "model", "parts": [{"text": x["content"]}]} for x in h]}
    return await gcall(body)

async def claude(h):
    resp = await AI.messages.create(model=AI_MODEL, max_tokens=800, system=SYS, messages=h)
    return "".join(b.text for b in resp.content if b.type == "text").strip()

async def ask_ai(m: Message, text: str):
    uid = m.from_user.id
    if not (GKEY or AI):
        return await m.answer("🤖 AI hali yoqilmagan (.env ga GEMINI_API_KEY yoki ANTHROPIC_API_KEY kerak).")
    k = (uid, date.today().isoformat())
    if uid not in PREMIUM and USED.get(k, 0) >= AI_LIMIT:
        return await m.answer(f"⏳ Bugungi bepul limit ({AI_LIMIT} ta savol) tugadi.\n💎 Cheksiz AI uchun Premium: @muhammadjonov001")
    USED[k] = USED.get(k, 0) + 1
    h = HIST.setdefault(uid, [])
    h.append({"role": "user", "content": text[:2000]})
    del h[:-8]
    while h and h[0]["role"] != "user":
        h.pop(0)
    await m.bot.send_chat_action(m.chat.id, "typing")
    try:
        out = (await gemini(h) if GKEY else await claude(h)) or "..."
    except Exception as e:
        logging.warning("AI xato: %s", e); h.pop()
        dbg = f"\n\n🛠 {str(e)[:200]}" if os.getenv("DEBUG", "1") != "0" else ""
        return await m.answer("😔 AI hozir javob bera olmadi, birozdan keyin urinib ko'ring." + dbg)
    h.append({"role": "assistant", "content": out})
    await add_xp(uid, m.from_user.full_name, 2)
    await m.answer(out[:4000])

@r.message(CommandStart(deep_link=True))
async def start_dl(m: Message, command: CommandObject):
    if (command.args or "") in PRESET:
        await m.answer("🤖 AI ustoz o'ylayapti...")
        return await ask_ai(m, PRESET[command.args])
    await start(m)

@r.message(CommandStart())
async def start(m: Message):
    await add_xp(m.from_user.id, m.from_user.full_name, 0)
    s = await m.answer("🎓")
    await typing_anim(s, ["🎓 E", "🎓 English", "🎓 English with me", "🎓 English with me ✨"])
    await m.answer(f"Salom, *{m.from_user.first_name}*! 👋\n\nBu bot seni *Beginner (A1) → Elementary (A2)* darajasigacha olib boradi.\n\n"
                   "📚 8 ta dars · 📝 test + kalitlar · 🎤 speaking · 📖 darsliklar\n\nBoshlaymizmi? 👇",
                   parse_mode="Markdown", reply_markup=main_menu())

@r.message(Command("menu"))
async def menu(m: Message): await m.answer("🏠 Bosh menyu:", reply_markup=main_menu())

@r.callback_query(F.data == "home")
async def home(c: CallbackQuery):
    await c.message.edit_text("🏠 Bosh menyu:", reply_markup=main_menu()); await c.answer()

def unit_list(prefix, icon):
    rows = [[Btn(text=f"{icon} {u['t']} [{u['lv']}]", callback_data=f"{prefix}:{i}")] for i, u in enumerate(UNITS)]
    rows.append([Btn(text="⬅️ Menyu", callback_data="home")]); return KB(inline_keyboard=rows)

@r.callback_query(F.data == "units")
async def units(c: CallbackQuery):
    await c.message.edit_text("📚 *Darsni tanlang:*", parse_mode="Markdown", reply_markup=unit_list("u", "📘")); await c.answer()
@r.callback_query(F.data == "tests")
async def tests(c: CallbackQuery):
    await c.message.edit_text("📝 *Test tanlang:*", parse_mode="Markdown", reply_markup=unit_list("t", "📝")); await c.answer()
@r.callback_query(F.data == "speaks")
async def speaks(c: CallbackQuery):
    await c.message.edit_text("🎤 *Speaking mavzusi:*", parse_mode="Markdown", reply_markup=unit_list("s", "🎤")); await c.answer()

@r.callback_query(F.data == "books")
async def books(c: CallbackQuery):
    rows = [[Btn(text=n, url=u)] for n, u in TEXTBOOKS] + [[Btn(text="⬅️ Menyu", callback_data="home")]]
    await c.message.edit_text("📖 *Beginner uchun bepul darsliklar* (Google'da mutaxassislar tayyorlagan rasmiy manbalar):",
                              parse_mode="Markdown", reply_markup=KB(inline_keyboard=rows)); await c.answer()

# ───────────────────────── DARS ─────────────────────────
@r.callback_query(F.data.startswith("u:"))
async def unit(c: CallbackQuery):
    i = int(c.data[2:]); u = UNITS[i]
    words = "\n".join(f"• *{e}* — {z}" for e, z in u["words"])
    kb = KB(inline_keyboard=[[Btn(text="🔊 So'zlarni tinglash", callback_data=f"v:{i}")],
                             [Btn(text="📝 Testga o'tish", callback_data=f"t:{i}"), Btn(text="🎤 Speaking", callback_data=f"s:{i}")],
                             [Btn(text="⬅️ Darslar", callback_data="units")]])
    await c.message.edit_text(f"*{u['t']}*  `{u['lv']}`\n\n{u['lesson']}\n\n🗂 *So'zlar:*\n{words}", parse_mode="Markdown", reply_markup=kb)
    await mark(c.from_user.id, i, "lesson"); await add_xp(c.from_user.id, c.from_user.full_name, 5); await c.answer("+5 XP ⭐")

async def tts(text):
    try:
        from gtts import gTTS; import io
        def gen():
            b = io.BytesIO(); gTTS(text, lang="en").write_to_fp(b); return b.getvalue()
        return BufferedInputFile(await asyncio.to_thread(gen), "audio.mp3")
    except Exception as e:
        logging.warning("TTS xato: %s", e); return None

@r.callback_query(F.data.startswith("v:"))
async def vocab_audio(c: CallbackQuery):
    i = int(c.data[2:]); await c.answer("🔊 Tayyorlanmoqda...")
    a = await tts(". ".join(e for e, _ in UNITS[i]["words"]))
    if a: await c.message.answer_audio(a, title=f"Unit {i+1} words")

# ───────────────────────── TEST ─────────────────────────
@r.callback_query(F.data.startswith("t:"))
async def test_start(c: CallbackQuery):
    i = int(c.data[2:]); await c.answer()
    await ask(c.message, i, 0, 0, edit=True)

async def ask(msg, i, q, score, edit=False):
    qs = UNITS[i]["quiz"]; text_q, opts, _, _ = qs[q]
    kb = KB(inline_keyboard=[[Btn(text=o, callback_data=f"a:{i}:{q}:{k}:{score}")] for k, o in enumerate(opts)])
    bar = "🟩" * q + "⬜" * (len(qs) - q)
    t = f"📝 *{UNITS[i]['t']}*\n{bar}\n\n*{q+1}/{len(qs)}.* {text_q}"
    await (msg.edit_text if edit else msg.answer)(t, parse_mode="Markdown", reply_markup=kb)

@r.callback_query(F.data.startswith("a:"))
async def answer(c: CallbackQuery):
    _, i, q, k, score = c.data.split(":"); i, q, k, score = int(i), int(q), int(k), int(score)
    right = UNITS[i]["quiz"][q][2]; ok = k == right; score += ok
    await c.answer("✅ To'g'ri!" if ok else "❌ Noto'g'ri", show_alert=False)
    if q + 1 < len(UNITS[i]["quiz"]): return await ask(c.message, i, q + 1, score, edit=True)
    n = len(UNITS[i]["quiz"])
    key = "\n".join(f"{x+1}) *{qq[1][qq[2]]}* — {qq[3]}" for x, qq in enumerate(UNITS[i]["quiz"]))
    emoji = "🏆" if score == n else "👍" if score >= n/2 else "💪"
    await c.message.edit_text(f"{emoji} *Natija: {score}/{n}*\n\n🔑 *Test kalitlari:*\n{key}", parse_mode="Markdown",
        reply_markup=KB(inline_keyboard=[[Btn(text="🔁 Qayta", callback_data=f"t:{i}"), Btn(text="⬅️ Testlar", callback_data="tests")]]))
    await mark(c.from_user.id, i, "test", score); await add_xp(c.from_user.id, c.from_user.full_name, score * 10)
    try: await c.message.answer_dice(emoji="🎉" if score == n else "🎯")   # animatsion dice
    except Exception: pass

# ───────────────────────── SPEAKING ─────────────────────────
SPK_STATE = {}
@r.callback_query(F.data.startswith("s:"))
async def speak(c: CallbackQuery):
    i = int(c.data[2:]); await c.answer()
    SPK_STATE[c.from_user.id] = i
    ph = UNITS[i]["speak"]
    await c.message.answer(f"🎤 *Speaking — {UNITS[i]['t']}*\n\n1️⃣ Gapni tinglang 🔊\n2️⃣ Takrorlab *ovozli xabar* yuboring 🎙\n\n" +
                           "\n".join(f"▫️ _{p}_" for p in ph), parse_mode="Markdown")
    for p in ph:
        a = await tts(p)
        if a: await c.message.answer_voice(a, caption=p)

@r.message(F.voice)
async def got_voice(m: Message):
    i = SPK_STATE.get(m.from_user.id)
    s = await m.answer("🎧 Tinglayapman...")
    fb = None
    if GKEY:
        try:
            buf = io.BytesIO(); await m.bot.download(m.voice, destination=buf)
            body = {"system_instruction": {"parts": [{"text": SYS}]},
                    "contents": [{"role": "user", "parts": [
                        {"inline_data": {"mime_type": "audio/ogg", "data": base64.b64encode(buf.getvalue()).decode()}},
                        {"text": "This is my English speaking practice (voice message). 1) Write what I said. 2) Give short feedback on pronunciation and grammar and show the corrected sentence. 3) Give a score from 0 to 100. Answer in Uzbek, briefly."}]}]}
            fb = await gcall(body)
        except Exception as e:
            logging.warning("Voice AI xato: %s", e)
    if fb:
        await s.edit_text("🎤 " + fb[:4000])
    else:
        await s.edit_text("✅ Ovozingiz qabul qilindi. +15 XP ⭐\n(AI tekshiruvi hozir ishlamadi.)")
    if i is not None: await mark(m.from_user.id, i, "speak", 1)
    await add_xp(m.from_user.id, m.from_user.full_name, 15)

# ───────────────────────── NATIJA ─────────────────────────
@r.callback_query(F.data == "me")
async def me(c: CallbackQuery):
    xp, rows, top = await get_progress(c.from_user.id)
    L = sum(1 for _, k, _ in rows if k == "lesson"); T = [s for _, k, s in rows if k == "test"]; S = sum(1 for _, k, _ in rows if k == "speak")
    pct = int((L + len(T) + S) / (len(UNITS) * 3) * 100)
    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
    lb = "\n".join(f"{x+1}. {n} — {p} XP" for x, (n, p) in enumerate(top))
    await c.message.edit_text(f"🏆 *Natijangiz*\n\n⭐ XP: *{xp}*\n📈 [{bar}] {pct}%\n📚 Darslar: {L}/{len(UNITS)}\n📝 Testlar: {len(T)}/{len(UNITS)}\n🎤 Speaking: {S}/{len(UNITS)}\n\n🥇 *Top 5:*\n{lb}",
        parse_mode="Markdown", reply_markup=KB(inline_keyboard=[[Btn(text="⬅️ Menyu", callback_data="home")]])); await c.answer()

@r.callback_query(F.data == "ai")
async def ai_cb(c: CallbackQuery):
    await c.message.answer("🤖 *AI ustoz*\n\nIstalgan tilda yozing: savol, tarjima, grammatika yoki darsni tushuntirish so'rang. Inglizcha gapingizni yuborsangiz, xatolarini tuzataman.", parse_mode="Markdown")
    await c.answer()

@r.message(Command("ai"))
async def ai_cmd(m: Message):
    await m.answer("🤖 AI ustoz tayyor! Savolingizni istalgan tilda yozing.")

@r.message(F.text & ~F.text.startswith("/"))
async def any_text(m: Message):
    await ask_ai(m, m.text)

async def main():
    logging.basicConfig(level=logging.INFO); await db_init()
    bot = Bot(BOT_TOKEN); dp = Dispatcher(); dp.include_router(r)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
