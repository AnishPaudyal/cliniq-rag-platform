from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.limiter import limiter
from app.auth.jwt_handler import get_current_user, require_admin
from app.db.models import Feedback, User
from app.db.postgres import get_session

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    query_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    thumbs: str = Field(pattern="^(up|down|neutral)$")


@router.post("")
@limiter.limit("10/minute")
async def feedback(
    request: Request,
    payload: FeedbackRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = Feedback(
        query_id=payload.query_id,
        rating=payload.rating,
        comment=payload.comment,
        thumbs=payload.thumbs,
        user_id=user.id,
    )
    session.add(item)
    await session.commit()
    return {"status": "stored", "feedback_id": item.id}


@router.get("/summary")
@limiter.limit("10/minute")
async def feedback_summary(
    request: Request,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    avg_rating = await session.execute(select(func.avg(Feedback.rating)))
    complaints = await session.execute(
        select(Feedback.comment)
        .where(Feedback.thumbs == "down", Feedback.comment.is_not(None))
        .order_by(Feedback.created_at.desc())
        .limit(10)
    )
    return {
        "avg_rating": float(avg_rating.scalar() or 0.0),
        "common_complaints": [row[0] for row in complaints.all()],
    }
