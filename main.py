import os
import json
import time
from src.app.logger.logger import StaticLogger
from src.app.fascades.bingads_fascade import BingadsFascade
from datetime import datetime, timedelta, timezone

def main():
    script_start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Get script path
    script_dir = os.path.dirname(os.path.abspath(__file__))

    logger = StaticLogger(os.path.join(script_dir, "log/app.log"))

    # Required
    with open(os.path.join(script_dir, "env.json"), 'r') as file:
        ENVIRONMENT_INFO = json.load(file)
    env = {
        # Neccessary
        "CLIENT_ID": ENVIRONMENT_INFO["CLIENT_ID"],
        "DEVELOPER_TOKEN": ENVIRONMENT_INFO["DEVELOPER_TOKEN"],
        "ENVIRONMENT": ENVIRONMENT_INFO["ENVIRONMENT"],
        "REFRESH_TOKEN": os.path.join(script_dir, "credentials/refresh.txt"),
        # Optional
        "CLIENT_STATE": int(time.time()),
        }

    bingads_fascade = BingadsFascade(env, logger)
    bingads_fascade.bootstrap()

main()
