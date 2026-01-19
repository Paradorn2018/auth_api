from app.db.base_class import Base

# IMPORTANT: import models เพื่อให้ metadata รู้จักตาราง
from app.models.user import User  # noqa
from app.models.refresh_token import RefreshToken  # noqa
from app.models.password_reset_token import PasswordResetToken  # noqa
