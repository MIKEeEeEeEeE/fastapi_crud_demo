import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_DRIVER = "asyncpg"
DB_URL = f"postgresql+{DB_DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine: AsyncEngine = create_async_engine(
    DB_URL, pool_size=10, pool_timeout=30, pool_recycle=1800, echo=True
)

session = AsyncSession(engine)
