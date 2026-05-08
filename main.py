"""
api-practicum-bot — Telegram бот для воронки API Practicum
Полный цикл: 4 задачи → прогрев → оффер
"""

import asyncio
import sqlite3
import logging
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.bot import DefaultBotProperties
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── КОНФИГ ────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("TOKEN", "7519683641:AAFSl4pd6DENDM7JYb0l70Y08_SjX9GFeK8")
DB_NAME = os.environ.get("DB_PATH", "practicum.db")
CHANNEL_EDDYTESTER = "https://t.me/eddytester"
# Реальный username бота: api_practikum_bot
PRODUCT_LINK = "https://t.me/api_practikum_bot"
# Старая ссылка с start=buy — сохранить на будущее:
# PRODUCT_LINK = "https://t.me/api_practikum_bot?start=buy"

# ─── FSM СОСТОЯНИЯ ─────────────────────────────────────────────────────────
class Practicum(StatesGroup):
    welcome = State()
    task1 = State()
    task2 = State()
    task3 = State()
    task4 = State()
    msg1_story = State()
    msg2_theory = State()
    msg2_pain = State()
    msg3_video = State()
    msg4_inside = State()
    msg5_offer = State()
    msg6_soft_exit = State()

# ─── БАЗА ДАННЫХ ───────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users
                   (tg_id INTEGER PRIMARY KEY,
                    username TEXT,
                    step TEXT,
                    last_act TIMESTAMP,
                    pain_choice TEXT,
                    offer_status TEXT DEFAULT NULL)""")
    conn.commit()
    conn.close()

def upsert_user(tg_id, username, step, **extra):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (tg_id, username, step, last_act)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(tg_id) DO UPDATE SET
            username = excluded.username,
            step = excluded.step,
            last_act = excluded.last_act
    """, (tg_id, username or "unknown", step,
          datetime.now().strftime("%Y-%m-%d %d:%M:%S")))
    conn.commit()
    conn.close()

def update_user_step(tg_id, step):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE users SET step = ?, last_act = ? WHERE tg_id = ?",
                (step, datetime.now().strftime("%Y-%m-%d %d:%M:%S"), tg_id))
    conn.commit()
    conn.close()

# ─── ХЕЛПЕРЫ ───────────────────────────────────────────────────────────────
def kb_back_to_tasks():
    b = InlineKeyboardBuilder()
    b.button(text="⬅ К задачам", callback_data="back_to_tasks")
    return b.as_markup()

def kb_next(next_cb: str, text="Дальше ➡"):
    b = InlineKeyboardBuilder()
    b.button(text=text, callback_data=next_cb)
    return b.as_markup()

def kb_url(text: str, url: str):
    b = InlineKeyboardBuilder()
    b.button(text=text, url=url)
    return b.as_markup()

# ─── DIPATCHER ─────────────────────────────────────────────────────────────
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ═══════════════════════════════════════════════════════════════════════════
#  ПОТОК 1: 4 ЗАДАЧИ
# ═══════════════════════════════════════════════════════════════════════════

@dp.message(Command("start"), flags={"long_operation": True})
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    upsert_user(message.from_user.id, message.from_user.username, "start")
    tg_id = message.from_user.id

    # Сброс pain_choice в БД
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE users SET pain_choice = NULL, offer_status = NULL WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

    msg = (
        "👋 Привет! Это <b>мини-практикум по поиску багов в API</b>.\n\n"
        "За 10 минут проверишь, насколько хорошо ловишь ошибки —\n"
        "как на реальном проекте.\n\n"
        "4 задачи → разбор → поймёшь, где подтянуться.\n\n"
        "<i>Готов? Жми «Начать» 👇</i>"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="Начать 🚀", callback_data="start_practicum")
    await message.answer(msg, reply_markup=kb.as_markup())
    await state.set_state(Practicum.welcome)


# ─── ЗАДАЧА 1: Create Order (success: true при ошибке) ────────────────────

