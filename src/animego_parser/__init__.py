import argparse
import asyncio
import aiohttp
import sys

from . import misc
from . import profile

async def parse_profile(args):
    if args.format not in {'json', 'xml'}:
        print("animego-parser error: supported formats: json, xml")
        exit(1)

    session = aiohttp.ClientSession()
    session.headers.update(misc.HEADERS)
    await session.get(misc.BASE_URL) # Update cookies

    try:
        anime_list = await profile.parse_list(session,
            profile_url=args.profile_url,
            show_progress_bar=bool(args.output),
        )
        await session.close()

    except profile.ParsingError as e:
        print(e)
        exit(1)

    finally:
        await session.close()

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


async def async_main():
    parser = argparse.ArgumentParser(
        description="Anime list parser. ")

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    parser_profile = subparsers.add_parser("profile", help="parsing anime list from user profile")

    parser_profile.add_argument("--url", type=str,
        help="Anime user list url", dest='profile_url', required=True)
    parser_profile.add_argument("--output", type=str,
        help="Output file name (stdout if not specified)", required=False)
    parser_profile.add_argument("--format", type=str,
        help="Output file format (xml/json, json by default)",
        default="json", required=False)

    args = parser.parse_args()

    if args.subcommand == "profile":
        await parse_profile(args)


def main():
    asyncio.run(async_main())
