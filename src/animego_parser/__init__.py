import argparse
import asyncio
import aiohttp
import sys

from . import profile
from . import video

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36",
}

async def parse_profile(args):
    if args.format not in {'json', 'xml'}:
        print("animego-parser error: supported formats: json, xml")
        exit(1)

    BASE_URL = "https://animego.me"

    session = aiohttp.ClientSession()
    session.headers.update(HEADERS)
    await session.get(BASE_URL) # Update cookies

    anime_list = await profile.parse_list(session, args.username)
    await session.close()
    if anime_list == None: exit(1)

    if args.format == "json":
        data = profile.generate_json(anime_list, indent=4)
    elif args.format == "xml":
        data = profile.generate_xml(anime_list, indent=4)
    else:
        data = profile.generate_json(anime_list, indent=4)

    if args.output:
        with open(args.output, 'w', encoding="utf-8") as file:
            file.write(data)
    else:
        sys.stdout.write(data)


async def parse_video(args):
    session = aiohttp.ClientSession()
    session.headers.update(HEADERS)

    URL = "https://animego.me/anime/semya-shpiona-3-2868"
    player_url = await video.adapters.request_player_url(session, URL)
    player_data, translations = await video.kodik.request_player_data(session, player_url)
    #print(player_data)

    await session.close()


async def async_main():
    parser = argparse.ArgumentParser(
        description="Anime list parser. ")

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    parser_profile = subparsers.add_parser("profile", help="parsing anime list from user profile")

    parser_profile.add_argument("--username", type=str,
        help="Anime list owner username", required=True)
    parser_profile.add_argument("--output", type=str,
        help="Output file name (stdout if not specified)", required=False)
    parser_profile.add_argument("--format", type=str,
        help="Output file format (xml/json, json by default)",
        default="json", required=False)

    parser_video = subparsers.add_parser("video", help="parsing video assets from given page")

    parser_video.add_argument("--url", type=str,
        help="URL of anime page", required=True)

    args = parser.parse_args()

    if args.subcommand == "profile":
        await parse_profile(args)
    elif args.subcommand == "video":
        await parse_video(args)


def main():
    asyncio.run(async_main())
