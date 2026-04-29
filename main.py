import asyncio
import sqlite3
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.bot import DefaultBotProperties
import os

logging.basicConfig(level=logging.INFO)

# --- КОНФИГ ---
TOKEN = os.environ.get("TOKEN", "7519683641:AAFSl4pd6DENDM7JYb0l70Y08_SjX9GFeK8")
DB_NAME = os.environ.get("DB_PATH", "practicum.db")

class Practicum(StatesGroup):
    welcome = State()
    task1 = State()
    task2 = State()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users
                   (tg_id INTEGER PRIMARY KEY, username TEXT, step TEXT, last_act TIMESTAMP)""")
    conn.commit()
    conn.close()

def upsert_user(tg_id, username, step):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (tg_id, username, step, last_act)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(tg_id) DO UPDATE SET
            username = excluded.username,
            step = excluded.step,
            last_act = excluded.last_act
    """, (tg_id, username, step, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

dp = Dispatcher()

# --- ХЕНДЛЕРЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    upsert_user(message.from_user.id, message.from_user.username or "unknown", "start")
    kb = InlineKeyboardBuilder()
    kb.button(text="Начать \u2192", callback_data="start_practicum")
    await message.answer("Привет! Это мини-практикум по поиску багов в API. Готов?", reply_markup=kb.as_markup())
    await state.set_state(Practicum.welcome)

@dp.callback_query(F.data == "start_practicum")
async def start_task1(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task1_view")

    msg = (
        "<b>\U0001F4C4 Документация метода:</b>\n\n"
        "<blockquote><b>GET /api/v1/day-of-week</b>\n\n"
        "Параметры:\n- year (int) - год, обязательный\n- month (int) - месяц (1-12), обязательный\n- day (int) - день (1-31), обязательный\n\n"
        "Ответ:\n- dayOfWeek (string) - день недели на английском</blockquote>\n\n"
        "<b>\U0001F310 Фактический запрос/ответ:</b>\n\n"
        "<blockquote><b>GET /api/v1/day-of-week?year=2026&month=1&day=1</b>\n\n"
        "Ответ:\n<code>{\n  \"dayOfWeek\": \"Thursday\"\n}</code></blockquote>\n\n"
        "<b>Где баг?</b>\n\n\u2022 (выбери вариант, нажав на кнопку)"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="A) Бага нет", callback_data="t1_correct")
    kb.button(text="B) Статус 404", callback_data="t1_wrong")
    kb.button(text="C) На русском", callback_data="t1_wrong2")
    kb.adjust(1)

    await callback.message.answer(msg, reply_markup=kb.as_markup())
    await state.set_state(Practicum.task1)
    await callback.answer()

@dp.callback_query(F.data.startswith("t1_"))
async def check_task1(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task1_done")

    if callback.data == "t1_correct":
        msg = "\u2705 \u0412\u0435\u0440\u043d\u043e! 1 \u044f\u043d\u0432\u0430\u0440\u044f 2026 \u2014 \u0447\u0435\u0442\u0432\u0435\u0440\u0433 (Thursday). API \u0432\u0435\u0440\u043d\u0443\u043b \u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u044b\u0439 \u043e\u0442\u0432\u0435\u0442. \u0411\u0430\u0433\u0430 \u043d\u0435\u0442."
    else:
        msg = "\u274c \u041d\u0435\u0442. 1 \u044f\u043d\u0432\u0430\u0440\u044f 2026 \u2014 \u0447\u0435\u0442\u0432\u0435\u0440\u0433, API \u0432\u0435\u0440\u043d\u0443\u043b Thursday. \u042d\u0442\u043e \u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u044b\u0439 \u043e\u0442\u0432\u0435\u0442."

    kb = InlineKeyboardBuilder()
    kb.button(text="\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0430\u044f \u0437\u0430\u0434\u0430\u0447\u043a\u0430 \u2192", callback_data="start_task2")
    await callback.message.answer(f"{msg}\n\n\u0413\u043e\u0442\u043e\u0432 \u043a \u0431\u043e\u043b\u0435\u0435 \u0441\u043b\u043e\u0436\u043d\u043e\u0439 \u0437\u0430\u0434\u0430\u0447\u0435?", reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "start_task2")
async def start_task2(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task2_view")

    msg = (
        "<b>\U0001F4C4 Документация метода:</b>\n\n"
        "<blockquote><b>POST /api/v1/orders</b>\n\n"
        "Body:\n<code>{\n  \"product_id\": 123,\n  \"quantity\": -1\n}</code></blockquote>\n\n"
        "<b>\U0001F310 Фактический запрос/ответ:</b>\n\n"
        "<blockquote>Ответ:\n<code>{\n  \"status\": \"ok\",\n  \"order_id\": 456\n}</code></blockquote>\n\n"
        "<b>Где баг?</b>\n\n\u2022 (выбери вариант, нажав на кнопку)"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="A) Бага нет", callback_data="t2_wrong")
    kb.button(text="B) 400 Bad Request", callback_data="t2_correct")
    kb.adjust(1)
    await callback.message.answer(msg, reply_markup=kb.as_markup())
    await state.set_state(Practicum.task2)
    await callback.answer()

@dp.callback_query(F.data.startswith("t2_"))
async def check_task2(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task2_done")

    if callback.data == "t2_correct":
        res = "\u2705 \u0412 \u0442\u043e\u0447\u043a\u0443! \u041d\u0435\u043b\u044c\u0437\u044f \u0437\u0430\u043a\u0430\u0437\u0430\u0442\u044c -1 \u0442\u043e\u0432\u0430\u0440. \u0421\u0435\u0440\u0432\u0435\u0440 \u0434\u043e\u043b\u0436\u0435\u043d \u0431\u044b\u043b \u0432\u0435\u0440\u043d\u0443\u0442\u044c 400 Bad Request."
    else:
        res = "\u274c \u041c\u0438\u043c\u043e. \u0422\u0443\u0442 \u044f\u0432\u043d\u044b\u0439 \u0431\u0430\u0433: quantity = -1 \u043f\u0440\u043e\u0448\u043b\u043e \u0443\u0441\u043f\u0435\u0448\u043d\u043e. \u0421\u0435\u0440\u0432\u0435\u0440 \u0434\u043e\u043b\u0436\u0435\u043d \u0431\u044b\u043b \u0432\u0435\u0440\u043d\u0443\u0442\u044c 400."

    kb = InlineKeyboardBuilder()
    kb.button(text="\u0423\u0437\u043d\u0430\u0442\u044c \u0431\u043e\u043b\u044c\u0448\u0435 \u043e\u0431 API \u2192", url="https://t.me/eddytester")

    await callback.message.answer(f"{res}\n\n\u0422\u044b \u043f\u0440\u043e\u0448\u0435\u043b \u043c\u0438\u043d\u0438-\u043f\u0440\u0430\u043a\u0442\u0438\u043a\u0443\u043c! \u0425\u043e\u0447\u0435\u0448\u044c \u0441\u0442\u0430\u0442\u044c \u043f\u0440\u043e\u0444\u0438 \u0432 \u0442\u0435\u0441\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0438 API?", reply_markup=kb.as_markup())
    await callback.answer()

async def main():
    init_db()
    session = AiohttpSession()
    bot = Bot(token=TOKEN, session=session, default=DefaultBotProperties(parse_mode="HTML"))
    await dp.start_polling(bot, handle_as_tasks=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
