import logging
import time
import uuid
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

class SwirlQueryRequestLogger:
    def __init__(self, query, providers, start_time=None, request_id=None):
        self.request_id = request_id if request_id is not None else str(uuid.uuid4())
        self.start_time = start_time if start_time is not None else time.time()
        self.providers = providers
        self.query = query

    def put_providers(self, providers):
        self.providers = providers

    def complete_execution(self):
        elapsed_time = time.time() - self.start_time
        logger.debug(f'PLG_QXC|{self.request_id}|{round(elapsed_time,4)}|{self.query}|{self.providers}')

    def timeout_execution(self):
        logger.debug(f'PLG_QXT|{self.request_id}|{getattr(settings, "SWIRL_TIMEOUT", 10)}|{self.query}|{self.providers}')

    def error_execution(self, msg):
        elapsed_time = time.time() - self.start_time
        logger.debug(f'PLG_QXE|{self.request_id}|{round(elapsed_time,4)}|{self.query}|{self.providers}|{msg}')

class ProviderQueryRequestLogger:
    def __init__(self, name, id):
        self.name = name
        self.request_id = id

    def __enter__(self):
        self.start_time = time.time()

    def __exit__(self, type, value, traceback):
        elapsed_time = time.time() - self.start_time
        logger.debug(f'PLG_PXC|{self.request_id}|{round(elapsed_time,4)}|{self.name}')

class SwirlRelevancyLogger:
    def __init__(self,  request_id, name="anonymous",log_sim=False):
        self.request_id = request_id
        self.name = name
        self.log_sim = log_sim

    def _log_elapsed(self, t, p):
        logger.debug(f'PLG_RP{p}|{self.request_id}|{t}|{self.name}')

    def start_pass_1(self):
        self.pass_1_start_time = time.time()

    def complete_pass_1(self):
        elapsed_time = time.time() - self.pass_1_start_time
        self._log_elapsed(round(elapsed_time,4),1)

    def start_pass_2(self):
        self.pass_2_start_time = time.time()

    def complete_pass_2(self):
        elapsed_time = time.time() - self.pass_2_start_time
        self._log_elapsed(round(elapsed_time,4),2)

    def start_nlp(self, flen):
        self.nlp_start_time = time.time()
        self.nlp_field_len = flen

    def end_nlp(self):
        elapsed_time = time.time() - self.nlp_start_time
        if self.log_sim:
            logger.debug(f'PLG_NLP|{self.request_id}|{round(elapsed_time,4)}|{self.nlp_field_len}')

    def start_sim(self):
        self.sim_start_time = time.time()

    def end_sim(self):
        elapsed_time = time.time() - self.sim_start_time
        if self.log_sim:
            logger.debug(f'PLG_SIM|{self.request_id}|{round(elapsed_time,4)}|')
