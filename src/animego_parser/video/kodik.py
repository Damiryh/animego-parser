import asyncio
from urllib.parse import unquote, urlparse, urlunparse
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup as Soup
from dataclasses import dataclass
from base64 import b64decode
from pathlib import Path
import logging as log
import aiohttp
import json
import re


@dataclass
class Page:
    url: str
    body: str

    def __repr__(self) -> str:
        return f"<File \"{self.url}\">"

    def soup(self) -> "Soup":
        return Soup(self.body, features="html.parser")


@dataclass
class PlayerData:
    domain: str
    domain_sign: str
    reference: str
    reference_sign: str
    player_domain: str
    player_domain_sign: str
    player_url: str
    endpoint: str

    @classmethod
    def parse(cls, player_page: "Page", player_script: "Page") -> Optional["PlayerData"]:
        soup = player_page.soup()
        player_init_script = soup.select('script')[0]
        data = re.search(r"var urlParams = '(.*?)';", player_init_script.text)

        if data == None:
            log.warning(f'urlParams isn\'t found')
            return None

        data = json.loads(data.group(1))

        endpoint = re.search(r'type:"POST",url:atob\("(.*?)"\),', player_script.body)
        if endpoint == None:
            log.warning(f'endpoint isn\'t found')
            return None

        endpoint = b64decode(endpoint.group(1)).decode('utf-8')
        endpoint = urlunparse(('https', data['pd'], endpoint, None, None, None))

        return cls(
            domain=data['d'],
            domain_sign=data['d_sign'],
            reference=unquote(data['ref']),
            reference_sign=data['ref_sign'],
            player_domain=data['pd'],
            player_domain_sign=data['pd_sign'],
            player_url=player_page.url,
            endpoint=endpoint,
        )

    def sign(self) -> Dict[str, str]:
        return {
            'd': self.domain,
            'd_sign': self.domain_sign,
            'pd': self.player_domain,
            'pd_sign': self.player_domain_sign,
            'ref': self.reference,
            'ref_sign': self.reference_sign,
            'bad_user': 'false',
            'cdn_is_working': 'true',
        }


@dataclass
class Video:
    quality: str
    url: str

    @staticmethod
    def decode_url(encoded_url: str) -> str:
        if '//' in encoded_url: return encoded_url
        decode = lambda c: (chr(c) if ((90 if c <= 'Z' else 122) >= (c := ord(c) + 18)) else chr(c - 26)) if c.isalpha() else c
        return b64decode(''.join([decode(ch) for ch in encoded_url]) + '===========').decode('utf-8')


@dataclass
class Episode:
    id: int
    index: int
    season: str
    season_name: str
    hash: str
    title: str
    assets: Optional[List["Video"]] = None

    @classmethod
    def parse_list(cls, player_page: "Page") -> Optional[List["Episode"]]:
        soup = player_page.soup()
        seasons = soup.select('.series-options div')
        if len(seasons) == 0: return None
        episodes = []

        season_names = dict([
            (f'season-{str(season["value"])}', str(season['data-title']))
            for season in soup.select('.serial-seasons-box option')
        ])

        for season in seasons:
            options = season.select('option')
            if len(options) == 0: return None

            for option in options:
                episodes.append(Episode(
                id=int(str(option['data-id'])),
                index=int(str(option['value'])),
                season=str(season['class'][0]),
                season_name=season_names[str(season['class'][0])],
                hash=str(option['data-hash']),
                title=str(option['data-title']),
            ))

        return episodes

    async def request_assets(self, session: aiohttp.ClientSession, player_data: Optional["PlayerData"], translation: Optional["Translation"]) -> bool:
        self.assets = await request_episode(session, player_data, translation, self)
        return self.assets != None


