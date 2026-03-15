import datetime

from sqlalchemy import String, DateTime, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
import os

db_url = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(db_url)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Token(Base):
    __tablename__ = "token"
    site: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(String)
    updated_at: Mapped[datetime.datetime] = mapped_column(  # when it was last saved
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    def __repr__(self) -> str:
        return f"Token(site={self.site}, value={self.value}, date = {self.updated_at})"

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_token() -> str | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Token).where(Token.site == "google_token")
        )
        row = result.scalar_one_or_none()  # one row or None
        return row.value if row else None

async def save_token(token_json: str):
    async with AsyncSessionLocal() as session:
        stmt = insert(Token).values(
            site="google_token",
            value=token_json,
            updated_at= datetime.datetime.now(datetime.timezone.utc)
        ).on_conflict_do_update(        # if the site already exists...
            index_elements=["site"],     # ...find conflict by this column
            set_={                      # ...update these fields
                "value": token_json,
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
        )
        await session.execute(stmt)
        await session.commit()
