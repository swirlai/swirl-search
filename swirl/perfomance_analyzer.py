import logging
import time
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)

class SwirlQueryRequest:
    def __init__(self, request_id=uuid):
        self.request_id = request_id
        self.start_time = time.time()
        self.providers = []

    def put_providers(self, providers):
        self.providers = providers

    def complete_execution(self):
        elapsed_time = time.time() - self.start_time
        logger.info(f'PAZ_QXC|{self.id}|{elapsed_time}|{self.providers}')

    def timeout_execution(self):
        logger.info(f'PAZ_QXT|{self.id}|{getattr(settings, 'SWIRL_TIMEOUT', 10)}|{self.providers}')

    def error_execution(self):
        elapsed_time = time.time() - self.start_time
        logger.info(f'PAZ_QXE|{self.id}|{elapsed_time}|{self.providers}')

class ProviderQueryRequest:
    def __init__(self, name, id):
        self.name = name
        self.id = id
        self.start_time = time.time()

    def complete_execution(self):
        elapsed_time = time.time() - self.start_time
        logger.info(f'PAZ_PXC|{self.id}|{elapsed_time}')
        pass

class ElapsedTimeLogger:
    """
    Log elapsed time of individual tasks
    """
    def __init__(self, name, id):
        self.name = name
        self.id = id

    def __enter__(self):
        self.start_time = time.time()

    def __exit__(self, type, value, traceback):
        elapsed_time = time.time() - self.start_time
        logger.info(f'PAZ_EXT|{self.id}|{self.name}|{elapsed_time}')
