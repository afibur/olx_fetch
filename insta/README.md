# Скачивание фото и видео из Instagram на телефон

Скрипт `insta_dl.py` скачивает посты, карусели (все фото/видео), reels и stories.
Внутри — [gallery-dl](https://github.com/mikf/gallery-dl), запасной вариант — [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Android (рекомендуется) — через кнопку «Поделиться»

1. Установите из **F-Droid** (не из Google Play — там устаревшие версии):
   - **Termux**
   - **Termux:API** (чтобы файлы сразу появлялись в Галерее)
2. Откройте Termux и выполните одну команду:
   ```bash
   curl -sL https://raw.githubusercontent.com/afibur/olx_fetch/main/insta/setup_termux.sh | bash
   ```
   Разрешите доступ к файлам, когда спросит.
3. Готово. В Instagram: пост/reel → **Поделиться → (Ещё) → Termux**.
   Файлы сохраняются в `Pictures/Instagram` и видны в Галерее.

Вручную из Termux тоже можно:
```bash
python ~/insta/insta_dl.py https://www.instagram.com/reel/XXXXXXX/
```

## iPhone — через приложение a-Shell

1. Установите **a-Shell** из App Store и выполните в нём:
   ```bash
   pip install gallery-dl yt-dlp
   curl -sL https://raw.githubusercontent.com/afibur/olx_fetch/main/insta/insta_dl.py -o ~/Documents/insta_dl.py
   ```
2. Скачивание: `python ~/Documents/insta_dl.py ССЫЛКА -o ~/Documents/Instagram`
3. Файлы появятся в приложении **Файлы → a-Shell → Instagram**; оттуда «Сохранить в Фото».
4. Удобнее: сделайте Команду (Shortcuts), которая принимает URL из «Поделиться» и
   вызывает действие a-Shell «Execute Command» с той же командой.
   (Видео — без склейки ffmpeg, но для Instagram обычно хватает.)

## Если пишет «login required» / приватный аккаунт / stories

Instagram часто требует вход. Экспортируйте cookies из браузера, где вы залогинены
(расширение «Get cookies.txt LOCALLY» на компьютере), и положите файл как
`~/insta/cookies.txt` (Android) или рядом со скриптом (iPhone).
Скрипт подхватит его автоматически. Никому не передавайте этот файл — это доступ к аккаунту.

## Обновление

Instagram регулярно что-то меняет; если перестало качать:
```bash
pip install --upgrade gallery-dl yt-dlp
```
