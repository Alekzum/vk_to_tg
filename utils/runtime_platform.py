import subprocess, logging, venv, sys, os


logger = logging.getLogger(__name__)
VENV_DIR = ".venv"

# i know only about two paths xd
if sys.platform == "linux":
    VENV = [VENV_DIR, "bin"]
    _PYTHON = ["python"]

else:
    VENV = [VENV_DIR, "Scripts"]
    _PYTHON = ["python.exe"]


PYTHON = VENV + _PYTHON
PATH_TO_PYTHON = os.sep.join(PYTHON)


def in_venv():
    print(f"{sys.prefix=!r}, {sys.base_prefix=!r}")
    inVenv = sys.prefix != sys.base_prefix or '--in-venv' in sys.argv
    return inVenv


def check_platform():
    # if venv not exists then create it
    if not os.path.isfile(PATH_TO_PYTHON):
        print(f"Creating {VENV_DIR}...")
        venv.create(VENV_DIR, with_pip=True)
        install_packages()
        start_venv()
    
    elif not in_venv():
        start_venv()


def install_packages():
    custom_requirements = "requirements.txt"
    command = [PATH_TO_PYTHON, "-m", "pip", "install", "-r", custom_requirements]
    print(f"Starting install packages from {custom_requirements!r}")

    p = subprocess.Popen(command)
    returncode = p.wait()
    if returncode != 0:
        logger.error("idk what happened. write to me, maybe i can do something: https://a1ekzfame.t.me")
        exit(returncode)
    print("Packages installed")
    return


def start_venv():
    command = [PATH_TO_PYTHON, "main.py", '--in-venv']
    print(f"Starting main.py with {PATH_TO_PYTHON!r}")
    p = subprocess.Popen(command)
    try:
        returncode = p.wait()
        exit(returncode)
    except KeyboardInterrupt:
        print("Bot is stopped")


# check_platform()
