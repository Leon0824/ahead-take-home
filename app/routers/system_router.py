from fastapi import APIRouter



router = APIRouter(prefix='/system', tags=['system'])



@router.get('/health', operation_id='get_health_status')
async def get_health_status() -> bool: return True