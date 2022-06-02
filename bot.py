from aiogram import Dispatcher, Bot, types, executor
from aiogram.utils import exceptions
from aiogram.types import ParseMode
from config import bot_token, admin_id, tag_list
from datetime import time, datetime, timedelta, timezone

import olimpiada
import logging
import users
import asyncio

logging.basicConfig(filename="exceptions.log", filemode="a")

bot = Bot(token=bot_token)
dp = Dispatcher(bot)
parse_mode = ParseMode.MARKDOWN


@dp.message_handler(commands=['start'])
async def welcoming(msg: types.Message):
    if msg.from_user.id != msg.chat.id:
        await msg.answer("Извините, но бот пока не работает в группах.")
        await bot.leave_chat(msg.chat.id)
        return

    await msg.answer("Доброго времени суток! Данный бот будет уведомлять вас о новостях с сайта olimpiada.ru")
    await msg.answer("Чтобы фильтровать новости по предметам, по которым хотите получать новости, "
                     "возпользуйтесь командой /tags", reply_markup=types.ReplyKeyboardRemove())
    await msg.answer("Если вы хотите получить список выбранных вами предметов, то используйте /me")


@dp.message_handler(commands=['me'])
async def showing_tags(msg: types.Message):
    if msg.from_user.id != msg.chat.id:
        await msg.answer("Извините, но бот пока не работает в группах.")
        await bot.leave_chat(msg.chat.id)
        return

    user_id = msg.from_user.id

    try:
        tags = await users.get_tags(user_id)
    except Exception as error:
        await bot.send_message(user_id, "Ошибка сервера :(")
        text_for_admin = f"⁉️Почини меня пж. Не могу показать пользователю с user_id={user_id}, его предметы"
        await bot.send_message(admin_id, text_for_admin)
        logging.exception(error)
        return

    if tags == "Все предметы":
        text = "Сейчас вы получаете все новости с сайта olimpiada.ru, " \
               "так как *у вас включён режим \'Все предметы\'*.\n" \
               "Чтобы как-то фильтровать новости, выключите этот режим и выберите несколько предметов, " \
               "по которым хотите получать новости. Для этого есть команта /tags"
        await bot.send_message(user_id, text, parse_mode=parse_mode)

    elif tags == "Ноль предметов":
        text = "Сейчас вы получаете все новости с сайта olimpiada.ru, так как *вы не выбрали предметы* " \
               "по которым хотите получать новости. Чтобы выбрать предметы, используйте команду /tags"
        await bot.send_message(user_id, text, parse_mode=parse_mode)

    else:
        text = "Вы выбрали следующие предметы:\n\n"

        for tag in tags:
            text += f"*{tag}*\n"

        await bot.send_message(user_id, text, parse_mode=parse_mode)


@dp.message_handler(commands=["send"])
async def sending_message(msg: types.Message):
    if msg.chat.id != admin_id:
        return

    try:
        text = msg.text[len("/send "):]
        for user in await users.tables.fetch("users"):
            try:
                user_id = user["user_id"]
                await bot.send_message(user_id, text=text, disable_web_page_preview=True, parse_mode=parse_mode)
            except Exception as error:
                logging.exception(error)

    except Exception as error:
        text = "Не могу отослать сообщения"
        await bot.send_message(admin_id, text=text, disable_web_page_preview=True, parse_mode=parse_mode)
        logging.exception(error)


@dp.message_handler(commands=["get_post"])
async def getting_post(msg: types.Message):
    if msg.chat.id != admin_id:
        return

    try:
        post_id = int(msg.text[len("/get_post "):])

        if post_id is None:
            text_for_admin = f"⁉️Почини меня пж. Бот не может получить post_id"
            await bot.send_message(admin_id, text_for_admin)
            return

        post: users.Post = await olimpiada.get_post(post_id)
        if post is None:
            await asyncio.sleep(3600)
            return

        link_keyboard = types.InlineKeyboardMarkup()

        if len(post.text) < 200:
            text = await post.full_text(f"https://olimpiada.ru/news/{post_id}")

        else:
            text = await post.short_text(f"https://olimpiada.ru/news/{post_id}")
            link_keyboard.add(
                types.InlineKeyboardButton(text="⇩Полный текст", callback_data=f"full_text:{post_id}")
            )

        await bot.send_message(msg.from_user.id, text=text, reply_markup=link_keyboard, parse_mode=parse_mode,
                               disable_web_page_preview=True)

    except Exception as error:
        logging.exception(error)


@dp.message_handler(commands=["tags"])
async def manage_tags(msg: types.Message):
    if msg.from_user.id != msg.chat.id:
        await msg.answer("Извините, но бот пока не работает в группах.")
        await bot.leave_chat(msg.chat.id)
        return

    user_id = msg.from_user.id
    keyboard = types.InlineKeyboardMarkup(row_width=3)

    all_tags = types.InlineKeyboardButton(text="Все предметы", callback_data="tag_id:0")

    for tag_id in range(1, len(tag_list)):
        tag = tag_list[tag_id]
        button = types.InlineKeyboardButton(text=tag, callback_data=f"tag_id:{tag_id}")
        keyboard.insert(button)

    keyboard.add(all_tags)

    text = "Перед вами список предметов. Нажав на соответствующую кнопку, " \
           "вы можете добавить или удалить предмет из избранных.\n\n" \
           "Режим *\"Все предметы\"* даёт вам возможность получать все новости. " \
           "При выключении, предыдущие настройки остаются."

    await bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard, parse_mode=parse_mode)


