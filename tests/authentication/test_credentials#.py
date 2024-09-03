from src.domains.user.functions import map_user
from src.domains.user.models import User, UserStatus
from src.utils.db import crud
from src.utils.db.db import get_db_session
from src.utils.functions import get_otp_expiration
from src.utils.security.crypto import get_salted_hash


class TestCredentials:
    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    def __init__(self, username, password):
        self._username = username
        self._password = password


async def get_test_credentials(pk='user@example.com', initialize=False):
    db = get_db_session()
    user_old = await crud.get_one_where(db, User, att_name=User.email, att_value=pk)
    # a. Delete user (if target is NR)
    if user_old and initialize:
        await crud.delete(db, User, user_old.id)
    # b. Set attributes
    # - Password
    password = 'Password1!'
    password = get_salted_hash(password)
    user = User(email=pk, password=password, expired=get_otp_expiration(),
                fail_count=0, status=UserStatus.Active)
    if user_old:
        # c. Update user
        user.id = user_old.id
        user = await crud.upd(db, User, user_old.id, map_user(user))

    else:
        # d. Add user
        user = await crud.add(db, user)

    return TestCredentials(
        username=user.email,
        password=password  # un-hashed
    )
