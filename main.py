import os
import json
from app.logger.logger import StaticLogger
from app.fascades.bingads_fascade import BingadsFascade
from datetime import datetime, timedelta, timezone

def main():
    script_start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Get script path
    script_dir = os.path.dirname(os.path.abspath(__file__))

    logger = StaticLogger()
    logger.setup_logger(os.path.join(script_dir, "log/app.log"))

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
        "CLIENT_STATE": None,
        }

    bingads_adapter = BingadsFascade(env, logger)
    bingads_adapter.bootstrap()

main()
