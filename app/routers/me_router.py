from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlmodel import Session, select
from ulid import ULID

from app.auth import get_requestor_user
from app.db import Job, JobStatusEnum, JobTypeEnum, User, get_db_session
from app.models import JobRead



router = APIRouter(prefix='/me', tags=['me'])



@router.post('/files/stat-jobs/create', status_code=status.HTTP_201_CREATED, operation_id='create_state_task')
async def create_state_task(
    file_idno: ULID,
    db_session: Session = Depends(get_db_session),
    user: User | None = Security(get_requestor_user),
) -> UUID:
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    job = Job(job_type=JobTypeEnum.FILES_STAT, job_kwargs=None, status=JobStatusEnum.PENDING, user_id=user.id)
    job.queue_job_id = uuid4() # Enqueue the job and get a UUID from job queue
    db_session.add(job)
    db_session.commit()
    return job.queue_job_id
    



@router.get('/files/stat-jobs', operation_id='get_user_files_stat_jobs')
async def get_user_files_stat_jobs(
    user: User | None = Security(get_requestor_user),
    db_session: Session = Depends(get_db_session),
) -> list[JobRead]:
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    
    jobs = db_session.exec(select(Job).where(Job.user_id == user.id)).all()
    return [JobRead.model_validate(j, from_attributes=True) for j in jobs]
    



@router.get('/files/stat-jobs/{job_id}', operation_id='get_user_files_stat_job')
async def get_user_files_stat_job(
    job_id: UUID,
    user: User | None = Security(get_requestor_user),
    db_session: Session = Depends(get_db_session),
) -> JobRead:
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    job = db_session.exec(select(Job).where(Job.queue_job_id == job_id).where(Job.user_id == user.id)).one_or_none()
    if not job: raise HTTPException(status.HTTP_404_NOT_FOUND)
    return JobRead.model_validate(job, from_attributes=True)
