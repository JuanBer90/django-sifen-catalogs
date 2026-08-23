#!/usr/bin/env python
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Install the project with "
            'pip install -e ".[dev]" and try again.'
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
