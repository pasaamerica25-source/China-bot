"""
Телеграм-бот: консультация + приём заказов + ответы клиенту через reply.

Установка:   pip install "aiogram>=3.4"
Запуск:      BOT_TOKEN=токен_от_BotFather ADMIN_ID=ваш_телеграм_id python china_bot.py
(ADMIN_ID узнайте у бота @userinfobot)

Как работает:
- Клиент нажимает «Сделать заказ» и пишет, что нужно (текст, фото, ссылки).
- Бот присылает это вам. Вы отвечаете reply (ответом) на сообщение бота —
  ответ уходит клиенту.
- Любое другое сообщение клиента тоже приходит вам как вопрос.
"""
import asyncio
import json
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
LINKS_FILE = "links.json"

# ====== РЕДАКТИРУЙТЕ ПОД СЕБЯ ======
WELCOME = (
    "Привет! 👋 Я помогу с заказом товаров из Китая.\n"
    "Выберите раздел ниже или просто напишите свой вопрос."
)

# Кнопка -> текст ответа. Добавляйте свои разделы.
INFO = {
    "💰 Цены и комиссия": "Здесь напишите про цены, курс, вашу комиссию.",
    "🚚 Доставка и сроки": "Здесь напишите про способы доставки и сроки.",
    "💳 Оплата": "Здесь напишите, как и чем можно оплатить.",
    "❓ Как заказать": "1. Нажмите «Сделать заказ»\n2. Опишите товар (ссылка, фото, размер, цвет, кол-во)\n3. Я пришлю расчёт стоимости.",
}
BTN_ORDER = "📦 Сделать заказ"
BTN_QUESTION = "💬 Задать вопрос"
# ===================================


class Flow(StatesGroup):
    order = State()


dp = Dispatcher()


def load_links() -> dict:
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


links = load_links()  # id сообщения у админа -> id клиента


def save_links() -> None:
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f)


def menu() -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=BTN_ORDER)]]
    rows += [[KeyboardButton(text=t)] for t in INFO]
    rows.append([KeyboardButton(text=BTN_QUESTION)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


async def to_admin(bot: Bot, m: Message, title: str) -> None:
    u = m.from_user
    name = u.full_name + (f" (@{u.username})" if u.username else "")
    head = await bot.send_message(
        ADMIN_ID,
        f"{title}\n👤 {name}\nID: {u.id}\n\n↩️ Ответьте (reply) на это сообщение — ответ уйдёт клиенту.",
    )
    copy = await bot.copy_message(ADMIN_ID, m.chat.id, m.message_id)
    for x in (head, copy):
        links[str(x.message_id)] = m.chat.id
    save_links()


# ---------- Админ: reply -> клиенту ----------
@dp.message(F.chat.id == ADMIN_ID, F.reply_to_message)
async def admin_reply(m: Message):
    cid = links.get(str(m.reply_to_message.message_id))
    if not cid:
        await m.reply("Не нашёл, какому клиенту отправить. Ответьте на сообщение, пришедшее от бота.")
        return
    try:
        await m.copy_to(cid)
        await m.react([{"type": "emoji", "emoji": "👍"}])
    except Exception as e:  # клиент мог заблокировать бота
        await m.reply(f"Не удалось отправить: {e}")


@dp.message(F.chat.id == ADMIN_ID)
async def admin_other(m: Message):
    await m.answer("Чтобы ответить клиенту, сделайте reply на его сообщение.")


# ---------- Клиент ----------
@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(WELCOME, reply_markup=menu())


@dp.message(F.text == BTN_ORDER)
async def order_begin(m: Message, state: FSMContext):
    await state.set_state(Flow.order)
    await m.answer(
        "Напишите, что хотите заказать: ссылка или фото товара, размер, цвет, количество. "
        "Можно отправить одним или несколькими сообщениями — первое сообщение уйдёт как заказ."
    )


@dp.message(F.text == BTN_QUESTION)
async def question_begin(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Напишите свой вопрос — я передам его и скоро отвечу.")


@dp.message(F.text.in_(set(INFO)))
async def info(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(INFO[m.text])


@dp.message(Flow.order)
async def order_receive(m: Message, state: FSMContext, bot: Bot):
    await to_admin(bot, m, "📦 НОВЫЙ ЗАКАЗ")
    await state.clear()
    await m.answer("✅ Заказ принят! Скоро напишу вам с расчётом.", reply_markup=menu())


@dp.message()
async def any_message(m: Message, bot: Bot):
    await to_admin(bot, m, "💬 Сообщение от клиента")
    await m.answer("Передал, скоро отвечу 🙌")


async def main():
    logging.basicConfig(level=logging.INFO)
    if not TOKEN or not ADMIN_ID:
        raise SystemExit("Задайте BOT_TOKEN и ADMIN_ID")
    await dp.start_polling(Bot(TOKEN))


if __name__ == "__main__":
    asyncio.run(main())
