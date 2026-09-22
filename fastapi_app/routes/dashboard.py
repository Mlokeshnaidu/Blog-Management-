from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.models.user import User
from fastapi_app.schemas.dashboard import DashboardResponse
from fastapi_app.services.dashboard_service import get_dashboard_data

router = APIRouter(prefix="/user", tags=["User Dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
@router.get("/dashboard/", response_model=DashboardResponse)
def user_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return personalised dashboard analytics for the authenticated user.

    Metrics include:
    - Total posts created
    - Total comments made
    - Total likes received on all posts
    - Total post views (if tracking enabled)
    - Per-post likes/comments distribution (for bar/pie charts)
    - Post activity over time (for line chart)

    **Requires JWT authentication.**
    """
    data = get_dashboard_data(current_user.id, db)
    return DashboardResponse(
        user_id=current_user.id,
        username=current_user.username,
        **data,
    )
