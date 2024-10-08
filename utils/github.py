# !/usr/bin/env python3

"""
Author: Ming Wen (bitmingw@gmail.com)
This script is used to track the changes in the github, and if a new commit
is found, update the local repository accordingly.
"""

if __name__ == "__main__":
    import config as cfg  # type: ignore[import-not-found]
else:
    from . import config as cfg

Config = cfg.Config

from urllib.request import urlopen
from subprocess import PIPE, run
import json
import os
import sys


# Configurations
USERNAME = "alekzum"
REPO = "vk_to_tg"
BRANCH = "main"
LOCAL_DIR = "."


def log(text: str) -> None:
    import datetime
    print(f"{str(datetime.datetime.now())[:-3]} - utils/github.py - {text}")


def check_output(*args, **kwargs):
    return run(*args, stdout=PIPE, **kwargs).stdout


def github_sync(directory):
    os.chdir(directory)
    remote_sha = fetch_remove_sha()
    local_sha = fetch_local_sha()
    if remote_sha != local_sha:
        check_output(["git", "pull", "origin", BRANCH])
        log("The local repo has been updated")
        return 1
    else:
        log("The local repo is already up-to-date")
        return 0


def fetch_remove_sha():
    repo_path = "/".join(["repos", USERNAME, REPO, "branches", BRANCH])
    req_url = "https://api.github.com/" + repo_path
    resp = urlopen(req_url)
    resp_str = str(resp.read(), encoding="utf-8")
    resp_data = json.loads(resp_str)
    remote_sha = resp_data["commit"]["sha"]
    return remote_sha


def fetch_local_sha():
    check_output(["git", "checkout", BRANCH])
    local_sha = str(check_output(["git", "rev-parse", "HEAD"]), encoding="utf-8")
    return local_sha[:-1]  # remove newline


def check_local_dir():
    needUpdate = Config.need_update
    if needUpdate and "--with-github" not in sys.argv:
        statuscode = github_sync(LOCAL_DIR)
        log(f"{statuscode = }. Restarting the program...")
        run_with_github_tag()
            
        exit(0)


def restarted():
    restarted = "--with-github" in sys.argv
    if not restarted:
        run_with_github_tag()
    return restarted


def run_with_github_tag():
    try:
        run([sys.executable] + sys.argv + ["--with-github"])
    except KeyboardInterrupt:
        exit()


if __name__ == "__main__":
    check_local_dir()