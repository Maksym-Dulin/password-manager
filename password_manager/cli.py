"""
Текстовый интерфейс менеджера паролей.
"""

from __future__ import annotations

import getpass
import os

from . import crypto
from .storage import Storage

PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"
STORAGE_FILE = "encrypted_passwords.json"


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def generate_keys() -> None:
    if os.path.exists(PRIVATE_KEY_FILE) or os.path.exists(PUBLIC_KEY_FILE):
        print("Ключи уже существуют. Чтобы создать новые, удалите старые .pem-файлы.")
        return

    passphrase = getpass.getpass("Придумайте пароль-фразу для приватного ключа: ")
    confirm = getpass.getpass("Повторите пароль-фразу: ")
    if passphrase != confirm:
        print("Пароль-фразы не совпадают. Попробуйте снова.")
        return
    if not passphrase:
        print("Пароль-фраза не может быть пустой.")
        return

    print("Генерация пары ключей (может занять пару секунд)...")
    private_pem, public_pem = crypto.generate_key_pair(passphrase)

    with open(PRIVATE_KEY_FILE, "wb") as f:
        f.write(private_pem)
    with open(PUBLIC_KEY_FILE, "wb") as f:
        f.write(public_pem)

    print(f"Приватный ключ сохранён в {PRIVATE_KEY_FILE} (зашифрован пароль-фразой).")
    print(f"Публичный ключ сохранён в {PUBLIC_KEY_FILE}.")
    print("\nВАЖНО: храните приватный ключ и пароль-фразу в безопасности.")
    print("Без них расшифровать сохранённые пароли невозможно.")


def add_password(storage: Storage) -> None:
    if not os.path.exists(PUBLIC_KEY_FILE):
        print("Публичный ключ не найден. Сначала сгенерируйте ключи (пункт 1).")
        return

    service = input("Сервис (например, github): ").strip()
    username = input("Логин / e-mail: ").strip()
    raw_password = getpass.getpass("Пароль: ")
    if not raw_password:
        print("Пустой пароль сохранять нет смысла.")
        return

    public_key = crypto.load_public_key(_read_bytes(PUBLIC_KEY_FILE))
    encrypted_key, token = crypto.encrypt(public_key, raw_password)
    entry = storage.add(service, username, encrypted_key, token)

    print(f"\nПароль для «{service}» сохранён (id: {entry['id'][:8]}).")


def list_passwords(storage: Storage) -> None:
    entries = storage.all()
    if not entries:
        print("Пока нет ни одной сохранённой записи.")
        return

    print("\nСохранённые записи:")
    for e in entries:
        print(f"  [{e['id'][:8]}]  {e['service']:<20} {e['username']}")


def reveal_password(storage: Storage) -> None:
    if not os.path.exists(PRIVATE_KEY_FILE):
        print("Приватный ключ не найден.")
        return
    if not storage.all():
        print("Нет сохранённых записей.")
        return

    list_passwords(storage)
    short_id = input("\nВведите id записи (первые символы): ").strip()

    matches = [e for e in storage.all() if e["id"].startswith(short_id)]
    if not matches:
        print("Запись не найдена.")
        return
    if len(matches) > 1:
        print("Под этот id подходит несколько записей, уточните.")
        return
    entry = matches[0]

    passphrase = getpass.getpass("Пароль-фраза приватного ключа: ")
    try:
        private_key = crypto.load_private_key(_read_bytes(PRIVATE_KEY_FILE), passphrase)
    except (ValueError, TypeError):
        print("Неверная пароль-фраза или повреждённый ключ.")
        return

    try:
        password = crypto.decrypt(private_key, entry["encrypted_key"], entry["token"])
    except Exception:
        print("Не удалось расшифровать запись (повреждённые данные).")
        return

    print(f"\nСервис:  {entry['service']}")
    print(f"Логин:   {entry['username']}")
    print(f"Пароль:  {password}")


def delete_password(storage: Storage) -> None:
    if not storage.all():
        print("Нет сохранённых записей.")
        return

    list_passwords(storage)
    short_id = input("\nВведите id записи для удаления: ").strip()
    matches = [e for e in storage.all() if e["id"].startswith(short_id)]
    if len(matches) != 1:
        print("Нужно указать ровно одну запись.")
        return

    if storage.delete(matches[0]["id"]):
        print("Запись удалена.")


def run() -> None:
    storage = Storage(STORAGE_FILE)
    actions = {
        "1": ("Сгенерировать пару ключей", lambda: generate_keys()),
        "2": ("Добавить и зашифровать пароль", lambda: add_password(storage)),
        "3": ("Показать список записей", lambda: list_passwords(storage)),
        "4": ("Расшифровать пароль", lambda: reveal_password(storage)),
        "5": ("Удалить запись", lambda: delete_password(storage)),
    }

    while True:
        print("\n--- Менеджер паролей ---")
        for key, (label, _) in actions.items():
            print(f"{key}. {label}")
        print("6. Выход")

        choice = input("Выберите действие: ").strip()
        if choice == "6":
            print("Выход.")
            break
        action = actions.get(choice)
        if action:
            action[1]()
        else:
            print("Неверный выбор.")