@dp.callback_query_handler()
async def calling(call: types.CallbackQuery):
    user_id = call.from_user.id

    downloading_keyboard = types.InlineKeyboardMarkup()
    downloading_keyboard.add(types.InlineKeyboardButton(text="Загрузка...", callback_data="None"))

    if call.data[:len("full_text:")] == "full_text:":
        post_id = int(call.data[len("full_text:"):])
        await call.message.edit_reply_markup(downloading_keyboard)
        post = await olimpiada.get_post(post_id)
        text = await post.full_text(f"https://olimpiada.ru/news/{post_id}")
        link_keyboard = types.InlineKeyboardMarkup()
        link_keyboard.add(
            types.InlineKeyboardButton(text="⇧Сжать текст", callback_data=f"short_text:{post_id}"),
        )
        await call.message.edit_text(text=text, parse_mode=parse_mode,
                                     disable_web_page_preview=True, reply_markup=link_keyboard)

    if call.data[:len("short_text:")] == "short_text:":
        post_id = int(call.data[len("short_text:"):])
        await call.message.edit_reply_markup(downloading_keyboard)
        post = await olimpiada.get_post(post_id)
        text = await post.short_text(f"https://olimpiada.ru/news/{post_id}")
        link_keyboard = types.InlineKeyboardMarkup()
        link_keyboard.add(
            types.InlineKeyboardButton(text="⇩Полный текст", callback_data=f"full_text:{post_id}")
        )
        await call.message.edit_text(text=text, parse_mode=parse_mode,
                                     disable_web_page_preview=True, reply_markup= link_keyboard)

    if call.data[:len("tag_id:")] == "tag_id:":
        tag_id = int(call.data[len("tag_id:"):])
        try:
            if tag_id != 0:
                bits = await users.get_bits(user_id)
                if bits % 2 == 1:
                    await call.answer("У вас и так включён режим \'Все предметы\'")
                    return

            await users.reverse_bit(user_id, tag_id)
            tag = tag_list[tag_id]

            if await users.get_bit(user_id, tag_id):
                if tag_id == 0:
                    await call.answer("Режим \'Все предметы\' включён")
                else:
                    await call.answer(f"Предмет \'{tag}\' добавлен")

            else:
                if tag_id == 0:
                    await call.answer("Режим \'Все предметы\' отключён")
                else:
                    await call.answer(f"Предмет \'{tag}\' удалён")

        except Exception as error:
            await call.answer("Ошибка серверв :(")
            text_for_admin = f"⁉️Почини меня пж. Пользователь с user_id={user_id} не может выбрать предмет."
            await bot.send_message(admin_id, text_for_admin)
            logging.exception(error)
            return


async def news():
    while True:
        post_id = await users.get_post_id()

        if post_id is None:
            text_for_admin = f"⁉️Почини меня пж. Бот не может получить post_id"
            await bot.send_message(admin_id, text_for_admin)
            return

        post_id += 1

        post: users.Post = await olimpiada.get_post(post_id)
        if post is None:
            await asyncio.sleep(3600)
            continue

        link_keyboard = types.InlineKeyboardMarkup()

        if len(post.text) < 200:
            text = await post.full_text(f"https://olimpiada.ru/news/{post_id}")

        else:
            text = await post.short_text(f"https://olimpiada.ru/news/{post_id}")
            link_keyboard.add(
                types.InlineKeyboardButton(text="⇩Полный текст", callback_data=f"full_text:{post_id}")
            )

        tags = 0
        for tag_id in range(len(tag_list)):
            tag = tag_list[tag_id]
            if tag in post.tags:
                tags += (1 << tag_id)

        command = f"SELECT user_id FROM users WHERE tags & {tags} != 0 OR tags % 2 = 1 OR tags = 0"
        for user_id in await users.tables.select(command):
            try:
                user_id = user_id[0]
                await bot.send_message(user_id, text=text, reply_markup=link_keyboard, parse_mode=parse_mode,
                                       disable_web_page_preview=True)
            except exceptions.BotBlocked:
                try:
                    await users.tables.execute(f"DELETE from users WHERE user_id = \'{user_id}\'")
                    logging.warning(f"Deleted user with user_id = {user_id}")
                except Exception as error:
                    logging.exception(error)

            except Exception as error:
                logging.exception(error)

        await users.inc_post_id()


async def deleting_posts():
    while True:
        try:

            current_time = datetime.utcnow().timestamp()
            delta = timedelta(days=2).total_seconds()
            lower_bound = int(current_time - delta)

            await users.tables.execute(f"DELETE FROM posts WHERE time < {lower_bound}")
        except Exception as error:
            logging.exception(error)

        await asyncio.sleep(3600*3)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(news())
    loop.create_task(deleting_posts())
    executor.start_polling(dp, skip_updates=True)