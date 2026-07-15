"""
Криптографическое ядро менеджера паролей.

Схема работы (гибридное шифрование):
    1. Для каждого пароля генерируется случайный симметричный ключ Fernet (AES-128 в CBC + HMAC).
    2. Пароль шифруется этим ключом Fernet -> получаем token.
    3. Сам ключ Fernet шифруется публичным RSA-ключом (OAEP/SHA-256) -> получаем encrypted_key.
    4. На хранение уходит пара (encrypted_key, token). Длина исходного пароля не ограничена.

Расшифровка идёт в обратном порядке: приватным RSA-ключом достаём ключ Fernet,
им расшифровываем token обратно в пароль.
"""

from __future__ import annotations

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import (
    RSAPrivateKey,
    RSAPublicKey,
)

# Паддинг OAEP используется одинаковый и при шифровании, и при расшифровке.
_OAEP = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)


def generate_key_pair(passphrase: str, key_size: int = 2048) -> tuple[bytes, bytes]:
    """
    Создаёт пару RSA-ключей.

    Возвращает кортеж (private_pem, public_pem) в виде байтов.
    Приватный ключ зашифрован переданной пароль-фразой.
    """
    if not passphrase:
        raise ValueError("Пароль-фраза не может быть пустой.")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(
            passphrase.encode("utf-8")
        ),
    )

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_pem, public_pem


def load_public_key(pem_bytes: bytes) -> RSAPublicKey:
    """Загружает публичный ключ из PEM-байтов."""
    return serialization.load_pem_public_key(pem_bytes, backend=default_backend())


def load_private_key(pem_bytes: bytes, passphrase: str) -> RSAPrivateKey:
    """
    Загружает приватный ключ из PEM-байтов, расшифровывая его пароль-фразой.

    Бросает ValueError, если фраза неверна (cryptography сама поднимает исключение).
    """
    return serialization.load_pem_private_key(
        pem_bytes,
        password=passphrase.encode("utf-8"),
        backend=default_backend(),
    )


def encrypt(public_key: RSAPublicKey, plaintext: str) -> tuple[str, str]:
    """
    Гибридно шифрует строку.

    Возвращает (encrypted_key_hex, token_hex):
        encrypted_key_hex — ключ Fernet, зашифрованный RSA-ключом (hex);
        token_hex         — сам пароль, зашифрованный Fernet (hex).
    """
    fernet_key = Fernet.generate_key()          # 32 байта в base64-формате
    token = Fernet(fernet_key).encrypt(plaintext.encode("utf-8"))

    encrypted_key = public_key.encrypt(fernet_key, _OAEP)

    return encrypted_key.hex(), token.hex()


def decrypt(private_key: RSAPrivateKey, encrypted_key_hex: str, token_hex: str) -> str:
    """
    Расшифровывает пару (encrypted_key_hex, token_hex) обратно в строку.
    """
    encrypted_key = bytes.fromhex(encrypted_key_hex)
    token = bytes.fromhex(token_hex)

    fernet_key = private_key.decrypt(encrypted_key, _OAEP)
    plaintext = Fernet(fernet_key).decrypt(token)

    return plaintext.decode("utf-8")
