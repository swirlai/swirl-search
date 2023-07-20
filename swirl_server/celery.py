'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    SWIRL 1.x
'''

import os
from celery import Celery
from celery.schedules import crontab
from celery.signals import after_setup_logger
import logging
logging.basicConfig(level=logging.INFO)

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')

### REDIS CONFIGURATION
# app = Celery('swirl_server', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

### RABBITMQ CONFIGURATION
app = Celery('swirl_server', backend='rpc://', ampq='amqp://guest:guest@localhost:5672//')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    print('Setting logger level to INFO')
    logger.setLevel(logging.INFO)

@app.task(name='process_federate_results')
def process_federate_results(results):
    # Process the results here (e.g., aggregate data, perform further actions)
    print("Processing federate results:", results)
    # ... Your additional processing logic ...
    return "Result processing completed"