from markdownify import markdownify
from bs4 import BeautifulSoup
import requests
import logging
import users


def md(*args, **kwargs):
    return markdownify(*args, **kwargs).replace("\xa0", " ")


async def get_post(post_id: int):
    """Получаем данные с какой-то новости еа сайте olimpiada.ru"""

    # проверяем на наличие в базе данных
    try:
        post = await users.find_post(post_id)
        if post is not None:
            return post
    except Exception as error:
        logging.exception(error)

    page = requests.get(f"https://olimpiada.ru/news/{post_id}/")

    # проверяем, что такая страница есть
    if not page.ok:
        return None

    soup = BeautifulSoup(page.text, "html.parser")

    res = users.Post()

    left_part = soup.find("div", class_="news_left")  # часть с текстом поста
    right_part = soup.find("div", class_="news_right")  # часть с текстом прикреплённой олимпиады
    subject_tags = soup.find("div", class_="subject_tags")  # часть c тегами
    head_part = soup.find("h1", class_="headline")  # часть с заголовком

    # пытаемся добыть заголовок
    if head_part is not None:
        try:
            res.head = md(str(head_part), strip=['h1'])
        except Exception as error:
            logging.exception(error)
    else:
        return None

    # пытаемся добыть основной текст
    if left_part is not None:
        try:
            full_text = left_part.find("div", class_="full_text")
            text_parts = []

            for elem in full_text.contents:
                if elem.name == "p" or elem.name == "ol":
                    try:
                        text_parts.append(markdownify(str(elem)).strip())
                    except Exception as error:
                        logging.exception(error)
                if elem.name == "ul":
                    try:
                        text = ""
                        for li in elem.find_all("li"):
                            text += '◾ ' + markdownify(str(li), strip=['li']).strip() + "\n"
                        text_parts.append(text.strip())
                    except Exception as error:
                        logging.exception(error)
            res.text = "\n\n".join(text_parts)

        except Exception as error:
            logging.exception(error)

    # пытаемся добыть теги
    if subject_tags is not None:

        try:
            for subject_tag in subject_tags.find_all("span", class_="subject_tag"):
                text = md(str(subject_tag))[1:]
                res.tags.append(text)

        except Exception as error:
            logging.exception(error)

    # пытаемся добыть олимпиаду, которая связанна с постом
    if right_part is not None:
        try:
            for olimp_for_news in right_part.find_all("div", class_="olimp_for_news"):
                href = olimp_for_news.find("a")["href"]
                activity_id = int(href[len("/activity/"):])
                res.olimp.append(activity_id)
        except Exception as error:
            logging.exception(error)

    # проверяем что олимпиада перечневая
    for activity_id in res.olimp:
        if await users.tables.fetchrow("level_activity", activity_id=activity_id) is not None:
            res.head = "⭐️" + res.head
            break

    # добавляем пост в базу данных
    try:
        await users.insert_post(post_id, res)
    except Exception as error:
        logging.exception(error)

    return res