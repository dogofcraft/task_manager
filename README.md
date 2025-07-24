# Task Manager Service

## 运行
1. 激活环境: conda activate task_manager
2. 启动 Celery: celery -A celery_app worker --loglevel=info
3. 启动 API: uvicorn main:app --reload

## 测试
curl -X POST "http://localhost:7862/tasks" -d "service_type=entity_extraction"