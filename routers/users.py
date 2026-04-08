from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
import schemas
from database import get_db
from security import get_current_admin
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[schemas.UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """List all registered users (admin only)."""
    return UserService.list_users(db)
