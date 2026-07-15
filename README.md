🔐 Password Manager

A small command-line password manager written in Python. You type your passwords in,
it saves them encrypted, and later you can get them back.

This is a learning project, I built it to understand how encryption actually works
in practice, not to compete with real password managers.

The idea in one paragraph

Storing passwords in a text file is obviously a bad idea. So this program encrypts
every password before writing it to disk. The only file that can unlock them is your
private key, and the private key itself is locked with a passphrase you choose. If
somebody steals encrypted_passwords.json, they get a pile of unreadable hex.

What it can do


Create a pair of RSA keys, protected by a passphrase
Encrypt a password of any length
Save entries with a service name and a login
List your entries, decrypt one, or delete one
Hide your typing in the terminal (using getpass)


How the encryption works

I use hybrid encryption, which sounds fancy but is just two steps glued together.

RSA can only encrypt very short messages, so encrypting a long password with it
directly doesn't work. The usual trick is:


Make up a brand-new random key (a Fernet key, which is AES under the hood).
Encrypt the password with that random key → this gives a token.
Encrypt the random key itself with your RSA public key → this gives an
encrypted_key.
Save only token and encrypted_key. Throw the random key away.


password ──Fernet(random key)──▶ token
                  │
      random key ──RSA(public key)──▶ encrypted_key

on disk: token + encrypted_key   (the random key is gone)

To read the password back you go the other way: the RSA private key decrypts
encrypted_key to recover the random key, and the random key decrypts token.

Why bother with two keys? Because RSA is asymmetric: the public key can only lock,
not unlock. So the program can save new passwords without ever asking for your
passphrase — you only need it when you actually want to read something back.

Project structure

password-manager/
├── main.py                     # start here
├── password_manager/
│   ├── crypto.py               # all the encryption
│   ├── storage.py              # reading/writing the JSON file
│   └── cli.py                  # the menu you see in the terminal
├── requirements.txt
├── .gitignore
└── README.md

What each file does

main.py — the entry point. It does one thing: import run() from the CLI and
call it. Kept tiny on purpose, so all the real logic lives in the package.

password_manager/crypto.py — the encryption engine. It knows nothing about
menus or files; it just takes strings and keys and gives back other strings. Four
things live here:


generate_key_pair(passphrase) — makes the RSA key pair and locks the private
half with your passphrase
load_public_key() / load_private_key() — read keys back from PEM files
encrypt(public_key, text) — the hybrid encryption described above, returns
(encrypted_key, token) as hex strings
decrypt(private_key, encrypted_key, token) — the reverse


password_manager/storage.py — the database, except it's just a JSON file. The
Storage class loads the file on startup and saves it after every change. Each
entry looks like this:

json{
  "id": "8f3c...",
  "service": "gmail",
  "username": "user@gmail.com",
  "encrypted_key": "ab12...",
  "token": "cd34...",
  "created_at": "2026-07-14T10:00:00+00:00"
}

Methods: add(), all(), find(), delete(). Storage never sees a plain
password — the CLI encrypts it first.

password_manager/cli.py — everything the user touches. It prints the menu,
asks questions, and wires the other two modules together: get input → call
crypto → hand the result to storage. It also holds the filenames
(private_key.pem, public_key.pem, encrypted_passwords.json).

The point of splitting it this way: crypto.py and storage.py don't import each
other and don't call print() or input(). Only cli.py does. So if I ever want a
web version, I throw away cli.py and keep the rest.

Install

You need Python 3.9 or newer.

bashgit clone https://github.com/<your-username>/password-manager.git
cd password-manager

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

Run

bashpython main.py

You'll see:

--- Password Manager ---
1. Generate key pair
2. Add and encrypt a password
3. List entries
4. Decrypt a password
5. Delete an entry
6. Exit

First time through


Option 1 — generate your keys and pick a passphrase. Do this once.
Option 2 — add a password: service, login, password.
Option 3 — see your entries and their ids.
Option 4 — type an id and your passphrase to reveal a password.
Option 5 — delete an entry you don't need.


Run the program from the same folder every time — the key files and the JSON are
looked up relative to your current directory.

⚠️ Read this before trusting it with anything


Never commit private_key.pem or encrypted_passwords.json. They're already
in .gitignore. The JSON has no plaintext passwords in it, but it does show which
services you use and under which logins — that alone is worth keeping private.
Lose the private key or the passphrase and your passwords are gone forever.
There is no recovery. Back the key up somewhere safe.
Pick a long passphrase. A short one can be brute-forced offline by anyone who
copies your .pem file. Use a sentence, not a word.
The revealed password gets printed straight to your terminal, so it stays in your
scrollback. Clear it when you're done.
This is a learning project. For passwords you actually care about, use
something audited: Bitwarden, KeePassXC, or 1Password.
