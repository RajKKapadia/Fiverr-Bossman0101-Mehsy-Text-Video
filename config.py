import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

MESHY_API_KEY = os.getenv("MESHY_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
