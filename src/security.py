from dataclasses import dataclass


@dataclass
class UserContext:
    user_id: str


ADMIN_USER = UserContext(user_id="admin")
