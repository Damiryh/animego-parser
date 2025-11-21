from setuptools import setup

setup(
    name="animego-parser",
    version="1.1.0",
    description="Anime list parser for animego.org",
    url="https://github.com/damiryh/animego-parser",
    author="damiryh",
    author_email="damir.alimbekov.2002@gmail.com",
    license="MIT",
    packages=["animego_parser"],
    install_requires=[
        "beautifulsoup4>=4.14.2",
        "aiohttp>=3.13.2",
        "asyncio>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "animego-parser = animego_parser.__main__:main",
        ],
    },
    zip_safe=False)
