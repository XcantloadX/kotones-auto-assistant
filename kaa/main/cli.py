import warnings

try:
    from ..util.telemetry import setup  # noqa: F401
    setup()
except Exception as e:
    print(f'Failed to set up telemetry: {e}')

warnings.filterwarnings("ignore", message=".*HTTP_422_UNPROCESSABLE_ENTITY.*")

import kaa.application.cli.setup  # noqa: F401
from kaa.application.cli.index import main

if __name__ == '__main__':
    main()
