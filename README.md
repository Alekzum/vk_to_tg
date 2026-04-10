# Forward messages from vk.com to t.me

## how to run it?
- I'm using python 3.13.7 with win11
- Make environment - I use `python -m venv .venv`
- Enter into environment - `.venv\scripts\activate`
- Download packages - `python -m pip -r requirements.txt`
- Copy `.env.example` to `.env` - On win11 via powershell `copy .env.example .env`
- Edit `.env` with your values:
  - `API_ID`/`API_HASH` - Get from https://my.telegram.org/apps
  - `BOT_TOKEN` - Get from https://t.me/botfather
  - `OWNER_ID` - user with this telegram ID can use /dev commands (have fun with it :P)


---
it's still WIP, but it's some kind of "release" beta - I'm working on it, but I think it's will not raise errors at other users' OS xD