@dataclass
class Translation:
    id: int
    hash: str
    type: str
    title: str
    episodes: Optional[List["Episode"]] = None

    @classmethod
    def parse_list(cls, player_page: "Page") -> Optional[List["Translation"]]:
        soup = player_page.soup()
        options = soup.select('.serial-translations-box select option')

        if len(options) == 0: # Возможно, что у сериала только один перевод
            log.info('Single translation')
            player_init_script = soup.select('script')[0]

            serial_id = re.search(r'var serialId = Number\((.*?)\);', player_init_script.text)
            if serial_id == None: return None
            serial_id = int(serial_id.group(1))

            serial_hash = re.search(r'var serialHash = "(.*?)";', player_init_script.text)
            if serial_hash == None: return None
            serial_hash = serial_hash.group(1)

            translation_title = re.search(r'var translationTitle = "(.*?)";', player_init_script.text)
            if translation_title == None: return None
            translation_title = translation_title.group(1)

            return [
                Translation(
                    id=serial_id,
                    hash=serial_hash,
                    type='serial',
                    title=translation_title,
                )
            ]

        return [
            Translation(
                id=int(str(option['data-media-id'])),
                hash=str(option['data-media-hash']),
                type=str(option['data-media-type']),
                title=str(option['data-title']),
            )
            for option in options
        ]

    async def request_episodes(self, session: aiohttp.ClientSession, player_data: Optional["PlayerData"]) -> bool:
        self.episodes = await request_translation(session, player_data, self)
        return self.episodes != None


async def request_player_data(session: aiohttp.ClientSession, player_url: Optional[str]) -> Tuple[Optional["PlayerData"], Optional[List["Translation"]]]:
    """
    Запрос данных плеера, необходимых для осуществления дальнейших запросов
    :param session: request.Session с cookies сайта
    :param player_url: ссылка на плеер
    :return: данные плееера и информация о дубляже
    """
    if player_url == None: return (None, None)

    log.info(f'Request player page from "{player_url}"')
    r = await session.get(player_url, params={
        'translations': 'true',
    }, headers={
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'iframe',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Storage-Access': 'active',
        'Referer': 'https://jut-su.net',
    })
    if r.status != 200:
        log.error(f'Can\'t request player data: status code {r.status}')
        return (None, None)
    player_page = Page(player_url, await r.text())

    player_script_url = re.search(r'src="(/assets/js/.*?)"></script>', player_page.body)
    if player_script_url == None:
        log.error(f'Can\'t find player script url')
        return (None, None)

    player_url_parts = urlparse(player_url)
    player_script_url = player_script_url.group(1)
    player_script_url = urlunparse((
        player_url_parts[0],
        player_url_parts[1],
        player_script_url,
        None, None, None
    ))

    log.info(f'Request player script from url "{player_script_url}"...')
    r = await session.get(player_script_url, headers={
        'Referer': player_url,
        'Host': 'kodik.cc',
        'Connection': 'keep-alive',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Storage-Access': 'active',
    })
    if r.status != 200:
        log.error(f'Can\'t request player script: status code {r.status}')
        return (None, None)
    player_script = Page(player_script_url, await r.text())

    player_data = PlayerData.parse(player_page, player_script)
    if player_data == None:
        log.error(f'Can\'t parse data from player page')
        return (None, None)

    print(player_page.body)

    translations = Translation.parse_list(player_page)
    if translations == None:
        log.error(f'Can\'t parse translations from player page')
        return (player_data, None)

    return (player_data, translations)


async def request_translation(session: aiohttp.ClientSession, player_data: Optional["PlayerData"], translation: Optional["Translation"]) -> Optional[List["Episode"]]:
    if player_data == None: return None
    if translation == None: return None

    url = urlunparse((
        'https', player_data.player_domain,
        str(Path('/', translation.type, str(translation.id), translation.hash, '720p')),
        None, None, None
    ))

    log.info(f'Request episodes for translation with id={translation.id}...')
    r = await session.get(url, params={
        **player_data.sign(),
        'first_url': 'false',
    }, headers={
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'iframe',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Storage-Access': 'active',
        'Referer': 'https://jut-su.net',
    })
    if r.status != 200:
        log.error(f'Can\'t request episodes: status code {r.status}')
        return None

    page = Page(url=url, body=await r.text())
    episodes = Episode.parse_list(page)
    if episodes == None: log.error(f'Can\'t parse episodes from player page')
    return episodes


async def request_episode(session: aiohttp.ClientSession, player_data: Optional["PlayerData"], translation: Optional["Translation"], episode: Optional[Episode]) -> Optional[List[Video]]:
    if player_data == None: return None
    if translation == None: return None
    if translation.episodes == None: return None
    if episode == None: return None

    video_types = {
        'serial': 'seria',
        'video': 'video',
    }

    log.info(f'Request episode from {episode.season_name}. index {episode.index}/{len(translation.episodes)} with id={episode.id}...')
    r = await session.post(player_data.endpoint, data={
        **player_data.sign(),
        'type': video_types[translation.type],
        'id': episode.id,
        'hash': episode.hash,
        'info': '{}'
    }, headers={
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Storage-Access': 'active',
        'Referer': player_data.player_url,
        'Host': player_data.player_domain,
        'Origin': urlunparse(('https', player_data.player_domain, '', None, None, None)),
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
    })
    if r.status != 200:
        log.error(f'Can\'t request episode: status code {r.status}')
        return None

    data = await r.json()
    del data['vast']
    del data['reserve_vast']
    del data['ip']
    del data['advert_script']

    assets = []

    for quality, links in data['links'].items():
        url = data['links'][quality][0]['src']
        url = 'https:' + Video.decode_url(url)

        assets.append(Video(
            quality=quality,
            url=url
        ))

    return assets


