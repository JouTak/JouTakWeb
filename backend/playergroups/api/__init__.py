from . import content, members, processes
from .account import router as account_router
from .moderation import router as moderation_router
from .profiles import router as profile_router

router = content.router
router.add_router("", members.router)
router.add_router("", processes.router)

__all__ = ["router", "account_router", "profile_router", "moderation_router"]
