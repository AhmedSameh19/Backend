from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.oGX.leads import router as leads_router
from app.api.v1.endpoints.oGX.Realizations.realizations import router as realizations_router
from app.api.v1.endpoints.oGX.Realizations.standards import router as ogx_standards_router
from app.api.v1.endpoints.oGX.status import router as status_router
from app.api.v1.endpoints.oGX.comments import router as comments_router
from app.api.v1.endpoints.oGX.followups import router as followups_router
from app.api.v1.endpoints.iCX.leads import router as icx_leads_router
from app.api.v1.endpoints.iCX.comments import router as icx_comments_router
from app.api.v1.endpoints.iCX.followups import router as icx_followups_router
from app.api.v1.endpoints.iCX.status import router as icx_status_router
from app.api.v1.endpoints.iCX.realizations import router as icx_realizations_router
from app.api.v1.endpoints.iCX.realizations_standards import router as icx_realizations_standards_router
from app.api.v1.endpoints.members import router as members_router
from app.api.v1.endpoints.B2C.back_to_process import router as b2c_back_to_process_router
from app.api.v1.endpoints.B2C.comments import router as b2c_comments_router
from app.api.v1.endpoints.B2C.status import router as b2c_leads_router
api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(leads_router)
api_router.include_router(realizations_router)
api_router.include_router(ogx_standards_router)
api_router.include_router(status_router)
api_router.include_router(comments_router)
api_router.include_router(followups_router)
api_router.include_router(icx_leads_router)
api_router.include_router(icx_comments_router)
api_router.include_router(icx_followups_router)
api_router.include_router(icx_status_router)
api_router.include_router(icx_realizations_router)
api_router.include_router(icx_realizations_standards_router)
api_router.include_router(members_router)
api_router.include_router(b2c_back_to_process_router)
api_router.include_router(b2c_comments_router)
api_router.include_router(b2c_leads_router)
