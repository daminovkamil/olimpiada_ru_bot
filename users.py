import datetime
import logging
from database import Tables
from config import tag_list, database_link

tables = Tables(database_link)


class Post:
    """
    Определения:

    head: str - заголовок поста
    text: str - основной текст новости
    olymp: list of int - список id прикреплённых записей
    tags: list of str - предметы этой новости
    """

    none_head = "Нет заголовка"
    none_text = "Нет текста"

    def __init__(self, head="Нет заголовка", text="Нет заголовка", olymp=None, tags=None):
        self.head = head
        self.text = text
        if olymp is None:
            self.olymp = []
        else:
            self.olymp = olymp

        if tags is None:
            self.tags = []
        else:
            self.tags = tags

    async def full_text(self, post_link: str) -> str:
        text = f"[{self.head}]({post_link})"
        text += "\n\n"
        text += self.text
        text += "\n\n"
        text += " ".join(["#" + tag.replace(" ", "") for tag in self.tags])
        return text

    async def short_text(self, post_link: str) -> str:
        text = f"[{self.head}]({post_link})"
        text += "\n\n"

        if '.' in self.text or '!' in self.text or '?' in self.text:
            i = len(self.text)

            for symbol in ['.', '!', '?']:
                if symbol in self.text:
                    i = min(i, self.text.find(symbol) + 1)

            while i != len(self.text) and not self.text[i].isspace():
                i += 1
            text += self.text[:i]
            text += "\n\n"

        text += " ".join(["#" + tag.replace(" ", "") for tag in self.tags])
        return text


async def user_exist(user_id: int):
    return await tables.fetchrow("users", user_id=user_id) is not None


async def add_user(user_id: int):
    """Добавление пользователя, если его 100% нет"""
    await tables.insert("users", user_id=user_id)


async def get_bits(user_id):
    if not await user_exist(user_id):
        await add_user(user_id)

    row = await tables.fetchrow("users", user_id=user_id)
    tags = row.get("tags")
    return tags


async def get_bit(user_id: int, tag_id: int):
    tags = await get_bits(user_id)

    return bool(tags & (1 << tag_id))


async def reverse_bit(user_id: int, tag_id: int):
    tags = await get_bits(user_id)
    tags ^= (1 << tag_id)

    await tables.execute(f"UPDATE users SET tags = \'{tags}\' WHERE user_id = \'{user_id}\'")


async def get_tags(user_id: int):
    res = []
    tags = await get_bits(user_id)

    if tags % 2 == 1:
        return "Все предметы"

    if tags == 0:
        return "Ноль предметов"

    for tag_id in range(len(tag_list)):
        if tags & (1 << tag_id):
            res.append(tag_list[tag_id])

    return res


async def get_post_id():
    try:
        post_id = await tables.fetchrow("post")
        return post_id["post_id"]

    except Exception as error:
        logging.exception(error)
        return None


async def inc_post_id():
    try:
        await tables.execute("UPDATE post SET post_id = post_id + 1")
    except Exception as error:
        logging.exception(error)


async def find_post(post_id: int):
    try:
        res = await tables.fetchrow("posts", post_id=post_id)
        if res is None:
            return None
        else:

            head = res["head"]
            text = res["text"]
            olymp = res["olymp"]
            tags = res["tags"]

            return Post(head, text, olymp, tags)

    except Exception as error:
        logging.exception(error)


async def insert_post(post_id: int, post: Post):
    if await find_post(post_id) is None:
        try:

            head = post.head
            text = post.text
            olymp = '{' + ', '.join(str(elem) for elem in post.olymp) + '}'
            tags = '{' + ', '.join(str(elem) for elem in post.tags) + '}'
            time = int(datetime.datetime.utcnow().timestamp())

            await tables.insert("posts", post_id=post_id, head=head, text=text, olymp=olymp, tags=tags, time=time)
        except Exception as error:
            logging.exception(error)