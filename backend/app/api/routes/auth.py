from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register():
    return {"message": "Auth route scaffold. Implemented in Phase 5."}


@router.post("/login")
async def login():
    return {"message": "Auth route scaffold. Implemented in Phase 5."}
