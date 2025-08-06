from celery_app import app
from config import *
from database import SessionLocal
from models import Task
from dotenv import load_dotenv
import os
import time  # 用于模拟长任务

load_dotenv()
redis_host = os.getenv('REDIS_HOST')
redis_port = os.getenv('REDIS_PORT')
redis_db = os.getenv('REDIS_DB')
import redis
redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

@app.task(bind=True)
def process_task(self, task_id: str, service_type: str):
    db = SessionLocal()
    try:
        stage_progress = {}
        for idx, stage in enumerate(TASK_STAGES):
            db.query(Task).filter(Task.task_id == task_id).update({
                'current_stage': stage,
                'status': 'Running',
                'percent': int((idx + 1) / len(TASK_STAGES) * 100)
            })
            stage_progress[stage] = int((idx + 1) / len(TASK_STAGES) * 100)
            db.query(Task).filter(Task.task_id == task_id).update({'stages': stage_progress})
            db.commit()
            redis_client.set(f'task_progress:{task_id}', stage_progress[stage])
            self.update_state(state='PROGRESS', meta={'stage': stage, 'progress': stage_progress[stage]})
            time.sleep(2)  # 模拟耗时
        db.query(Task).filter(Task.task_id == task_id).update({'status': 'Success', 'percent': 100, 'current_stage': 'completed'})
        db.commit()
    except Exception as e:
        db.query(Task).filter(Task.task_id == task_id).update({'status': 'Failed', 'last_error': str(e)})
        db.commit()
        raise
    finally:
        db.close()

def get_task(task_id: str, user_id: str):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.task_id == task_id, Task.user_id == user_id).first()
        if not task:
            raise Exception("Task not found or no permission.")
        return task
    finally:
        db.close()

def save_task(task):
    db = SessionLocal()
    try:
        db.merge(task)
        db.commit()
    finally:
        db.close()

def retry_task_by_id(task_id: str, user_id: str):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.task_id == task_id, Task.user_id == user_id).first()
        if not task:
            raise Exception("Task not found or no permission.")
        if task.status.lower() == "failed":
            task.status = "queued"
            task.current_stage = "queued"
            task.percent = 0
            task.stages = {stage: 0 for stage in [
                "uploaded", "queued", "parsing", "ocr", "entity_extract", "entity_review",
                "processing", "qa", "assembling", "packaging", "completed", "failed"
            ]}
            task.eta_seconds = None
            db.commit()
            # 重新入队逻辑（如调用 Celery）
            process_task.delay(task.task_id, "default")
        else:
            raise Exception("Only failed tasks can be retried.")
    finally:
        db.close()

def get_task_by_id(task_id: str):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise Exception("Task not found.")
        return task
    finally:
        db.close()

def get_task_progress_snapshot(task_id: str):
    task = get_task_by_id(task_id)
    return {
        "task_id": task.task_id,
        "status": task.status,
        "percent": task.percent,
        "stages": task.stages,
        "eta_seconds": task.eta_seconds
    }
def cancel_task_by_id(task_id: str, user_id: str):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.task_id == task_id, Task.user_id == user_id).first()
        if not task:
            raise Exception("Task not found or no permission.")
        if task.status.lower() in ["running", "queued"]:
            task.status = "Cancelled"
            db.commit()
            # 取消逻辑（如调用 Celery 任务取消）
        else:
            raise Exception("Only running or queued tasks can be cancelled.")
    finally:
        db.close()