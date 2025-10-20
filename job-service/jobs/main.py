from tempfile import NamedTemporaryFile
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flowio import FlowData
from rq import get_current_job
from sqlmodel import Session, select, func

from jobs.db import FcsFile, FcsInfo, FilesStat, Job, JobStatusEnum, engine
from jobs.logging import logger
from jobs.settings import get_settings



_SETTINGS = get_settings()



def do_files_stat(user_id: int):
    start_time = time.perf_counter()
    job = get_current_job()
    if not job:
        logger.error(f'Current job not found, it may not be ran from the job queue?')
        return
    
    with Session(engine) as session:
        # Make status to running
        db_job = session.exec(select(Job).where(Job.queue_job_id == job.id)).one_or_none()
        if not db_job:
            logger.error(f'Job {job.id} not found in DB')
            return
        logger.info(f'{db_job.job_type} Job {job.id} is running')

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
        db_job.job_working_duration_second = time.perf_counter() - start_time
        session.add(db_job)
        session.commit()
        session.refresh(db_job)
        logger.info(f'Job {job.id} is finished')
    return result



def do_fcs_info(user_id: int, file_idno: str):
    start_time = time.perf_counter()
    job = get_current_job()
    if not job:
        logger.error(f'Current job not found, it may not be ran from the job queue?')
        return
    
    with Session(engine) as session:
        # Make status to running
        db_job = session.exec(select(Job).where(Job.queue_job_id == job.id)).one_or_none()
        if not db_job:
            logger.error(f'Job {job.id} not found in DB')
            return
        logger.info(f'{db_job.job_type} Job {job.id} is running')

        db_job.status = JobStatusEnum.RUNNING
        session.add(db_job)
        session.commit()
        session.refresh(db_job)

        # Run the job
        db_file = session.exec(select(FcsFile).where(FcsFile.file_idno == file_idno).where(FcsFile.user_id == user_id)).one_or_none()
        if not db_file:
            logger.error(f'File {file_idno} not found')
            return

        s3_client = boto3.client(
            's3',
            region_name=_SETTINGS.AWS_DEFAULT_REGION,
            endpoint_url='https://2d318ba7bbba6520730569a4819999c4.r2.cloudflarestorage.com',
            aws_access_key_id=_SETTINGS.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=_SETTINGS.AWS_SECRET_ACCESS_KEY.get_secret_value(),
        )
        with NamedTemporaryFile(suffix='.fcs', prefix=db_file.file_name, delete=False) as fcs_file:
            try: s3_client.download_fileobj(Bucket='ahead-fcs-files', Key=db_file.s3_key, Fileobj=fcs_file)
            except BotoCoreError as boto_error:
                logger.error(boto_error)
                return
            except ClientError as client_error:
                logger.error(client_error)
                return
            fd = FlowData(fcs_file)
            # logger.debug(fd.name) # /var/folders/8k/cxl3xhj13bj4n8rb_r83ds200000gn/T/0000123456_1234567_AML_ClearLLab10C_BTube.fcsklhz2za3.fcs
            # logger.debug(db_file.file_size_byte) # 2585280
            # logger.debug(fd.file_size) # 2585280
            result = FcsInfo(
                file_name=db_file.file_name, file_size_byte=db_file.file_size_byte, file_upload_time=db_file.upload_batch.upload_time,
                fcs_version=fd.version, fcs_pnn_labels=fd.pnn_labels, fcs_event_count=fd.event_count,
            )

        # Finish the job
        db_job.result = result.model_dump(mode='json')
        db_job.status = JobStatusEnum.FINISHED
        db_job.job_working_duration_second = time.perf_counter() - start_time
        session.add(db_job)
        session.commit()
        session.refresh(db_job)
        logger.info(f'Job {job.id} is finished')
    return result