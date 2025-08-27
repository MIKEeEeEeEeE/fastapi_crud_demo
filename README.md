# Инструкция по запуску

Alembic не работает с sqlmodel напрямую, поэтому при первом запуске будет ошибка

  File "/home/admin/Desktop/fastapi_crud_demo/alembic/versions/ff8da24de7c7_create_initial_tables.py", line 24, in upgrade
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
                      ^^^^^^^^
    NameError: name 'sqlmodel' is not defined

Решение: import sqlmodel в начале файла, который выдал ошибку


# Пользователи

1. admin role -> amdin / password ; actions -> GET, POST, PUT, DELETE
2. dev role -> developer / password ; actions -> GET, POST, PUT
3. viewer role -> viewer / password ; actions -> GET