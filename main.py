from fastapi import FastAPI, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Task
from tasks import process_task
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv
import os
import uuid
import asyncio
import redis

load_dotenv()
redis_client = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=os.getenv('REDIS_DB'))

app = FastAPI()

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/tasks")
def submit_task(service_type: str = Form(...), db: Session = Depends(get_db)):
    task_id = str(uuid.uuid4())
    db_task = Task(id=task_id, service_type=service_type, status='Pending')
    db.add(db_task)
    db.commit()
    process_task.delay(task_id, service_type)  # 触发 Celery
    return {"task_id": task_id}

@app.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    progress = redis_client.get(f'task_progress:{task_id}') or task.progress
    return {"status": task.status, "progress": int(progress)}

@app.get("/tasks/{task_id}/events")
async def task_events(task_id: str):
    async def event_generator():
        prev_progress = 0
        while True:
            progress = redis_client.get(f'task_progress:{task_id}')
            if progress and int(progress) != prev_progress:
                prev_progress = int(progress)
                yield {'data': f'{{"progress": {progress}}}'}
            await asyncio.sleep(1)
    return EventSourceResponse(event_generator())