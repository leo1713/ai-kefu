from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate


async def list_agents(db: AsyncSession) -> list[Agent]:
    result = await db.execute(
        select(Agent).where(Agent.deleted_at.is_(None)).order_by(Agent.created_at)
    )
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, agent_id: object) -> Agent:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.deleted_at.is_(None))
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent not found")
    return agent


async def create_agent(db: AsyncSession, data: AgentCreate) -> Agent:
    agent = Agent(**data.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def update_agent(db: AsyncSession, agent_id: object, data: AgentUpdate) -> Agent:
    agent = await get_agent(db, agent_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(agent, field, value)
    await db.commit()
    await db.refresh(agent)
    return agent


async def seed_default_agent(db: AsyncSession) -> Agent:
    result = await db.execute(
        select(Agent).where(Agent.is_default.is_(True), Agent.deleted_at.is_(None))
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await create_agent(
        db,
        AgentCreate(
            name="默认客服",
            system_prompt=(
                "你是一个专业的AI客服助手，请用礼貌、简洁的语言回答客户问题。"
                "如果不确定答案，请诚实告知并建议转人工客服。"
            ),
            is_default=True,
        ),
    )
