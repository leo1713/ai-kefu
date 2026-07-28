import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from app.services.agent_service import (
    create_agent,
    get_agent,
    list_agents,
    seed_default_agent,
    update_agent,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def get_agents(db: AsyncSession = Depends(get_db)) -> list[AgentResponse]:
    agents = await list_agents(db)
    return [AgentResponse.model_validate(a) for a in agents]


@router.post("", response_model=AgentResponse, status_code=201)
async def post_agent(
    data: AgentCreate, db: AsyncSession = Depends(get_db)
) -> AgentResponse:
    agent = await create_agent(db, data)
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent_by_id(
    agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> AgentResponse:
    agent = await get_agent(db, agent_id)
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def patch_agent(
    agent_id: uuid.UUID, data: AgentUpdate, db: AsyncSession = Depends(get_db)
) -> AgentResponse:
    agent = await update_agent(db, agent_id, data)
    return AgentResponse.model_validate(agent)


@router.post("/seed", response_model=AgentResponse, status_code=201)
async def post_seed_default(db: AsyncSession = Depends(get_db)) -> AgentResponse:
    agent = await seed_default_agent(db)
    return AgentResponse.model_validate(agent)
