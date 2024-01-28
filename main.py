import os
import json
import time

import src.app.utils.utils as utils

from src.app.logger.logger import StaticLogger
from src.app.fascades.bingads_fascade import BingadsFascade
from datetime import datetime, timedelta, timezone

def main():
    script_start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Get script path
    script_dir = os.path.dirname(os.path.abspath(__file__))

    logger = StaticLogger(utils.resolve_sys_path("log/app.log"))

    # Required
    with open(utils.resolve_sys_path("env.json"), 'r') as file:
        ENVIRONMENT_INFO = json.load(file)
    env = {
        # Neccessary
        "CLIENT_ID": ENVIRONMENT_INFO["CLIENT_ID"],
        "DEVELOPER_TOKEN": ENVIRONMENT_INFO["DEVELOPER_TOKEN"],
        "ENVIRONMENT": ENVIRONMENT_INFO["ENVIRONMENT"],
        "REFRESH_TOKEN": utils.resolve_sys_path("credentials/refresh.txt"),
        "VERSION": 13,
        # Optional
        "CLIENT_STATE": int(time.time()),
        }

    bingads_fascade = BingadsFascade(env, logger)
    bingads_fascade.bootstrap()

main()
