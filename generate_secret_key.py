# Source - https://stackoverflow.com/a/55147077
# Posted by Martijn Pieters, modified by community. See post 'Timeline' for change history
# Retrieved 2026-04-20, License - CC BY-SA 4.0

from cryptography.fernet import Fernet

key = Fernet.generate_key()  # store in a secure location
# PRINTING FOR DEMO PURPOSES ONLY, don't do this in production code
print("Key:", key.decode())
