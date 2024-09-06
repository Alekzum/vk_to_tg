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


def check_output(*args, **kwargs):
    return run(*args, stdout=PIPE, **kwargs).stdout


def github_sync(directory):
    os.chdir(directory)
    remote_sha = fetch_remove_sha()
    local_sha = fetch_local_sha()
    if remote_sha != local_sha:
        check_output(["git", "pull", "origin", BRANCH])
        print("The local repo has been updated")
        return 1
    else:
        print("The local repo is already up-to-date")
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
    if needUpdate and len(sys.argv) == 1:
        statuscode = github_sync(LOCAL_DIR)
        print(f"{statuscode = }. Restarting the program...")
        try:
            run([sys.executable, "main.py", "-restarted"])
        except KeyboardInterrupt:
            pass
            
        exit(0)


def restarted():
    return len(sys.argv) > 1 and sys.argv[1] == "-restarted"


if __name__ == "__main__":
    check_local_dir()