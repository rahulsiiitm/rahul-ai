from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.admin_auth import require_admin_key
from models.schemas import AdminChatDeleteRequest
from services.chat_admin import (
    ChatDeletionConfigurationError,
    delete_all_chats,
    delete_selected_chats,
)

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin_key)])


@router.delete("/chats/{session_id}")
async def delete_one_chat(session_id: str) -> dict[str, int | str]:
    try:
        normalized = str(UUID(session_id))
        return await delete_selected_chats([normalized])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid session ID.") from exc
    except ChatDeletionConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        print(f"[ADMIN DELETE] Failed: {type(exc).__name__}")
        raise HTTPException(status_code=502, detail="Chat deletion failed.") from exc


@router.delete("/chats")
async def delete_chats(body: AdminChatDeleteRequest) -> dict[str, int | str]:
    try:
        if body.delete_all:
            return await delete_all_chats()
        return await delete_selected_chats(body.session_ids)
    except ChatDeletionConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        print(f"[ADMIN DELETE] Failed: {type(exc).__name__}")
        raise HTTPException(status_code=502, detail="Chat deletion failed.") from exc
