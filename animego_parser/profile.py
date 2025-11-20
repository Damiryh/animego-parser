from bs4 import BeautifulSoup as Soup
import xml.etree.ElementTree as xet
import aiohttp
import json


class ParsingError(Exception):
    pass


async def parse_single_page(session: aiohttp.ClientSession, *, username: str, page: int, output: list) -> bool:
    URL = "https://animego.me/user/%s/mylist/anime"

    r = await session.get(URL % username,
        params={"type": "mylist", "page": page},
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })

    if r.status != 200:
        raise ParsingError(f"Request error (Status code {r.status}): '{r.text}'")

    r = await r.json()
    if r["status"] != "success":
        raise ParsingError(f"Server error: {r['status']}")

    content = r["content"]
    last_page = r["endPage"]

    soup = Soup(content, features="html.parser")

    for row in soup.select("tr"):
        columns = row.select("td")

        title = columns[1].find("a")
        if title != None: title = title.get_text().strip()

        original_title = columns[1].find("div")
        if original_title != None: original_titl = original_title.get_text().strip()

        user_status = columns[2].find("span")
        if user_status != None: user_status = user_status.get_text().strip()

        user_score = columns[3].get_text().strip()
        episodes = columns[4].get_text().strip().replace(' ', '')
        release_type = columns[5].get_text().strip()

        output.append({
            "title": title,
            "original_title": original_title,
            "user_status": user_status,
            "user_score": user_score,
            "episodes": episodes,
            "release_type": release_type,
        })

    return not last_page


async def parse_list(session: aiohttp.ClientSession, username: str) -> list | None:
    try:
        page = 1
        last_page = False
        anime_list = []

        while not last_page:
            last_page = await parse_single_page(session, username=username, page=page, output=anime_list)
            page += 1

        return anime_list

    except ParsingError as e:
        print(e)
        return None

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
