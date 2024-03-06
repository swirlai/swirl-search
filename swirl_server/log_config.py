import os
import logging.config

def setup_logging(default_level=logging.INFO):
    debug_modules = os.getenv("SWIRL_LOG_DEBUG", "").split(",")

    # Define a formatter with your specified format
    formatter = {
        'format': '{levelname} {asctime} {module} {message}',
        'style': '{',  # Use format string syntax for placeholders
        'datefmt': '%Y-%m-%d %H:%M:%S',  # Example date format, adjust as needed
    }

    # Initialize the logging configuration with default settings
    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'custom': formatter,  # Registering your custom formatter
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'custom',  # Apply your custom formatter here
            },
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console'],
                'level': logging.getLevelName(default_level),
                'propagate': True,
            },
        }
    }

    # Set DEBUG level for specific modules
    for module in debug_modules:
        if module:  # Check for empty strings
            module = module.strip()
            print(f'log_config setting DEBUG logging in : {module}')
            log_config['loggers'][module] = {
                'level': 'DEBUG',
                'handlers': ['console'],
                'propagate': False
            }

    logging.config.dictConfig(log_config)
