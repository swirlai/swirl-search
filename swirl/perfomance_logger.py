import logging
import time
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)

class SwirlQueryRequestLogger:
    def __init__(self, providers, start_time=time.time(), request_id=uuid):
        self.request_id = request_id
        self.start_time = start_time
        self.providers = providers

    def put_providers(self, providers):
        self.providers = providers

    def complete_execution(self):
        elapsed_time = time.time() - self.start_time
        logger.info(f'PAZ_QXC|{self.id}|{elapsed_time}|{self.providers}')

    def timeout_execution(self):
        logger.info(f'PAZ_QXT|{self.id}|{getattr(settings, "SWIRL_TIMEOUT", 10)}|{self.providers}')

    def error_execution(self, msg):
        elapsed_time = time.time() - self.start_time
        logger.info(f'PAZ_QXE|{self.id}|{elapsed_time}|{self.providers}|{msg}')

class ProviderQueryRequestLogger:
    def __init__(self, name, id):
        self.name = name
        self.request_id = id

    def __enter__(self):
        self.start_time = time.time()

    def __exit__(self, type, value, traceback):
        elapsed_time = time.time() - self.start_time
        logger.info(f'PAZ_PXC|{self.request_id}|{elapsed_time}|{self.name}')

class SwirlRelevancyLogger:
    def __init__(self,  request_id):
        self.request_id = request_id

    def _log_elapsed(self, t, p):
        logger.info(f'PAZ_RP{p}|{self.reques}|{t}')

    def start_pass_1(self):
        self.pass_1_start_time = time.time()

    def complete_pass_1(self):
        elapsed_time = time.time() - self.pass_1_start_time
        self._log_elapsed(elapsed_time,1)

    def start_pass_2(self):
        self.pass_2_start_time = time.time()

    def complete_pass_2(self):
        elapsed_time = time.time() - self.pass_2_start_time
        self._log_elapsed(elapsed_time,2)
