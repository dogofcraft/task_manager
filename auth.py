import os
from jose import JWTError, jwt
from fastapi import HTTPException
from prometheus_client import Counter, Histogram, Gauge

SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")

task_queue_length = Gauge("task_queue_length", "队列长度")
stage_duration = Histogram("stage_duration_seconds", "阶段耗时")
task_failures = Counter("task_failures_total", "失败任务数")

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")