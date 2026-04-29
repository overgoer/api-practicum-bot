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

logging.basicConfig(level=logging.INFO)

# --- КОНФИГ ---
TOKEN = "7519683641:AAFSl4pd6DENDM7JYb0l70Y08_SjX9GFeK8"
DB_NAME = "practicum.db"

class Practicum(StatesGroup):
    welcome = State()
    task1 = State()
    task2 = State()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users 
                   (tg_id INTEGER PRIMARY KEY, username TEXT, step TEXT, last_act TIMESTAMP)''')
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
    kb.button(text="Начать →", callback_data="start_practicum")
    await message.answer("Привет! Это мини-практикум по поиску багов в API. Готов?", reply_markup=kb.as_markup())
    await state.set_state(Practicum.welcome)

@dp.callback_query(F.data == "start_practicum")
async def start_task1(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task1_view")
    kb = InlineKeyboardBuilder()
    kb.button(text="Статус 401", callback_data="t1_wrong")
    kb.button(text="Бага нет", callback_data="t1_correct")
    kb.adjust(1)
    await callback.message.answer("🚀 Задача 1\n\nGET /api/v1/profile\nAuth: Bearer valid_token\n\nОтвет: 200 OK\nТело: {\"user_id\": 456}\n\n? Где баг?", reply_markup=kb.as_markup())
    await state.set_state(Practicum.task1)
    await callback.answer()

@dp.callback_query(F.data.startswith("t1_"))
async def check_task1(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text="Следующая задачка →", callback_data="start_task2")
    msg = "✅ Верно! Бага нет." if callback.data == "t1_correct" else "❌ Нет. Правильный ответ: бага нет."
    await callback.message.answer(f"{msg}\n\nГотов к более сложной задаче?", reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "start_task2")
async def start_task2(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task2_view")
    kb = InlineKeyboardBuilder()
    kb.button(text="Ошибка 400 Bad Request", callback_data="t2_correct")
    kb.button(text="Бага нет", callback_data="t2_wrong")
    kb.adjust(1)
    await callback.message.answer("🚀 Задача 2\n\nPOST /api/v1/orders\nТело: {\"product_id\": 123, \"quantity\": -1}\n\nОтвет: 200 OK\n? Что не так?", reply_markup=kb.as_markup())
    await state.set_state(Practicum.task2)
    await callback.answer()

# НОВЫЙ ХЕНДЛЕР: Ответ на задачу 2
@dp.callback_query(F.data.startswith("t2_"))
async def check_task2(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task2_done")
    
    if callback.data == "t2_correct":
        res = "✅ В точку! Нельзя заказать -1 товар. Сервер должен был вернуть 400."
    else:
        res = "❌ Мимо. Тут явный баг: отрицательное количество товара прошло успешно."
    
    kb = InlineKeyboardBuilder()
    kb.button(text="Узнать больше об API →", url="https://t.me/your_channel") # Твоя ссылка
    
    await callback.message.answer(f"{res}\n\nТы прошел мини-практикум! Хочешь стать профи в тестировании API?", reply_markup=kb.as_markup())
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
