from sqlalchemy.orm import Session
import models


class UserService:
    @staticmethod
    def list_users(db: Session):
        """Return all users without exposing passwords."""
        return db.query(models.User).all()
