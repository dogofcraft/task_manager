from sqlalchemy import Column, Integer, String, Enum, Text, TIMESTAMP, func, DateTime, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    task_id = Column(String, primary_key=True)
    user_id = Column(String)
    status = Column(String)  # 总状态
    current_stage = Column(String)  # 当前阶段
    percent = Column(Float)  # 总进度
    stages = Column(JSON)  # 各阶段进度
    eta_seconds = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)