from celery import Celery
from dotenv import load_dotenv
import os

load_dotenv()
broker_url = os.getenv('CELERY_BROKER_URL')
backend_url = os.getenv('CELERY_RESULT_BACKEND')

app = Celery('task_manager', broker=broker_url, backend=backend_url)
app.conf.update(
    task_track_started=True,
    task_time_limit=3600
)