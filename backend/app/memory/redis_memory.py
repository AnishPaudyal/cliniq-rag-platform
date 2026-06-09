class RedisConversationMemory:
    async def get_history(self, session_id: str) -> list[dict]:
        raise NotImplementedError("Redis memory is implemented in Phase 4.")
