import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.evaluation_cycle import get_cycle_by_id
from app.crud.user import list_active_users_by_company
from app.models.evaluation import Evaluation, EvaluationType
from app.models.evaluation_cycle import CycleStatus, EvaluationCycle
from app.models.question import Question
from app.schemas.evaluation_cycle import CycleCreate


async def create_cycle(db: AsyncSession, company_id: uuid.UUID, data: CycleCreate) -> EvaluationCycle:
    cycle = EvaluationCycle(
        company_id=company_id,
        name=data.name,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    db.add(cycle)
    await db.flush()

    for q in data.questions:
        db.add(Question(cycle_id=cycle.id, text=q.text, type=q.type, order=q.order))

    await db.commit()

    # Re-fetch with questions eager-loaded rather than relying on lazy-loading the
    # relationship afterward, which doesn't work outside an explicit eager-load in async SQLAlchemy.
    return await get_cycle_by_id(db, cycle.id)


async def activate_cycle(db: AsyncSession, cycle: EvaluationCycle) -> EvaluationCycle:
    if cycle.status != CycleStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only draft cycles can be activated")

    users = await list_active_users_by_company(db, cycle.company_id)
    for user in users:
        db.add(Evaluation(cycle_id=cycle.id, subject_id=user.id, evaluator_id=user.id, type=EvaluationType.SELF))
        if user.manager_id is not None:
            db.add(
                Evaluation(
                    cycle_id=cycle.id,
                    subject_id=user.id,
                    evaluator_id=user.manager_id,
                    type=EvaluationType.MANAGER,
                )
            )

    cycle.status = CycleStatus.ACTIVE
    await db.commit()
    await db.refresh(cycle)
    return cycle
