#!/data/data/com.termux/files/usr/bin/bash
# Установка на Android (Termux). Запуск:
#   curl -sL https://raw.githubusercontent.com/afibur/olx_fetch/main/insta/setup_termux.sh | bash
set -e
REPO_RAW="https://raw.githubusercontent.com/afibur/olx_fetch/main/insta"

pkg update -y
pkg install -y python ffmpeg termux-api curl
pip install --upgrade gallery-dl yt-dlp

# Доступ к общей памяти телефона (появится запрос разрешения)
[ -d "$HOME/storage/shared" ] || termux-setup-storage

mkdir -p "$HOME/insta" "$HOME/bin"
curl -sL "$REPO_RAW/insta_dl.py" -o "$HOME/insta/insta_dl.py"
curl -sL "$REPO_RAW/termux-url-opener" -o "$HOME/bin/termux-url-opener"
chmod +x "$HOME/insta/insta_dl.py" "$HOME/bin/termux-url-opener"

echo
echo "Готово! Откройте пост в Instagram → Поделиться → Termux."
echo "Файлы сохраняются в Pictures/Instagram."
