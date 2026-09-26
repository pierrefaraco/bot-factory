from sqlalchemy.orm import DeclarativeBase

from ai_server.database.session import SessionLocal


class Base(DeclarativeBase):
    pass


# Model.query compat (Flask-SQLAlchemy style): a sync query bound to the
# current request's scoped session -- see database/session.py.
Base.query = SessionLocal.query_property()
