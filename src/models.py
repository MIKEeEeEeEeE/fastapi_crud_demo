from sqlmodel import Field, SQLModel


class Role(SQLModel, table=True):
    name: str = Field(primary_key=True)
    level: int = Field(gt=0)


class User(SQLModel, table=True):
    userid: int = Field(default=None, gt=0, primary_key=True)
    username: str = Field(min_length=1, max_length=32)
    role: str = Field(default=None, foreign_key="role.name")


class Token(SQLModel):
    access_token: str
    token_type: str


class Todo(SQLModel, table=True):
    itemid: int = Field(default=None, gt=0, primary_key=True)
    title: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=0, max_length=256)
    completed: bool = Field(default=False)


class Item(SQLModel):
    title: str
    description: str
