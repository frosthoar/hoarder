import logging
import os
import pathlib
import sys
import tomllib


def load_config() -> dict:
    # get module path

    p = pathlib.Path(__file__).parent
    cf = p / "config.toml"
    with open(cf, "rb") as f:
        d = tomllib.load(f)
        p7z = pathlib.Path(d["executables"]["sevenzip"])
        if not os.path.isabs(p7z):
            d["executables"]["sevenzip"] = p / p7z
        return d


config = load_config()

SEVENZIP = config["executables"]["sevenzip"]

logger: logging.Logger = logging.getLogger("hoarder")

formatter: logging.Formatter = logging.Formatter(
    "%(asctime)s %(name)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger.setLevel(logging.DEBUG)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.addFilter(lambda record: record.levelno < logging.WARNING)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.WARNING)
stderr_handler.setFormatter(formatter)
logger.addHandler(stderr_handler)
