from bs4 import BeautifulSoup as Soup
from bs4.element import Tag, TemplateString, NavigableString
import xml.etree.ElementTree as xet
from urllib.parse import urlparse
from pathlib import Path
from typing import cast
import aiohttp
import asyncio
import json
import re
from dataclasses import dataclass

from . import misc


class ParsingError(Exception):
    pass

GET_TEXT_TYPES = (NavigableString, TemplateString,)

def parse_anime_item(item: Tag) -> dict:
    title = item.select_one('div.user-mylist__title a')
    if title != None:
        title = title.get_text(" ", strip=True, types=GET_TEXT_TYPES)

    original_title = item.select_one('div.fw-lighter')
    if original_title != None:
        original_title = original_title.get_text(" ", strip=True, types=GET_TEXT_TYPES)

    episodes = item.select_one('a.link-secondary')
    if episodes != None:
        episodes = episodes.get_text(" ", strip=True, types=GET_TEXT_TYPES)
        episodes = ''.join(episodes.split()[1:])

    user_score = item.select_one('div.user-mylist-rating__value span')
    if user_score != None:
        user_score = user_score.get_text(" ", strip=True, types=GET_TEXT_TYPES)
        user_score = '-' if len(user_score) == 0 else user_score

    return {
        'title': title,
        'original_title': original_title,
        'user_score': user_score,
        'episodes': episodes,
    }


async def parse_list(session: aiohttp.ClientSession, *, profile_url: str, show_progress_bar: bool) -> list:
    URL = "https://animego.me/user/mylist/%d/%d"
    RECORD_TYPES = [
        ("Watching",   1, "Смотрю"),
        ("Completed",  2, "Просмотрено"),
        ("OnHold",     3, "Отложено"),
        ("Dropped",    4, "Брошено"),
        ("Planned",    5, "Запланировано"),
        ("Rewatching", 6, "Пересматриваю"),
    ]
    parsed_profile_url = urlparse(profile_url)
    user_id = int(Path(parsed_profile_url.path).name)

    anime_list = []

    r = await session.get(profile_url)
    if r.status != 200:
        raise ParsingError(f"Request error (Status code {r.status}): '{await r.text()}'")

    soup = Soup(await r.text(), features='html.parser')
    items_count = {
        int(str(button['href']).split('=')[1]): int(cast("Tag", button.select_one('span')).get_text(" ", strip=True))
        for button in soup.select('a[data-action="click->profile-my-list#selectType"]')
        if str(button['href']).split('=')[1] != 'all'
    }

    for user_status_name, user_status_value, user_status_label in RECORD_TYPES:
        last_page = False
        item_count = 0
        page = 1

        if show_progress_bar:
            misc.progress_bar(0,
                target=items_count[user_status_value],
                prefix=f'Parsing list "{user_status_label}"',
            )

        while not last_page:
            r = await session.get(URL % (user_id, page),
                params={
                    "type[name]": user_status_name,
                    "type[value]": user_status_value,
                    "entities": "true",
                },
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                })

            if r.status != 200:
                raise ParsingError(f"Request error (Status code {r.status}): '{await r.text()}'")
            await asyncio.sleep(0.5)

            soup = Soup(await r.text(), features="html.parser")
            page += 1

            for item in soup.select("div.user-mylist__item div.user-mylist__body"):
                anime_item = parse_anime_item(item)

                anime_page_url = item.select_one('.user-mylist__title a')
                anime_page_url = anime_page_url.get('href') if anime_page_url != None else None
                anime_page_url = misc.BASE_URL + str(anime_page_url) if anime_page_url != None else None
                release_type = "–"

                if anime_page_url != None:
                    r = await session.get(anime_page_url)
                    await asyncio.sleep(0.5)
                    if r.status == 200:
                        soup = Soup(await r.text(), features='html.parser')
                        release_type = soup.select_one('.entity-field div.text-break')
                        release_type = release_type.get_text(" ", strip=True, types=GET_TEXT_TYPES) if release_type != None else "–"

                anime_item['release_type'] = release_type
                anime_item['user_status'] = user_status_label

                anime_list.append(anime_item)
                item_count += 1

                if show_progress_bar:
                    misc.progress_bar(item_count,
                        target=items_count[user_status_value],
                        prefix=f'Parsing list "{user_status_label}"',
                    )

            last_page = (item_count == items_count[user_status_value])

    return anime_list


def generate_xml(anime_list: list, indent: int | None) -> str:
    anime_list_xml = xet.Element("AnimeList")

    for anime in anime_list:
        anime_xml = xet.SubElement(anime_list_xml, "Anime")
        xet.SubElement(anime_xml, "title").text = anime["title"]
        xet.SubElement(anime_xml, "originalTitle").text = anime["original_title"]
        xet.SubElement(anime_xml, "userStatus").text = anime["user_status"]
        xet.SubElement(anime_xml, "userScore").text = anime["user_score"]
        xet.SubElement(anime_xml, "episodes").text = anime["episodes"]
        xet.SubElement(anime_xml, "releaseType").text = anime["release_type"]

    if type(indent) == int:
        xet.indent(anime_list_xml, space=' ' * indent, level=0)
    return xet.tostring(anime_list_xml, encoding='unicode')


def generate_json(anime_list: list, indent: int | None) -> str:
    return json.dumps(anime_list, indent=indent, ensure_ascii=False)
