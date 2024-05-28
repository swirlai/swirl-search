#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    print("Starting Swirl")
    if os.getenv('SWIRL_ENABLE_DEBUGPY', 'False') == 'True' and os.getenv('_SWIRL_IN_DEBUG', 'False') != 'True':
        dj_debug_port = os.getenv('SWIRL_DJANGO_DEBUG_PORT', 7029)
        print("Debug enabled")
        import debugpy
        debugpy.listen(('0.0.0.0', dj_debug_port))
        print(f"Waiting for debugger to attach at port {dj_debug_port}...")
        debugpy.wait_for_client()
        os.environ['_SWIRL_IN_DEBUG'] = 'True'
        _IN_DEBUG=True
        print("Debugger attached")
    main()