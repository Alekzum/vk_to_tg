import dotenv


def get_token() -> str:
    maybe_token: str | None = dotenv.get_key(".env", "BOT_TOKEN")
    if maybe_token is not None and maybe_token.strip():
        return maybe_token

    temp_token = input("Need bot's token (https://botfather.t.me): ")
    dotenv.set_key(".env", "BOT_TOKEN", temp_token)
    return temp_token or get_token()


path = dotenv.find_dotenv()
if path == "":
    with open(".env", "w") as f:
        pass
