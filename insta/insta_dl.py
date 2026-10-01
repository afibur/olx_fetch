#!/usr/bin/env python3
"""Скачивание фото и видео из Instagram (посты, карусели, reels, stories).

Использует gallery-dl (фото + видео, карусели), при неудаче — yt-dlp (видео).

Примеры:
    python insta_dl.py https://www.instagram.com/p/XXXXXXXX/
    python insta_dl.py https://www.instagram.com/reel/XXXXXXXX/ -o ~/storage/dcim/Instagram
    python insta_dl.py URL --cookies cookies.txt   # для приватных аккаунтов и stories
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_COOKIES = SCRIPT_DIR / "cookies.txt"
URL_RE = re.compile(r"https?://(?:www\.)?(?:instagram\.com|instagr\.am)/\S+", re.I)


def default_output_dir() -> Path:
    # В Termux после termux-setup-storage общая память доступна через ~/storage/shared
    termux_shared = Path.home() / "storage" / "shared"
    if termux_shared.exists():
        return termux_shared / "Pictures" / "Instagram"
    # На iPhone (a-Shell) видна в приложении «Файлы» только папка Documents
    if sys.platform == "darwin" and not (Path.home() / "Downloads").exists():
        return Path.home() / "Documents" / "Instagram"
    return Path.home() / "Downloads" / "Instagram"


def extract_url(text: str) -> str:
    match = URL_RE.search(text)
    if not match:
        sys.exit(f"Не найдена ссылка Instagram в: {text!r}")
    # Убираем трекинговые параметры (?igsh=..., ?utm_source=...)
    return match.group(0).split("?")[0]


def list_files(folder: Path) -> set[Path]:
    return {p for p in folder.rglob("*") if p.is_file()}


def run_module(call, argv: list[str]) -> bool:
    """Запуск в том же процессе: на iPhone (a-Shell) вложенный python не работает."""
    old_argv = sys.argv
    sys.argv = ["prog", *argv]
    try:
        code = call()
    except SystemExit as e:
        code = e.code
    except Exception as e:  # noqa: BLE001 — сообщаем и переходим к запасному варианту
        print(f"Ошибка: {e}")
        code = 1
    finally:
        sys.argv = old_argv
    return code in (0, None)


def run_gallery_dl(url: str, out: Path, cookies: Path | None) -> bool:
    import gallery_dl
    argv = [
        "--directory", str(out),
        "--filename", "{username}_{shortcode}_{num:>02}.{extension}",
        "--no-mtime",
    ]
    if cookies:
        argv += ["--cookies", str(cookies)]
    argv.append(url)
    return run_module(gallery_dl.main, argv)


def run_yt_dlp(url: str, out: Path, cookies: Path | None) -> bool:
    import yt_dlp
    argv = ["-o", str(out / "%(uploader_id)s_%(id)s.%(ext)s"), "--no-mtime"]
    if cookies:
        argv += ["--cookies", str(cookies)]
    argv.append(url)
    return run_module(lambda: yt_dlp.main(argv), argv)


def media_scan(files: set[Path]) -> None:
    """Чтобы файлы сразу появились в Галерее Android."""
    scan = shutil.which("termux-media-scan")
    if scan and files:
        subprocess.run([scan, *map(str, files)], stdout=subprocess.DEVNULL)


def main() -> None:
    parser = argparse.ArgumentParser(description="Скачать фото/видео из Instagram")
    parser.add_argument("url", nargs="+", help="ссылка (или текст со ссылкой)")
    parser.add_argument("-o", "--output", type=Path, default=None, help="папка для сохранения")
    parser.add_argument("--cookies", type=Path, default=None,
                        help="cookies.txt (Netscape) от залогиненного Instagram")
    args = parser.parse_args()

    url = extract_url(" ".join(args.url))
    out = (args.output or default_output_dir()).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    cookies = args.cookies or (DEFAULT_COOKIES if DEFAULT_COOKIES.exists() else None)
    if cookies and not cookies.exists():
        sys.exit(f"Файл cookies не найден: {cookies}")

    print(f"Скачиваю {url}\n -> {out}")
    before = list_files(out)
    ok = run_gallery_dl(url, out, cookies)
    if not ok:
        print("gallery-dl не справился, пробую yt-dlp...")
        ok = run_yt_dlp(url, out, cookies)

    new_files = list_files(out) - before
    media_scan(new_files)

    if new_files:
        print(f"\nГотово, сохранено файлов: {len(new_files)}")
        for f in sorted(new_files):
            print("  " + f.name)
    elif ok:
        print("\nФайлы уже были скачаны ранее.")
    else:
        sys.exit("\nНе удалось скачать. Если пост приватный или Instagram просит вход — "
                 "положите cookies.txt рядом со скриптом (см. README).")


if __name__ == "__main__":
    main()