def get_favourite_translation(translations: Optional[List["Translation"]], top_translations: List[str]) -> Optional["Translation"]:
    if translations == None: return None
    selected_translation = None

    for translation_title in top_translations:
        for translation in translations:
            if translation.title.strip().lower() == translation_title.strip().lower():
                selected_translation = translation
                break
        if selected_translation != None: break

    if selected_translation != None:
        log.info(f'Selected translation "{selected_translation.title}"')
    return selected_translation


def get_favourite_quality(assets: Optional[List["Video"]], top_quality: List[str]) -> Optional["Video"]:
    if assets == None: return None
    selected_video = None

    for quality in top_quality:
        for video in assets:
            if quality.strip().lower() == video.quality.strip().lower():
                selected_video = video
                break
        if selected_video != None: break

    if selected_video != None:
        log.info(f'Selected quality "{selected_video.quality}"')
    return selected_video


@dataclass
class HLS:
    type: str
    duration: int
    segments: List[str]

    @classmethod
    def parse(cls, manifest: "Page") -> "HLS":
        log.info('Parsing hls manifest...')
        lines = list(filter(lambda line: len(line.strip()) > 0,  manifest.body.split('\n')))
        magic = ''
        segments = []
        duration = 0
        type = ''

        manifest_url_parts = urlparse(manifest.url)
        segment_base_url = Path(manifest_url_parts.path.split(':hls:')[0]).parent

        for line in lines:
            if line == '#EXTM3U': magic = line
            elif line == '#EXT-X-ENDLIST': break
            elif line[0] == '#':
                key, value = line.split(':')
                if key == '#EXT-X-TARGETDURATION': duration = int(value)
                elif key == '#EXT-X-PLAYLIST-TYPE': type = value
            else:
                segment_path = str(Path(segment_base_url, line))
                segment_url = urlunparse((
                    manifest_url_parts.scheme,
                    manifest_url_parts.netloc,
                    segment_path,
                    None, None, None,
                ))
                segments.append(segment_url)

        return HLS(type=type, duration=duration, segments=segments)

    async def download(self, session: aiohttp.ClientSession, player_data: Optional["PlayerData"], path: str) -> bool:
        if player_data == None: return False
        if len(self.segments) == 0: return False

        tasks = [
            download_segment(session, index, len(self.segments), url, path)
            for index, url in enumerate(self.segments)
        ]

        results = await asyncio.gather(*tasks)
        return all(results)


async def download_video(session: aiohttp.ClientSession, player_data: Optional["PlayerData"], video: Optional["Video"], path: str) -> bool:
    if player_data == None: return False
    if video == None: return False

    log.info(f'Request hls manifest "{video.url}"')
    r = await session.get(video.url, headers={
        'Accept': '*/*',
        'Connection': 'keep-alive',
        'Origin': 'https://' + player_data.player_domain,
        'Referer': 'https://' + player_data.player_domain + '/',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site'
    })
    if r.status != 200:
        log.error(f"Can't request hls manifest: status code {r.status}")
        return False

    manifest = Page(url=video.url, body=await r.text())
    hls = HLS.parse(manifest)
    return await hls.download(session, player_data, path)


async def download_segment(session: aiohttp.ClientSession, index: int, count: int, url: str, path: str) -> bool:
    log.info(f"Request segment #{index + 1}/{count} with url \"{url}\"...")
    r = await session.get(url, headers={
        'Accept': '*/*',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
    })
    if r.status != 200:
        log.error(f"Can't request segment: status_code {r.status}")
        return False

    try:
        segment_filename = str(Path(path, f'segment-{index}.ts'))
        log.info(f'Saving segment into file "{segment_filename}"...')

        with open(segment_filename, 'wb') as segment_file:
            segment_file.write(await r.content.read())

    except Exception as e:
        log.error(str(e))
        return False

    return True
