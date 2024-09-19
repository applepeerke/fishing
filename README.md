# Fishing
## Purpose
My purpose is to build a Python authenticated FastAPI web app, using containerized microservices. 
As an example I use a Fishing simulation.
## Implementation
### Database
The project uses a Postgres database, which is built and migrated via alembic and maintained via asyncpg.
For the models I use SQLAlchemy and pydantic validation.
### Authentication
Authentication (2fa) is done via login with email handshaking and one-time-password. 
An OAuth2 bearer token is used for maintaining the session.
### Testing
Unit- and also automatic testing is done via pytest. A _virtual hacker_ is used to provide some basic input validation.

## Prerequisites
 - Python 3.12
 - Postgres with empty databases `fishing_db` and `fishing_db_test`


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
### Configuration
 - Rename `example.env` to `.env`
 - Adjust the lines marked with ### to you specific situation.
### Start up
 - Run `main.py`
### OpenAPI UI
 - Run `main.py`
 - Head over to http://localhost:8085/api/v1/docs/ for the OpenAPI frontend.
 - Here you can try out the FastAPI endpoints.
 - There is a test endpoint to populate the database with fake data, and to log-in a fake user. This can be convenient for trying out the login system. 
### Unit test
In the terminal of your IDE, run `pytest`.


