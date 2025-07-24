from celery_app import app
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
        # 更新状态为 Running
        db.query(Task).filter(Task.id == task_id).update({'status': 'Running', 'progress': 0})
        db.commit()

        # 模拟任务步骤（集成您的实体抽取服务）
        steps = 5  # 假设5个步骤
        for i in range(steps):
            time.sleep(2)  # 模拟耗时
            progress = int((i + 1) / steps * 100)
            redis_client.set(f'task_progress:{task_id}', progress)
            db.query(Task).filter(Task.id == task_id).update({'progress': progress})
            db.commit()
            self.update_state(state='PROGRESS', meta={'progress': progress})

        # 完成
        db.query(Task).filter(Task.id == task_id).update({'status': 'Success', 'progress': 100})
        db.commit()
    except Exception as e:
        db.query(Task).filter(Task.id == task_id).update({'status': 'Failed', 'last_error': str(e)})
        db.commit()
        raise
    finally:
        db.close()