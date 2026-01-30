from bs4 import BeautifulSoup as Soup, Tag
import xml.etree.ElementTree as xet
from urllib.parse import urlparse
from pathlib import Path
from typing import cast
import aiohttp
import asyncio
import json
import re

from . import misc


class ParsingError(Exception):
    pass


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
        int(str(button['href']).split('=')[1]): int(cast("Tag", button.select_one('span')).get_text())
        for button in soup.select('a[data-dynamic="[data-dynamic-user-mylist]"]')
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

            r = await r.json()
            if r["status"] != "success":
                raise ParsingError(f"Server error: {r['status']}")

            content = r["data"]["content"]
            last_page = r["data"]["endPage"]
            page += 1

            soup = Soup(content, features="html.parser")

            for row in soup.select(".user-mylist__item"):
                columns = row.select("td")

                title = row.select_one('.user-mylist__title')
                if title != None: title = title.get_text().strip()

                original_title = row.select_one('.fw-lighter')
                if original_title != None: original_title = original_title.get_text().strip()

                user_score = row.select_one('.user-mylist-rating__value span[data-rating-value]')
                user_score = user_score.get_text().strip() if user_score != None else ""
                user_score = user_score if len(user_score) > 0 else "–"

                episodes = row.select_one('a.link-secondary')
                if episodes != None:
                    m = re.search(r'(\d+)\s*?\/\s*?(\d+)', episodes.get_text().strip())
                    episodes = m.group(1) + '/' + m.group(2) if m != None else "–"
                else:
                    episodes = "–"

                anime_page_url = row.select_one('.user-mylist__title a')
                anime_page_url = anime_page_url.get('href') if anime_page_url != None else None
                anime_page_url = misc.BASE_URL + str(anime_page_url) if anime_page_url != None else None
                release_type = "–"

                if anime_page_url != None:
                    r = await session.get(anime_page_url)
                    await asyncio.sleep(0.5)
                    if r.status == 200:
                        soup = Soup(await r.text(), features='html.parser')
                        release_type = soup.select_one('.entity-field div.text-break')
                        release_type = release_type.get_text().strip() if release_type != None else "–"

                anime_list.append({
                    "title": title,
                    "original_title": original_title,
                    "user_status": user_status_label,
                    "user_score": user_score,
                    "episodes": episodes,
                    "release_type": release_type,
                })

                item_count += 1
                if show_progress_bar:
                    misc.progress_bar(item_count,
                        target=items_count[user_status_value],
                        prefix=f'Parsing list "{user_status_label}"',
                    )

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
