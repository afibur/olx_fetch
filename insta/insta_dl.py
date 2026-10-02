#!/usr/bin/env python3
"""Скачивание фото и видео из Instagram и TikTok.

Instagram: посты, карусели, reels, stories. TikTok: видео и фото-посты (слайдшоу).

Сначала берёт данные поста через yt-dlp и сам скачивает все фото и видео
(yt-dlp умеет работать без входа, но фото не сохраняет). Если не вышло —
gallery-dl (нужен cookies.txt), затем обычный yt-dlp (только видео).
TikTok: yt-dlp (видео), если не вышло — gallery-dl (фото-посты).

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
URL_RE = re.compile(
    r"https?://(?:[\w-]+\.)?(?:instagram\.com|instagr\.am|tiktok\.com)/\S+", re.I)


def is_tiktok(url: str) -> bool:
    return "tiktok.com" in url.lower()


def default_output_dir() -> Path:
    # В Termux после termux-setup-storage общая память доступна через ~/storage/shared
    termux_shared = Path.home() / "storage" / "shared"
    if termux_shared.exists():
        return termux_shared / "Pictures" / "Instagram"
    # На iPhone (a-Shell, sys.platform == "ios") писать можно только в Documents;
    # Быстрая команда забирает файлы из Documents/Instagram/new
    documents = Path.home() / "Documents"
    if sys.platform in ("ios", "darwin") and documents.exists() \
            and not (Path.home() / "Downloads").exists():
        return documents / "Instagram" / "new"
    return Path.home() / "Downloads" / "Instagram"


def extract_url(text: str) -> str:
    match = URL_RE.search(text)
    if not match:
        sys.exit(f"Не найдена ссылка Instagram или TikTok в: {text!r}")
    # Убираем трекинговые параметры (?igsh=..., ?_t=..., ?utm_source=...)
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


def need(module: str):
    try:
        return __import__(module)
    except ImportError:
        sys.exit(f"Не установлен {module}. Выполните: pip install gallery-dl yt-dlp")


def best(items: list, key: str = "width") -> str | None:
    items = [i for i in items or [] if isinstance(i, dict) and i.get("url")]
    return max(items, key=lambda i: i.get(key) or 0)["url"] if items else None


def media_urls(post: dict) -> list[tuple[str, str]]:
    """[(url, расширение), ...] для всех фото/видео поста (включая карусель)."""
    result = []
    for item in post.get("carousel_media") or [post]:
        video = best(item.get("video_versions"))
        image = best((item.get("image_versions2") or {}).get("candidates"))
        if video:
            result.append((video, "mp4"))
        elif image:
            result.append((image, "jpg"))
    return result


def run_direct(url: str, out: Path, cookies: Path | None) -> bool:
    """yt-dlp получает данные поста, а файлы (в том числе фото) качаем сами."""
    yt_dlp = need("yt_dlp")
    from yt_dlp.extractor.instagram import InstagramIE

    posts = []
    original = InstagramIE._extract_product

    def capture(self, product_info, *args, **kwargs):
        posts.append(product_info[0] if isinstance(product_info, list) else product_info)
        return original(self, product_info, *args, **kwargs)

    params = {"quiet": True, "no_warnings": True, "ignore_no_formats_error": True}
    if cookies:
        params["cookiefile"] = str(cookies)
    InstagramIE._extract_product = capture
    try:
        with yt_dlp.YoutubeDL(params) as ydl:
            try:
                ydl.extract_info(url, download=False, process=False)
            except Exception as e:  # noqa: BLE001 — для фото-постов yt-dlp ругается «нет видео»
                if not posts:
                    print(f"Не удалось получить данные поста: {e}")
                    return False
            if not posts:
                return False
            post = posts[0]
            files = media_urls(post)
            if not files:
                return False
            user = (post.get("user") or {}).get("username") or "instagram"
            code = post.get("code") or url.rstrip("/").rsplit("/", 1)[-1]
            for num, (media_url, ext) in enumerate(files, 1):
                target = out / f"ig_{user}_{code}_{num:02}.{ext}"
                if target.exists():
                    continue
                print(f"  {target.name}")
                with ydl.urlopen(yt_dlp.networking.Request(
                        media_url, headers={"Referer": "https://www.instagram.com/"})) as resp:
                    target.write_bytes(resp.read())
    except Exception as e:  # noqa: BLE001
        print(f"Ошибка при скачивании: {e}")
        return False
    finally:
        InstagramIE._extract_product = original
    return True


def run_gallery_dl(url: str, out: Path, cookies: Path | None) -> bool:
    gallery_dl = need("gallery_dl")
    if is_tiktok(url):
        # audio=false: у фото-постов TikTok есть музыка (mp3), в Фото её не сохранить
        name = ["--filename", "tt_{user|'unknown'}_{id}_{num:>02}.{extension}", "-o", "audio=false"]
    else:
        name = ["--filename", "ig_{username}_{shortcode}_{num:>02}.{extension}"]
    argv = ["--directory", str(out), *name, "--no-mtime"]
    if cookies:
        argv += ["--cookies", str(cookies)]
    argv.append(url)
    return run_module(gallery_dl.main, argv)


def run_yt_dlp(url: str, out: Path, cookies: Path | None) -> bool:
    yt_dlp = need("yt_dlp")
    template = "tt_%(uploader,channel|unknown)s_%(id)s.%(ext)s" if is_tiktok(url) \
        else "ig_%(channel,uploader_id|unknown)s_%(id)s.%(ext)s"
    argv = [
        "-o", str(out / template), "--no-mtime",
        # Один файл, где уже есть и видео, и звук. Иначе yt-dlp склеивает видео
        # с отдельной mp3-дорожкой, а Фото на iPhone такой mp3 внутри mp4 не играет.
        "-f", "b/bv*+ba",
        # Если склейка всё же нужна — перекодировать звук в AAC (его понимает iPhone)
        "--postprocessor-args", "Merger:-c:a aac",
    ]
    if cookies:
        argv += ["--cookies", str(cookies)]
    argv.append(url)
    return run_module(lambda: yt_dlp.main(argv), argv)


def media_scan(files: set[Path]) -> None:
    """Чтобы файлы сразу появились в Галерее Android."""
    scan = shutil.which("termux-media-scan")
    if scan and files:
        subprocess.run([scan, *map(str, files)], stdout=subprocess.DEVNULL)


def fix_argv(argv: list[str]) -> list[str]:
    """Быстрая команда может «приклеить» -o к ссылке: '...?x=1-o' -> ['...?x=1', '-o']."""
    fixed = []
    for arg in argv:
        if URL_RE.match(arg) and arg.endswith("-o") and len(arg) > 2:
            fixed += [arg[:-2], "-o"]
        else:
            fixed.append(arg)
    return fixed


def main() -> None:
    parser = argparse.ArgumentParser(description="Скачать фото/видео из Instagram и TikTok")
    parser.add_argument("url", nargs="*", help="ссылка (или текст со ссылкой)")
    parser.add_argument("-o", "--output", type=Path, default=None, help="папка для сохранения")
    parser.add_argument("--cookies", type=Path, default=None,
                        help="cookies.txt (Netscape) от залогиненного Instagram")
    args = parser.parse_args(fix_argv(sys.argv[1:]))

    if not args.url:
        sys.exit("Ссылка не передана. В Быстрой команде вставьте переменную «URL-адреса» "
                 "сразу после insta_dl.py и запускайте команду через «Поделиться» из Instagram.")
    url = extract_url(" ".join(args.url))
    out = (args.output or default_output_dir()).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    cookies = args.cookies or (DEFAULT_COOKIES if DEFAULT_COOKIES.exists() else None)
    if cookies and not cookies.exists():
        sys.exit(f"Файл cookies не найден: {cookies}")

    print(f"Скачиваю {url}\n -> {out}")
    before = list_files(out)
    if is_tiktok(url):
        # Видео надёжнее качает yt-dlp; фото-посты (слайдшоу) он не умеет — тогда gallery-dl
        ok = run_yt_dlp(url, out, cookies)
        if not ok:
            print("Пробую gallery-dl (фото-пост?)...")
            ok = run_gallery_dl(url, out, cookies)
    else:
        ok = run_direct(url, out, cookies)
        if not ok:
            print("Пробую gallery-dl...")
            ok = run_gallery_dl(url, out, cookies)
    if not ok and not is_tiktok(url):
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
