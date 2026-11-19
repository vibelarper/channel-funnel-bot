import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@larpitsehr")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "")  # Токен от ЮKassa/RoboKassa из @BotFather

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB_FILE = "subscribers.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

def add_user(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

# Клавиатура: бесплатный бонус за подписку ИЛИ покупка VIP-доступа
# В начале файла:


# В блоке клавиатуры main_kb:
main_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал",url=f"https://t.me{CHANNEL_ID}")],
        [InlineKeyboardButton(text="✅ Забрать бесплатный гайд", callback_data="check_sub")],
        [InlineKeyboardButton(text="💳 Купить VIP-доступ (500 ₽)", callback_data="buy_vip")]
    ]
)


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    add_user(message.from_user.id)
    await message.answer(
        f"Привет, {message.from_user.first_name}! 🎁\n"
        "Подпишись на канал, чтобы забрать бесплатный гайд, или оформи подписку на закрытый VIP-клуб:",
        reply_markup=main_kb
    )

# Проверка подписки
@dp.callback_query(F.data == "check_sub")
async def verify_sub(callback: types.CallbackQuery):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=callback.from_user.id)
        if member.status in ["member", "administrator", "creator"]:
            await callback.message.answer("🎉 Подписка подтверждена! Вот ваш бесплатный гайд: https://telegra.ph")
            await callback.answer()
        else:
            await callback.answer("❌ Вы ещё не подписались на канал!", show_alert=True)
    except Exception:
        await callback.answer("⚠️ Ошибка: добавьте бота администратором в канал.", show_alert=True)

# Выставление счёта на оплату
@dp.callback_query(F.data == "buy_vip")
async def send_vip_invoice(callback: types.CallbackQuery):
    if not PAYMENT_TOKEN:
        await callback.answer("⚠️ Оплата в демо-режиме (не задан PAYMENT_TOKEN в Railway).", show_alert=True)
        return

    await callback.message.answer_invoice(
        title="Доступ в закрытый VIP-клуб",
        description="Подписка на 30 дней с закрытыми уроками и разборами",
        payload="vip_access_30d",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка на 1 месяц", amount=50000)]  # 500.00 ₽
    )
    await callback.answer()

# Подтверждение платежа
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

# Выдача доступа после успешной оплаты
@dp.message(F.successful_payment)
async def success_payment(message: types.Message):
    await message.answer(
        "✅ Оплата прошла успешно! Добро пожаловать в VIP-клуб.\n"
        "Ваша персональная ссылка для входа: https://t.me+ваша_закрытая_ссылка"
    )
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"💰 Новая оплата VIP-доступа от @{message.from_user.username}!")

# Админ-команды
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"👥 Пользователей в базе: <b>{len(get_users())}</b>", parse_mode="HTML")

@dp.message(Command("send"))
async def cmd_send(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/send", "").strip()
    if not text:
        await message.answer("Пример: <code>/send Всем привет!</code>", parse_mode="HTML")
        return
    sent = 0
    for uid in get_users():
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            pass
    await message.answer(f"✅ Доставлено: {sent} чел.")

async def main():
    init_db()
    print("Бот с оплатой и воронкой запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
