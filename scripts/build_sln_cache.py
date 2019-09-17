import os.path
import logging
import argparse
from vsutil import SolutionCache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('solution',
                        help="The path to the solution file")
    parser.add_argument('cache',
                        help="The path to the cache file")
    parser.add_argument('-v', '--verbose',
                        action='store_true')
    args = parser.parse_args()

    loglevel = logging.INFO
    if args.verbose:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)
    logger = logging.getLogger()

    cache, loaded = SolutionCache.load_or_rebuild(args.solution, args.cache)
    if not loaded:
        total_items = sum([len(i) for i in cache.index.values()])
        logger.debug(f"Built cache with {total_items} items.")


if __name__ == '__main__':
    main()
