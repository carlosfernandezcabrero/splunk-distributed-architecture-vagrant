import json
import sys
import urllib.request
from os import path
from time import sleep
from urllib.error import URLError

MAX_RETRIES = 15
CALL_INTERVAL = 2

cwd = path.dirname(path.abspath(__file__))
f = open(f"{cwd}/../config.json")
master_node_ip = json.load(f)["manager"]["ips"][0]
f.close()


class Checks:
    def web_interface():
        try:
            return (
                urllib.request.urlopen(
                    f"http://{master_node_ip}:8000", timeout=2
                ).getcode()
                == 200
            )
        except URLError:
            return False


checks = [Checks.web_interface]
retries = 0

print("[INFO] Checking if Master is available...")

while True:
    if retries > MAX_RETRIES:
        print("[ERROR] Master is not available. Exiting...")
        sys.exit(1)

    for check in checks:
        if not check():
            print("[ERROR] Master is not available. Retrying...")
            retries += 1
            sleep(CALL_INTERVAL)

            break
    else:
        print("[INFO] Master is available.")
        break
