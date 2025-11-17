from fastapi import APIRouter

from models.schemas import TestData

router = APIRouter(prefix="/dummy", tags=["Dummy"])


@router.get("/test-data", response_model=TestData)
async def test_data():
    return TestData(some_text="Hello World!", random_number="42")
