import datetime
import hashlib
import os
import socket
from contextlib import asynccontextmanager
from functools import partial, wraps
from typing import Callable

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from returns.future import FutureResult, future_safe
from returns.pipeline import is_successful
from returns.result import safe

from db import engine, session
from models import Item, Role, Todo, Token, User

hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

viewer_role = Role(name="viewer", level=0)
developer_role = Role(name="developer", level=1)
admin_role = Role(name="admin", level=2)

roleDict = {
    "viewer": viewer_role,
    "developer": developer_role,
    "admin": admin_role,
}

UserDB = [
    {"userid": 1, "username": "admin", "hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8", "role": "admin"},
    {"userid": 2, "username": "developer", "hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8", "role": "developer"},
    {"userid": 3, "username": "viewer", "hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8", "role": "viewer"}
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return User( userid=payload.get("id"),
                     username=payload.get("sub"), 
                     role=payload.get("role"), )
    except jwt.ExpiredSignatureError:
        raise HTTPException( status_code=status.HTTP_401_UNAUTHORIZED,
                             detail="Token has expired",
                             headers={"WWW-Authenticate": "Bearer"}, )
    except jwt.InvalidTokenError:
        raise HTTPException( status_code=status.HTTP_401_UNAUTHORIZED,
                             detail="Invalid token",
                             headers={"WWW-Authenticate": "Bearer"}, )
    except Exception as e:
        raise HTTPException( status_code=status.HTTP_401_UNAUTHORIZED,
                             detail=f"Could not validate credentials: {e}",
                             headers={"WWW-Authenticate": "Bearer"}, )

def role_security(requiredRole: Role = viewer_role, user: User = Depends(get_current_user)) -> User:
    userrole = roleDict.get(user.role)
    if userrole.level < requiredRole.level:
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN,
                             detail="Not authorized!",
                             headers={"WWW-Authenticate": "Bearer"}, )
    return user

@app.post(path="/token")
async def login(creds: OAuth2PasswordRequestForm = Depends()) -> Token:
    for user in UserDB:
        if user.get("username") == creds.username and \
            user.get("hash") == hashlib.sha256(creds.password.encode()).hexdigest():
            payload = {
                "iss": f"{hostname} {IPAddr}", 
                "id": user.get("userid"), 
                "sub": user.get("username"), 
                "role": user.get("role"),
                "exp": datetime.datetime.now() + datetime.timedelta(minutes=30), }
            access_token = jwt.encode(payload=payload, key=SECRET_KEY, algorithm=ALGORITHM)
            return Token(access_token=access_token, token_type="bearer")
    raise HTTPException( status_code=status.HTTP_401_UNAUTHORIZED, 
                         detail="Authentication failed", 
                         headers={"WWW-Authenticate": "Bearer"}, )

@app.get(path="/users/me")
async def about_me(user: User = Depends(partial(role_security, requiredRole=viewer_role))) -> dict:
    return {"Message": f"Hi, {user}!"}

@app.get(path="/admin")
async def admin(user: User = Depends(partial(role_security, requiredRole=admin_role))) -> dict:
    return {"Message": f"Hi, admin {user.username}!"}

# -------------------------------------------------------------------------------------------------------------------------------------------- #

def side_effect(self: FutureResult, func: Callable[[], None], /, *args_to_side_func, **kwargs_to_side_func):
    async def inner():
        result_self = await self
        if not is_successful(result_self):
            return result_self
        result_side_effect = safe(func)(*args_to_side_func, **kwargs_to_side_func)
        if not is_successful(result_side_effect):
            return result_side_effect
        return result_self._inner_value
    return FutureResult(inner())

def async_side_effect(self: FutureResult, func: Callable[[], None], /, *args_to_side_func, **kwargs_to_side_func):
    async def inner():
        result_self = await self
        if not is_successful(result_self):
            return result_self
        result_side_effect = await future_safe(func)(*args_to_side_func, **kwargs_to_side_func)
        if not is_successful(result_side_effect):
            return result_side_effect
        return result_self._inner_value
    return FutureResult(inner())

def bind_side_effect(self: FutureResult, func: Callable[[], None], /, *args_to_side_func, **kwargs_to_side_func):
    async def inner():
        result_side_effect = await self.bind_result(lambda value: safe(func)(value, *args_to_side_func, **kwargs_to_side_func))
        if not is_successful(result_side_effect):
            return result_side_effect._inner_value
        result = await self
        return result._inner_value
    return FutureResult(inner())

def bind_async_side_effect(self: FutureResult, func: Callable[[], None], /, *args_to_side_func, **kwargs_to_side_func):
    async def inner():
        result_side_effect = await self.bind(lambda value: future_safe(func)(value, *args_to_side_func, **kwargs_to_side_func))
        if not is_successful(result_side_effect):
            return result_side_effect._inner_value
        result = await self
        return result._inner_value     
    return FutureResult(inner())

def assert_not_none(self: FutureResult, error):
    def _check(v):
        if v is None:
            raise error
    return self.bind_side_effect(_check)

def return_message(self: FutureResult, msg: dict):
    return self.bind(lambda _: FutureResult.from_value(msg))


FutureResult.side_effect = side_effect
FutureResult.async_side_effect = async_side_effect
FutureResult.bind_side_effect = bind_side_effect
FutureResult.bind_async_side_effect = bind_async_side_effect 
FutureResult.assert_not_none = assert_not_none
FutureResult.return_message = return_message

def ResultWrapper(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        if not is_successful(result):
            error = result.failure()._inner_value
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error))
        return result.unwrap()._inner_value
    return wrapper

# -------------------------------------------------------------------------------------------------------------------------------------------- #

@app.get("/todo/{id}", dependencies=[Depends(partial(role_security, requiredRole=viewer_role))])
@ResultWrapper
async def todo_get(itemid: int):
    async with session:
        return await future_safe(session.get)(entity=Todo, ident=itemid) \
            .assert_not_none(HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found!"))

@app.post(path="/todo", dependencies = [Depends(partial(role_security, requiredRole=developer_role))])
@ResultWrapper
async def todo_post(item: Item):
    async with session:
        todo = Todo(title=item.title, description=item.description)
        return await FutureResult.from_value(todo) \
            .bind_side_effect(session.add) \
            .async_side_effect(session.commit) \
            .bind_async_side_effect(session.refresh)
    
@app.put(path="/todo", dependencies = [Depends(partial(role_security, requiredRole=developer_role))])
@ResultWrapper
async def todo_put(todo: Todo):
    async with session:
        return await future_safe(session.get)(entity=Todo, ident=todo.itemid) \
            .assert_not_none(HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found!")) \
            .bind_side_effect(lambda x: x.sqlmodel_update(todo.model_dump(exclude_unset=True))) \
            .bind_side_effect(session.add) \
            .async_side_effect(session.commit) \
            .bind_async_side_effect(session.refresh)

@app.delete(path="/todo", dependencies = [Depends(partial(role_security, requiredRole=admin_role))])
@ResultWrapper
async def todo_delete(todo_id: int):
    async with session:
        return await future_safe(session.get)(entity=Todo, ident=todo_id) \
            .assert_not_none(HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found!")) \
            .bind_async_side_effect(session.delete) \
            .async_side_effect(session.commit) \
            .return_message({"Message": "Successfully Deleted"})
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)