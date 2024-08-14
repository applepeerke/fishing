# Python-microservice-FastAPI
## Purpose
Learn to build a containerized microservice using Python and FastAPI.
## Implementation
The project uses a Postgres database, which is migrated via alembic and maintained via asyncpg.

For ORM modeling SQLAlchemy is used, combined with pydantic validation.
Unit testing is done via pytest.

## Prerequisites
 - Python 3.12
 - Postgres with empty databases `fishing_db_dev` and `fishing_db_dev_test`


## Getting started
### Virtual environment
Create a virtual environment. Make sure the requirements listed in `requirements.txt` are installed.
### Alembic
```
alembic init -t async migrations
```
This gives you a directory in the root of the project folder as follows:
```
project-root
    migrations
        versions
```
The `versions `folder is mandatory, and should be created if it does not exist.
```
alembic upgrade head
```
The tables should now have been created in your postgres database.
### Swagger UI
 - Run `main.py`
 - Head over to http://localhost:8085/api/v1/docs/ for the swagger docs.
 - Here you may try out the CRUD API's.
### Unit test
In the terminal of your IDE, run `pytest`.


