"""A deterministic model substitute with no credentials or network resources."""

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from agent_framework import (
    BaseChatClient,
    ChatResponse,
    ChatResponseUpdate,
    Content,
    Message,
    ResponseStream,
)


class LocalChatClient(BaseChatClient):
    """Count user messages in the supplied history and echo the latest prompt."""

    def _inner_get_response(
        self,
        *,
        messages: Sequence[Message],
        stream: bool,
        options: Mapping[str, Any],
        **kwargs: Any,
    ):
        turns = sum(message.role == "user" for message in messages)
        text = f"User turn {turns}: {messages[-1].text}"
        created_at = datetime.now(timezone.utc).isoformat()

        async def updates():
            yield ChatResponseUpdate(
                role="assistant", contents=[Content.from_text(text)],
                created_at=created_at,
            )

        async def respond():
            return ChatResponse(
                messages=[Message(role="assistant", contents=[text])],
                created_at=created_at,
            )

        if stream:
            return ResponseStream(updates(), finalizer=ChatResponse.from_updates)
        return respond()
