from fastapi import FastAPI, Depends, HTTPException, Form, UploadFile, File, WebSocket
from fastapi import Response
from prometheus_client import generate_latest
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Task
from tasks import *
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv
import os
import uuid
import asyncio
import redis
from auth import *
load_dotenv()
redis_client = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=os.getenv('REDIS_DB'))

app = FastAPI()

Base.metadata.create_all(bind=engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/tasks")
def submit_task(service_type: str = Form(...), db: Session = Depends(get_db)):
    # 提交单个任务，生成唯一 task_id，入库并异步触发 Celery 任务
    task_id = str(uuid.uuid4())
    db_task = Task(id=task_id, service_type=service_type, status='Pending')
    db.add(db_task)
    db.commit()
    process_task.delay(task_id, service_type)  # 触发 Celery
    return {"task_id": task_id}

@app.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    # 查询单个任务进度（优先 Redis，回退数据库），返回任务状态和进度百分比
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    progress = redis_client.get(f'task_progress:{task_id}') or task.progress
    return {"status": task.status, "progress": int(progress)}

@app.get("/tasks/{task_id}/events")
async def task_events(task_id: str):
    # SSE 实时推送任务进度，前端可订阅进度变化
    async def event_generator():
        prev_progress = 0
        while True:
            progress = redis_client.get(f'task_progress:{task_id}')
            if progress and int(progress) != prev_progress:
                prev_progress = int(progress)
                yield {'data': f'{{"progress": {progress}}}'}
            await asyncio.sleep(1)
    return EventSourceResponse(event_generator())

@app.post("/api/v1/tasks")
async def register_tasks(files: list[UploadFile] = File(...), token: str = Depends(oauth2_scheme)):
    # 批量注册任务，支持文件上传，校验用户权限，返回所有 task_id
    user = verify_token(token)
    task_ids = []
    for file in files:
        # 保存文件、注册任务
        task_id = asyncio.create_task(file, user)
        task_ids.append(task_id)
    return {"task_ids": task_ids}

@app.get("/api/v1/tasks/{task_id}")
async def get_task_progress(task_id: str, token: str = Depends(oauth2_scheme)):
    # 查询任务详细进度，返回阶段进度、总进度、ETA 等
    user = verify_token(token)
    task = get_task(task_id, user)
    return {
        "task_id": task.task_id,
        "status": task.status,
        "percent": task.percent,
        "stages": task.stages,
        "eta_seconds": task.eta_seconds
    }

@app.websocket("/ws/progress/{task_id}")
async def ws_progress(websocket: WebSocket, task_id: str):
    # WebSocket 实时推送任务进度，前端可订阅
    await websocket.accept()
    while True:
        progress = get_task_progress_snapshot(task_id)
        await websocket.send_json(progress)
        await asyncio.sleep(1)

@app.post("/api/v1/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, token: str = Depends(oauth2_scheme)):
    # 取消任务，校验权限，仅允许取消运行中或排队中的任务
    user = verify_token(token)
    cancel_task_by_id(task_id, user)
    return {"status": "cancelled"}

@app.post("/api/v1/tasks/{task_id}/retry")
async def retry_task(task_id: str, token: str = Depends(oauth2_scheme)):
    # 重试失败任务，校验权限，仅允许重试失败状态的任务
    user = verify_token(token)
    retry_task_by_id(task_id, user)
    return {"status": "retried"}

@app.get("/metrics")
def metrics():
    # Prometheus 监控指标接口，暴露给监控系统采集
    return Response(generate_latest(), media_type="text/plain")
