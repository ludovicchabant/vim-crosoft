import os.path
import pickle
import pprint
import logging
import argparse
from vsutil import SolutionCache


def main():
    parser = argparse.ArgumentParser()
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

    cachepath = args.cache
    try:
        with open(cachepath, 'rb') as fp:
            cache = pickle.load(fp)
    except Exception as ex:
        logger.error("Error loading solution cache: %s" % ex)
        return 1

    loaded_ver = getattr(cache, '_saved_version', 0)
    if loaded_ver != SolutionCache.VERSION:
        logger.warn(f"Cache was saved with older format: {cachepath} "
                    f"(got {loaded_ver}, expected {SolutionCache.VERSION})")
    else:
        logger.info(f"Cache has correct version: {loaded_ver}")

    logger.info(f"VSSolution: {cache.slnobj.path}")
    logger.info(f"Projects: {len(cache.slnobj.projects)}")
    for proj in cache.slnobj.projects:
        logger.info(f"  {proj.name}: {proj.path}")
    logger.info(f"Sections: {len(cache.slnobj.sections)}")
    for section in cache.slnobj.sections:
        logger.info(f"  {section.name} ({len(section.entries)} entries)")

if __name__ == '__main__':
    main()
