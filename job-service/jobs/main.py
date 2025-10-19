from time import sleep

from rq import get_current_job
from sqlmodel import Session, select, func

from jobs.db import FcsFile, FilesStat, Job, JobStatusEnum, engine
from jobs.logging import logger



def do_files_stat(user_id: int):
    job = get_current_job()
    if not job:
        logger.error(f'Current job not found, it may not be ran from the job queue?')
        return
    
    with Session(engine) as session:
        # Make status to running
        logger.info(f'Job {job.id} is running')
        db_job = session.exec(select(Job).where(Job.queue_job_id == job.id)).one_or_none()
        if not db_job:
            logger.error(f'Job {job.id} not found in DB')
            return
        # logger.debug(db_job)

        db_job.status = JobStatusEnum.RUNNING
        session.add(db_job)
        session.commit()
        session.refresh(db_job)

        # Run the job
        files_count = session.exec(select(func.count(FcsFile.id)).where(FcsFile.user_id == user_id)).one()
        files_size_byte_sum: int | None = session.exec(select(func.sum(FcsFile.file_size_byte)).where(FcsFile.user_id == user_id)).one()
        if files_size_byte_sum is None: files_size_byte_sum = 0
        result = FilesStat(files_count=files_count, files_size_byte_sum=files_size_byte_sum)

        # Finish the job
        db_job.result = result.model_dump()
        db_job.status = JobStatusEnum.FINISHED
        session.add(db_job)
        session.commit()
        session.refresh(db_job)
        logger.info(f'Job {job.id} is finished')
    return result