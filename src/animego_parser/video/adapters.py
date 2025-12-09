from dataclasses import dataclass
from bs4 import BeautifulSoup as Soup
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Dict, List, Optional, cast
import logging as log
import aiohttp
from kodik import Page, PlayerData


async def request_player_url(session: aiohttp.ClientSession, anime_page_url: str) -> Optional[str]:
    r = await session.get(anime_page_url)
    if r.status != 200: return None

    soup = Soup(await r.text(), features="html.parser")

    soup = soup.select('#video-player')[0]
    player_options_url = soup.get('data-ajax-url')
    if player_options_url == None: return None
    player_options_url = urljoin(anime_page_url, cast(str, player_options_url))

    r = await session.get(player_options_url, params={
        "_allow": "true",
    }, headers={
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "X-Requested-With": "XMLHttpRequest",
        "Host": cast(str, urlparse(anime_page_url).hostname),
        "Referer": anime_page_url,
    })
    if r.status != 200: return None

    r = await r.json()
    if r.get("status") != "success": return None

    soup = Soup(r["content"], features="html.parser")
    players_buttons = soup.select("div[aria-labelledby=\"video-players-tab\"] > span.video-player-toggle-item")

    # Keep this for Xmas
    translations_buttons = soup.select("div[aria-labelledby=\"video-dubbing-tab\"] > span.video-player-toggle-item")
    translations = {
        item.getText(strip=True): item.get("data-dubbing")
        for item in translations_buttons
    }

    players_links = [
        {
            "id": item.get("data-provider"),
            "dubbing": item.get("data-provide-dubbing"),
            "name": item.getText(strip=True),
            "url": "https:" + str(item.get("data-player")),
        }
        for item in players_buttons
    ]

    kodik_player_links = list(filter(
        lambda link: link["name"] == "Kodik",
        players_links
    ))

    if len(kodik_player_links) == 0:
        return None

    link = urlparse(kodik_player_links[0]["url"])
    return urlunparse((
        link.scheme, link.hostname, link.path, "", "", ""
    ))

@dataclass
class AnimePage:
    url: str
    body: str
    translations: List[Dict[str, str]]
    episodes: List[Dict[str, str]]


async def request_anime_page(session: aiohttp.ClientSession, url: str) -> Optional["AnimePage"]:
    r = await session.get(url)
    if r.status != 200: return None

    soup = Soup(await r.text())

    translations_buttons = soup.select("div[aria-labelledby=\"video-dubbing-tab\"] > span.video-player-toggle-item")
    translations = {
        item.getText(strip=True): item.get("data-dubbing")
        for item in translations_buttons
    }
