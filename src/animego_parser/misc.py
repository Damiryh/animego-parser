BASE_URL = "https://animego.me"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36",
}

def progress_bar(x, *, target=100, prefix='', suffix='', length=60, fill='#'):
    x = max(0, min(target, x))
    ratio = x / target if target != 0 else 1

    percent = ratio * 100
    filled = int(ratio * length)
    empty = length - filled
    bar = fill * filled + ' ' * empty

    print(f'\r{prefix} |{bar}| {x}/{target} {percent:0.1f}% {suffix}\r', end='')
    if x >= target: print()
