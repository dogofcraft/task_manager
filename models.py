from sqlalchemy import Column, Integer, String, Enum, Text, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String, primary_key=True)
    service_type = Column(String, nullable=False)
    status = Column(Enum('Pending', 'Running', 'Success', 'Failed', name='task_status'))
    progress = Column(Integer, default=0)
    priority = Column(Integer, default=0)
    retries = Column(Integer, default=0)
    last_error = Column(Text)
    # created_at = Column(TIMESTAMP, server_default=func.now())
    # updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())    
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)