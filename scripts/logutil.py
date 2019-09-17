import logging


def setup_logging(verbose):
    loglevel = logging.INFO
    if verbose:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)

