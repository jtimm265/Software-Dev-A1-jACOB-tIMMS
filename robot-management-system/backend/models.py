from sqlalchemy import Column, Integer, String, DateTime
import datetime
from database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    user_role = Column(String, default="System") 
    command_type = Column(String, index=True)    
    details = Column(String)                     