TASK1_OBSIDIAN = (
    "<b>📄 Документация метода:</b>\n\n"
    "<blockquote><b>POST /api/v3/orders/create</b>\n\n"
    "Body:\n<code>{\n"
    '  "item_id": 404,\n'
    '  "quantity": 0,\n'
    '  "promo_code": "WINTER2026"\n'
    "}</code></blockquote>\n\n"
    "<b>🌐 Фактический ответ:</b>\n\n"
    "<blockquote><code>{\n"
    '  "success": true,\n'
    '  "order_id": null,\n'
    '  "message": "Quantity must be more than 0",\n'
    '  "server_time": "2026-09-11T12:00:00Z"\n'
    "}</code></blockquote>\n\n"
    "<b>Где баг?</b>\n\n"
    "A. 200 OK — должен быть 400 Bad Request\n"
    "B. success: true при сообщении об ошибке — противоречие\n"
    "C. order_id: null — при ошибке должен быть всегда\n\n"
    "👇 Выбери вариант"
)


@dp.callback_query(F.data == "start_practicum")
async def start_task1(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task1_view")

    kb = InlineKeyboardBuilder()
    kb.button(text="A", callback_data="t1_wrong")
    kb.button(text="B", callback_data="t1_correct")
    kb.button(text="C", callback_data="t1_wrong2")
    kb.adjust(1)

    await callback.message.answer(TASK1_OBSIDIAN, reply_markup=kb.as_markup())
    await state.set_state(Practicum.task1)
    await callback.answer()


@dp.callback_query(F.data.startswith("t1_"))
async def check_task1(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task1_done")

    if callback.data == "t1_correct":
        result = (
            "✅ <b>В точку!</b>\n\n"
            "`success: true` при сообщении об ошибке — это противоречие.\n"
            "Клиент не поймёт: заказ создан или нет?\n\n"
            "<b>Как должно быть:</b>\n"
            "<code>{\n"
            '  "success": false,\n'
            '  "order_id": null,\n'
            '  "message": "Quantity must be more than 0"\n'
            "}</code>\n\n"
            "Или статус <code>400 Bad Request</code> вместо <code>200 OK</code>."
        )
    elif callback.data == "t1_wrong":
        result = "❌ Нет. Статус 200 OK допустим — проблема именно в противоречивых полях ответа."
    else:
        result = "❌ Нет. order_id = null — это ок при ошибке. Баг в другом."

    kb = InlineKeyboardBuilder()
    kb.button(text="Следующая задача ➡", callback_data="start_task2")
    kb.adjust(1)

    await callback.message.answer(
        f"{result}\n\nГотов к более сложной задаче?",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


# ─── ЗАДАЧА 2: Profile (password_hash в ответе) ────────────────────────────

TASK2_OBSIDIAN = (
    "<b>📄 Документация метода:</b>\n\n"
    "<blockquote><b>GET /api/v2/profile?user_id={userId}</b>\n"
    "Header: <code>X-Auth-Token: admin_token_99</code></blockquote>\n\n"
    "<b>🌐 Фактический ответ:</b>\n\n"
    "<blockquote><code>{\n"
    '  "id": 8841,\n'
    '  "username": "tester_pro",\n'
    '  "email": "test@example.com",\n'
    '  "balance": 1500,\n'
    '  "password_hash": "sha256$uI89!jd#k9",\n'
    '  "roles": ["user"],\n'
    '  "is_active": true\n'
    "}</code></blockquote>\n\n"
    "<b>Где критическая уязвимость?</b>\n\n"
    "A. balance: 1500 — пользователь видит чужие финансы\n"
    "B. password_hash в ответе — утечка хеша пароля\n"
    'C. roles: ["user"] — должно быть больше ролей\n'
    "\n"
    "👇 Выбери вариант"
)


@dp.callback_query(F.data == "start_task2")
async def start_task2(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task2_view")

    kb = InlineKeyboardBuilder()
    kb.button(text="A", callback_data="t2_wrong")
    kb.button(text="B", callback_data="t2_correct")
    kb.button(text="C", callback_data="t2_wrong2")
    kb.adjust(1)

    await callback.message.answer(TASK2_OBSIDIAN, reply_markup=kb.as_markup())
    await state.set_state(Practicum.task2)
    await callback.answer()


@dp.callback_query(F.data.startswith("t2_"))
async def check_task2(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task2_done")

    if callback.data == "t2_correct":
        result = (
            "✅ <b>В точку!</b>\n\n"
            "`password_hash` <b>никогда</b> не должен возвращаться в API response.\n\n"
            "<b>Риск:</b> Злоумышленник может использовать хеш для:\n"
            "• Брутфорс-атаки (подбор пароля)\n"
            "• Pass-the-hash атаки\n"
            "• Обхода аутентификации\n\n"
            "<b>Как должно быть:</b> Поле <code>password_hash</code> должно быть полностью исключено из ответа."
        )
    elif callback.data == "t2_wrong":
        result = "❌ Нет. balance виден — это не критично для профиля. Ищи уязвимость."
    else:
        result = "❌ Нет. Количество ролей — это бизнес-логика, а не уязвимость."

    kb = InlineKeyboardBuilder()
    kb.button(text="Следующая задача ➡", callback_data="start_task3")
    kb.adjust(1)

    await callback.message.answer(
        f"{result}\n\nПродолжаем?",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


# ─── ЗАДАЧА 3: Products (фильтры не работают) ──────────────────────────────

TASK3_OBSIDIAN = (
    "<b>📄 Документация метода:</b>\n\n"
    "<blockquote><b>GET /api/products?status=active&has_discount=true&limit=2</b></blockquote>\n\n"
    "<b>🌐 Фактический ответ:</b>\n\n"
    "<blockquote><code>{\n"
    '  "items": [\n'
    "    {\n"
    '      "name": "Механическая клавиатура",\n'
    '      "status": "active",\n'
    '      "price": 5000,\n'
    '      "old_price": 7000\n'
    "    },\n"
    "    {\n"
    '      "name": "Игровая мышь",\n'
    '      "status": "archived",\n'
    '      "price": 2500,\n'
    '      "old_price": 2500\n'
    "    }\n"
    "  ],\n"
    '  "total_count": 45\n'
    "}</code></blockquote>\n\n"
    "<b>Что не так с этим ответом?</b>\n\n"
    "A. total_count = 45 — не совпадает с количеством товаров\n"
    "B. Вернулось 2 товара при limit=2 — бага нет\n"
    "C. Оба фильтра не сработали (status=active + has_discount=true)\n"
    "\n"
    "👇 Выбери вариант"
)


@dp.callback_query(F.data == "start_task3")
async def start_task3(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task3_view")

    kb = InlineKeyboardBuilder()
    kb.button(text="A", callback_data="t3_wrong")
    kb.button(text="B", callback_data="t3_wrong2")
    kb.button(text="C", callback_data="t3_correct")
    kb.adjust(1)

    await callback.message.answer(TASK3_OBSIDIAN, reply_markup=kb.as_markup())
    await state.set_state(Practicum.task3)
    await callback.answer()


@dp.callback_query(F.data.startswith("t3_"))
async def check_task3(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task3_done")

    if callback.data == "t3_correct":
        result = (
            "✅ <b>В точку! Оба фильтра не сработали.</b>\n\n"
            "<b>Проблема 1:</b> Второй товар имеет <code>status: \"archived\"</code> при фильтре <code>status=active</code>.\n\n"
            "<b>Проблема 2:</b> У второго товара <code>price = old_price = 2500</code> — скидки нет при фильтре <code>has_discount=true</code>.\n\n"
            "<b>Последствия:</b> Пользователи видят неактуальные товары, кликают → 404 или ошибка.\n\n"
            "<b>Как должно быть:</b> API должен применять все фильтры на стороне бэкенда."
        )
    elif callback.data == "t3_wrong":
        result = "❌ Частично верно, но проблема шире. Посмотри на второй товар внимательнее."
    else:
        result = "❌ Частично верно. Но первый товар со скидкой, а второй — archived и без скидки."

    kb = InlineKeyboardBuilder()
    kb.button(text="Последняя задача ➡", callback_data="start_task4")
    kb.adjust(1)

    await callback.message.answer(
        f"{result}\n\nОсталась ещё одна задача!",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


# ─── ЗАДАЧА 4: Cart Item (отрицательное quantity) ──────────────────────────

TASK4_OBSIDIAN = (
    "<b>📄 Документация метода:</b>\n\n"
    "<blockquote><b>PATCH /api/cart/items/55</b>\n\n"
    "Body:\n<code>{\n"
    '  "quantity": -1\n'
    "}</code></blockquote>\n\n"
    "<b>🌐 Фактический ответ:</b>\n\n"
    "<blockquote><code>{\n"
    '  "cart_id": "abc-123",\n'
    '  "item_id": 55,\n'
    '  "new_quantity": -1,\n'
    '  "total_price": -499.00\n'
    "}</code></blockquote>\n\n"
    "<b>Что не так в этом ответе?</b>\n\n"
    "A. quantity = -1 — отрицательное количество\n"
    "B. total_price = -499.00 — отрицательная цена\n"
    "C. И quantity, и total_price — оба бага\n"
    "\n"
    "👇 Выбери вариант"
)


@dp.callback_query(F.data == "start_task4")
async def start_task4(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task4_view")

    kb = InlineKeyboardBuilder()
    kb.button(text="A", callback_data="t4_wrong")
    kb.button(text="B", callback_data="t4_wrong2")
    kb.button(text="C", callback_data="t4_correct")
    kb.adjust(1)

    await callback.message.answer(TASK4_OBSIDIAN, reply_markup=kb.as_markup())
    await state.set_state(Practicum.task4)
    await callback.answer()


@dp.callback_query(F.data.startswith("t4_"))
async def check_task4(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "task4_done")

    if callback.data == "t4_correct":
        result = (
            "✅ <b>В точку! Оба варианта — баги.</b>\n\n"
            "Сервер принял отрицательное количество и посчитал отрицательную цену.\n\n"
            "<b>Риск:</b> Злоумышленник может:\n"
            "• «Вернуть» товары и получить деньги\n"
            "• Манипулировать итоговой суммой заказа\n"
            "• Сломать отчётность и аналитику\n\n"
            "<b>Как должно быть:</b> Валидация на бэкенде должна отклонять <code>quantity <= 0</code> с ошибкой <code>400 Bad Request</code>."
        )
    elif callback.data == "t4_wrong":
        result = "❌ Верно, но неполно. quantity=-1 это же не могло дать нормальную цену, правда?"
    else:
        result = "❌ total_price=-499 — это следствие, а не первопричина."

    kb = InlineKeyboardBuilder()
    kb.button(text="Узнать, что дальше ➡", callback_data="after_tasks")
    kb.adjust(1)

    await callback.message.answer(
        f"{result}\n\n<b>Ты прошёл мини-практикум! 👏</b>\n\n"
        "4 задачи позади. Хочешь узнать, как ловить такие баги на реальных проектах?",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════
#  ПОТОК 2: ПРОГРЕВ К ПОКУПКЕ
# ═══════════════════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "after_tasks")
async def after_tasks(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "after_tasks")

    msg = (
        "<b>История из продакшена</b>\n\n"
        "Один из первых рабочих багов:\n\n"
        "Я тестировал метод создания заказа, отправлял данные в Postman и проверял в БД. "
        "На тесте всё ок, веду задачу в релиз. И после раскатки на прод… "
        "<b>0 заказов в работе!</b> 100% новых заказов зависают сразу после создания.\n\n"
        "А всё дело в мелочи: заказ создаётся со статусом <code>\"NEW \"</code> вместо <code>\"NEW\"</code> "
        "и просто игнорируется системой.\n\n"
        "Пользователь оплатил товар, но склад его не видит, письмо с чеком не уходит. "
        "Заказы копятся в базе «мёртвым грузом».\n\n"
        "Я читал документацию. Разработчик тоже. Мы оба не подумали о пробелах, "
        "потому что привыкли к «стерильным» условиям учебных задач.\n\n"
        "<i>Только багованный API учит вниманию к деталям.</i>\n\n"
        "Жми «Дальше», чтобы я рассказал, как научиться видеть такие ловушки заранее. 👇"
    )

    await callback.message.answer(msg, reply_markup=kb_next("after_story"))
    await state.set_state(Practicum.msg1_story)
    await callback.answer()


@dp.callback_query(F.data == "after_story")
async def msg_theory_trap(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "msg2_theory")

    msg = (
        "<b>📚 Тупик теории</b>\n\n"
        "После того провала я пытался «добрать» знания везде…\n\n"
        "• <b>Читал умные книги про REST</b> → знал все термины, но всё равно не видел баги в реальных запросах.\n\n"
        "• <b>Проходил популярные курсы</b> → там всё «стерильно». Показывают идеальные кейсы, "
        "а в продакшене — «грязные» баги.\n\n"
        "• <b>Тренировался на учебных апишках</b> → это как учиться водить в NFS Underground. "
        "Багов почти нет, ответственности ноль.\n\n"
        "<b>Результат:</b> я тратил месяцы на учёбу, но моё «чувство бага» оставалось на нуле.\n\n"
        "👇 <b>Какая проблема сейчас больше всего «болит» у тебя?</b>"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="Вижу 200 OK — думаю «успех». А в теле ошибка", callback_data="pain_1")
    kb.button(text="Путаюсь в заголовках авторизации", callback_data="pain_2")
    kb.button(text="Нашёл баг — не знаю, как оформить отчёт", callback_data="pain_3")
    kb.adjust(1)

    await callback.message.answer(msg, reply_markup=kb.as_markup())
    await state.set_state(Practicum.msg2_theory)
    await callback.answer()


@dp.callback_query(F.data.startswith("pain_"))
async def handle_pain_choice(callback: types.CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    pain_map = {
        "pain_1": "200 OK — баг в теле",
        "pain_2": "Авторизация",
        "pain_3": "Оформление баг-репорта",
    }
    pain_text = pain_map.get(callback.data, "Неизвестно")

    # Сохраняем выбор
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE users SET pain_choice = ? WHERE tg_id = ?", (pain_text, tg_id))
    conn.commit()
    conn.close()

    upsert_user(tg_id, callback.from_user.username, "msg2_pain_answered")

    reply_map = {
        "pain_1": (
            "👀 Понятно. 200 OK с ошибкой в теле — классика. "
            "На реальных проектах такое встречается постоянно.\n\n"
            "В API Practicum таких кейсов — вагон. Ты научишься не доверять статус-кодам."
        ),
        "pain_2": (
            "🔐 Авторизация — боль многих. Токены, заголовки, refresh-механизмы… "
            "В API Practicum есть эндпоинты с реальными security-багами."
        ),
        "pain_3": (
            "📝 Баг нашёл — молодец. А оформить так, чтобы разработчик сразу понял "
            "и починил — это искусство. В практикуме есть шаблоны и примеры."
        ),
    }

    reply = reply_map.get(callback.data, "Спасибо за честность!")

    kb = InlineKeyboardBuilder()
    kb.button(text="Покажи, что внутри API Practicum ➡", callback_data="show_inside")
    kb.adjust(1)

    await callback.message.answer(
        f"{reply}\n\n"
        "Такие ловушки не учат на курсах. Их учат на реальных багах.\n"
        "<b>API Practicum</b> — это стенд с 15+ багами, на котором ты "
        "натренируешь «нюх» на ошибки.\n\n"
        "Хочешь посмотреть, что внутри?",
        reply_markup=kb.as_markup()
    )
    await state.set_state(Practicum.msg2_pain)
    await callback.answer()


@dp.callback_query(F.data == "show_inside")
async def show_inside(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "msg3_inside")

    msg = (
        "<b>📦 Что внутри API Practicum</b>\n\n"
        "🔹 <b>Стенд API</b> — реальный сервер с багами (доступ на 30 дней)\n"
        "🔹 <b>Postman-коллекция</b> — 20+ готовых запросов\n"
        "🔹 <b>15+ багов</b> — от простых до security-уязвимостей\n"
        "🔹 <b>Шаблон баг-репорта</b> — как оформлять, чтобы разработчик не переспрашивал\n"
        "🔹 <b>Видео-разборы</b> — объяснение каждого бага\n\n"
        "<i>Всё как на реальном проекте. Только без последствий для продакшена.</i>\n\n"
        "Готов прокачать навык поиска багов? 👇"
    )

    await callback.message.answer(msg, reply_markup=kb_next("show_offer"))
    await state.set_state(Practicum.msg4_inside)
    await callback.answer()


@dp.callback_query(F.data == "show_offer")
async def show_offer(callback: types.CallbackQuery, state: FSMContext):
    upsert_user(callback.from_user.id, callback.from_user.username, "msg5_offer")

    msg = (
        "<b>🎯 API Practicum — твой тренажёр по поиску багов</b>\n\n"
        "✅ Доступ к API-стенду на 30 дней\n"
        "✅ 15+ реальных багов\n"
        "✅ Postman-коллекция\n"
        "✅ Видео-разборы и шаблоны\n\n"
        "<b>Специальная цена: 5 000₽</b>\n\n"
        "<i>Это цена одной сессии код-ревью. Только здесь ты получишь 15+ багов "
        "и научишься видеть их самостоятельно.</i>\n\n"
        "👇 Выбирай:"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Беру! Как оплатить?", callback_data="offer_accept")
    kb.button(text="⏸ Пока нет, расскажи ещё", callback_data="offer_decline")
    kb.adjust(1)

    await callback.message.answer(msg, reply_markup=kb.as_markup())
    await state.set_state(Practicum.msg5_offer)
    await callback.answer()


@dp.callback_query(F.data == "offer_accept")
async def offer_accept(callback: types.CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    update_user_step(tg_id, "offer_accepted")

    upsert_user(tg_id, callback.from_user.username, "offer_accepted")

    kb = InlineKeyboardBuilder()
    kb.button(text="Написать @eddytester", url=CHANNEL_EDDYTESTER)
    kb.adjust(1)

    await callback.message.answer(
        "🚀 <b>Отличный выбор!</b>\n\n"
        "Для оплаты напиши мне в личные сообщения — "
        "я пришлю реквизиты и доступ к API Practicum в течение 15 минут.\n\n"
        "👇 Жми кнопку, чтобы написать:",
        reply_markup=kb.as_markup()
    )
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "offer_decline")
async def offer_decline(callback: types.CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    upsert_user(tg_id, callback.from_user.username, "offer_declined")

    msg = (
        'Вот <b>3 материала</b>, которые помогут прямо сейчас:\n\n'
        '1️⃣ <a href="https://t.me/eddytester/362"><b>Почему API — самый полезный навык для тестировщика</b></a> — про бизнес-логику\n'
        '2️⃣ <a href="https://t.me/eddytester/272"><b>400-ки, о которых молчат на собесах</b></a> — разбор редких HTTP-кодов\n'
        '3️⃣ <a href="https://developer.mozilla.org/ru/docs/Web/HTTP/Status"><b>MDN: HTTP response status codes</b></a> — официальная документация Mozilla\n\n'
        'Если надумаешь — просто напиши /start. Воронка никуда не денется.\n\n'
        '<i>— Эд, @eddytester</i>'
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="📢 @eddytester", url=CHANNEL_EDDYTESTER)
    kb.adjust(1)

    await callback.message.answer(msg, reply_markup=kb.as_markup())
    await state.clear()
    kb.button(text="🛒 Купить API Practicum", url=PRODUCT_LINK)
    kb.button(text="💡 Всё-таки надумал — купить практикум", url=PRODUCT_LINK)
    await callback.answer()


# ─── КНОПКА ВОЗВРАТА К ЗАДАЧАМ ────────────────────────────────────────────

@dp.callback_query(F.data == "back_to_tasks")
async def back_to_tasks(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    msg = (
        "👋 Привет! Это <b>мини-практикум по поиску багов в API</b>.\n\n"
        "4 задачи → разбор → поймёшь, где подтянуться.\n\n"
        "<i>Готов? Жми «Начать» 👇</i>"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="Начать 🚀", callback_data="start_practicum")
    await callback.message.answer(msg, reply_markup=kb.as_markup())
    await state.set_state(Practicum.welcome)
    await callback.answer()


# ─── HELP ───────────────────────────────────────────────────────────────────

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 @eddytester", url=CHANNEL_EDDYTESTER)
    kb.adjust(1)

    await message.answer(
        "<b>🤖 Practicum Bot — помощь</b>\n\n"
        "• /start — начать мини-практикум\n"
        "• /help — эта справка\n\n"
        "По вопросам оплаты и доступа — пиши @eddytester",
        reply_markup=kb.as_markup()
    )


# ─── MAIN ───────────────────────────────────────────────────────────────────

async def main():
    init_db()
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    try:
        await dp.start_polling(bot, handle_as_tasks=True)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
