import requests
from bs4 import BeautifulSoup as Soup
import json
import xml.etree.ElementTree as xet
import argparse
import sys


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36",
}

URL = "https://animego.me/user/%s/mylist/anime"


class ParsingError(Exception):
    pass


def parse_single_page(session: requests.Session, username: str, page: int, output: list) -> bool:
    r = session.get(URL % username,
        params={"type": "mylist", "page": page},
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })

    if r.status_code != 200:
        raise ParsingError(f"Request error (Status code {r.status_code}): '{r.text}'")

    r = r.json()
    if r["status"] != "success":
        raise ParsingError(f"Server error: {r['status']}")

    content = r["content"]
    lastPage = r["endPage"]

    soup = Soup(content, features="html.parser")

    for row in soup.select("tr"):
        columns = row.select("td")
        small_poster = columns[0].find("img")["src"]
        poster = columns[0].find("img")["srcset"]
        title = columns[1].find("a").get_text().strip()
        original_title = columns[1].find("div").get_text().strip()
        user_status = columns[2].find("span").get_text().strip()
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

    return not lastPage


def parse_list(session: requests.Session, username: str) -> list | None:
    try:
        page = 1
        anime_list = []
        while parse_single_page(session, username, page, anime_list): page += 1
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


def main():
    parser = argparse.ArgumentParser(
        description="Anime list parser. ")

    parser.add_argument("--username", type=str,
        help="Anime list owner username", required=True)
    parser.add_argument("--output", type=str,
        help="Output file name (stdout if not specified)", required=False)
    parser.add_argument("--format", type=str,
        help="Output file format (json by default)",
        default="json", required=False)

    args = parser.parse_args()

    if args.format not in {'json', 'xml'}:
        print("animego-parser error: supported formats: json, xml")

    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(URL) # Update cookies

    anime_list = parse_list(session, args.username)

    if args.format == "json":
        data = json.dumps(anime_list, indent=4, ensure_ascii=False)
    elif args.format == "xml":
        data = generate_xml(anime_list, indent=4)

    if args.output:
        with open(args.output, 'w', encoding="utf-8") as file:
            file.write(data)
    else:
        sys.stdout.write(data)

if __name__ == "__main__":
    main()
