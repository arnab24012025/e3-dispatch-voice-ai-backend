from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.agent import AgentConfiguration
from app.models.user import User
from app.schemas.agent import (
    AgentConfigurationCreate,
    AgentConfigurationUpdate,
    AgentConfigurationResponse
)
from app.utils.dependencies import get_current_user
from app.services.retell_service import retell_service

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/", response_model=AgentConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_configuration(
    agent_data: AgentConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new agent configuration and Retell AI agent"""
    
    # Create agent in Retell AI first
    try:
        retell_response = await retell_service.create_agent(
            agent_name=agent_data.name,
            system_prompt=agent_data.system_prompt,
            initial_message=agent_data.initial_message,
            voice_settings=agent_data.voice_settings
        )
        retell_agent_id = retell_response.get("agent_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent in Retell: {str(e)}"
        )
    
    # Create agent in database
    db_agent = AgentConfiguration(
        name=agent_data.name,
        description=agent_data.description,
        system_prompt=agent_data.system_prompt,
        initial_message=agent_data.initial_message,
        voice_settings=agent_data.voice_settings,
        scenario_type=agent_data.scenario_type,
        retell_agent_id=retell_agent_id,
        created_by=current_user.id
    )
    
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    
    return db_agent


@router.get("/", response_model=List[AgentConfigurationResponse])
async def list_agent_configurations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all agent configurations"""
    agents = db.query(AgentConfiguration).offset(skip).limit(limit).all()
    return agents


@router.get("/{agent_id}", response_model=AgentConfigurationResponse)
async def get_agent_configuration(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific agent configuration by ID"""
    agent = db.query(AgentConfiguration).filter(AgentConfiguration.id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent configuration not found"
        )
    
    return agent


@router.put("/{agent_id}", response_model=AgentConfigurationResponse)
async def update_agent_configuration(
    agent_id: int,
    agent_update: AgentConfigurationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an agent configuration"""
    agent = db.query(AgentConfiguration).filter(AgentConfiguration.id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent configuration not found"
        )
    
    # Update fields
    update_data = agent_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    
    # Update in Retell AI if agent exists there
    if agent.retell_agent_id:
        try:
            await retell_service.update_agent(
                agent_id=agent.retell_agent_id,
                updates=update_data
            )
        except Exception as e:
            print(f"Warning: Failed to update agent in Retell: {e}")
    
    db.commit()
    db.refresh(agent)
    
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_configuration(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an agent configuration (soft delete)"""
    agent = db.query(AgentConfiguration).filter(AgentConfiguration.id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent configuration not found"
        )
    
    agent.is_active = False
    db.commit()
    
    return None