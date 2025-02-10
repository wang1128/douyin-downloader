from sqlalchemy import create_engine, Column, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path

Base = declarative_base()

class DownloadRecord(Base):
    """下载记录模型"""
    __tablename__ = 'download_records'
    
    id = Column(String, primary_key=True)
    url = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    download_time = Column(DateTime, default=datetime.now)
    status = Column(String)
    metadata = Column(JSON)

class Database:
    def __init__(self, db_path: Path = Path("data/downloads.db")):
        db_path.parent.mkdir(exist_ok=True)
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    def add_record(self, url: str, file_path: str, status: str, metadata: dict = None):
        with self.Session() as session:
            record = DownloadRecord(
                url=url,
                file_path=file_path,
                status=status,
                metadata=metadata
            )
            session.add(record)
            session.commit() 