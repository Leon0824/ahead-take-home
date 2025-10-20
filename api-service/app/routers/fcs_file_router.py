from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security, status
import rq
from sqlmodel import Session, select

from app.auth import get_requestor_user
from app.db import FcsFile, Job, JobStatusEnum, JobTypeEnum, User, get_db_session
from app.job import queue
from app.logging import logger
from app.models import FcsInfoJobRead, JobRead



router = APIRouter(prefix='/fcs-files', tags=['fcs_file'])



@router.post('/fcs-info-jobs/create', status_code=status.HTTP_201_CREATED, operation_id='create_fcs_info_job')
async def create_fcs_info_job(
    file_idno: str,
    db_session: Session = Depends(get_db_session),
    user: User | None = Security(get_requestor_user),
) -> UUID:
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    file = db_session.exec(select(FcsFile).where(FcsFile.file_idno == file_idno).where(FcsFile.user_id == user.id)).one_or_none()
    if not file: raise HTTPException(status.HTTP_400_BAD_REQUEST, f'File {file_idno} not found')

    job = Job(
        job_type=JobTypeEnum.FCS_INFO,
        job_args={'user_id': user.id, 'file_idno': file_idno},
        status=JobStatusEnum.PENDING,
        user_id=user.id,
    )
    queue_job: rq.job.Job = queue.enqueue(f='jobs.main.do_fcs_info', **job.job_args) # Enqueue the job and get a UUID from job queue
    job.queue_job_id = queue_job.id
    logger.info(f'User {user.username} created a FCS info job, queue job ID: {job.queue_job_id}')
    logger.info(f'Job {job.queue_job_id} is pending')

    db_session.add(job)
    db_session.commit()
    return job.queue_job_id



@router.get('/fcs-info-jobs', operation_id='get_user_fcs_info_jobs')
async def get_user_fcs_info_jobs(
    user: User | None = Security(get_requestor_user),
    db_session: Session = Depends(get_db_session),
) -> list[JobRead]:
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    
    statement = select(Job).where(Job.user_id == user.id).where(Job.job_type == JobTypeEnum.FCS_INFO)
    jobs = db_session.exec(statement).all()
    return [JobRead.model_validate(j, from_attributes=True) for j in jobs]
    


@router.get('/fcs-info-jobs/{job_id}', operation_id='get_user_fcs_info_job')
async def get_user_fcs_info_job(
    job_id: UUID,
    user: User | None = Security(get_requestor_user),
    db_session: Session = Depends(get_db_session),
) -> FcsInfoJobRead:
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    statement = select(Job).where(Job.queue_job_id == job_id).where(Job.user_id == user.id).where(Job.job_type == JobTypeEnum.FCS_INFO)
    job = db_session.exec(statement).one_or_none()
    if not job: raise HTTPException(status.HTTP_404_NOT_FOUND)
    return FcsInfoJobRead.model_validate(job, from_attributes=True)