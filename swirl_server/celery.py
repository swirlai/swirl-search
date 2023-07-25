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
import ssl

logging.basicConfig(level=logging.INFO)

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')

### REDIS PROD TEST CONFIGURATION
# app = Celery('swirl_server', 
#              broker='rediss://localhost:16379/0', 
#              broker_use_ssl={'ssl_cert_reqs': ssl.CERT_REQUIRED,
#                                       'ssl_ca_certs': '/Users/dkostenko/Tests/tests/tls/ca.crt',
#                                       'ssl_certfile': '/Users/dkostenko/Tests/tests/tls/client.crt',
#                                       'ssl_keyfile': '/Users/dkostenko/Tests/tests/tls/client.key'
#                                     },
#              backend='rediss://localhost:16379/0',
#              redis_backend_use_ssl={'ssl_cert_reqs': ssl.CERT_REQUIRED,
#                                              'ssl_ca_certs': '/Users/dkostenko/Tests/tests/tls/ca.crt',
#                                              'ssl_certfile': '/Users/dkostenko/Tests/tests/tls/client.crt',
#                                              'ssl_keyfile': '/Users/dkostenko/Tests/tests/tls/client.key'
#                                             })

### REDIS DEV CONFIGURATION

app = Celery('swirl_server', 
             broker='redis://localhost:6379/0', 
             backend='redis://localhost:6379/0')

### RABBITMQ CONFIGURATION
# app = Celery('swirl_server', backend='rpc://', ampq='amqp://guest:guest@localhost:5672//')

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