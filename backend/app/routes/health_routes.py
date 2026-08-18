from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "study-abroad-ai-backend",
        "message": "API is running successfully."
    }
