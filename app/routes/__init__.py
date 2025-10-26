from app.routes.auth import router as auth_router
from app.routes.agent import router as agent_router
from app.routes.call import router as call_router
from app.routes.webhook import router as webhook_router
from app.routes.settings import router as settings_router

__all__ = ["auth_router", "agent_router", "call_router", "webhook_router", "settings_router"]