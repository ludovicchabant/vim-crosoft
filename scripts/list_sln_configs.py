import argparse
import logging
from logutil import setup_logging
from vsutil import SolutionCache


logger = logging.getLogger(__name__)


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('solution',
                        help="The path to the Visual Studio solution file.")
    parser.add_argument('-c', '--cache',
                        help="The path to the solution cache.")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Show verbose information.")
    args = parser.parse_args(args)
    setup_logging(args.verbose)

    cache, _ = SolutionCache.load_or_rebuild(args.solution, args.cache)
    sec = cache.slnobj.globalsection('SolutionConfigurationPlatforms')
    for e in sec.entries:
        config, platform = e.name.split('|')
        if config != "Invalid" and platform != "Invalid":
            print(e.name)


if __name__ == '__main__':
    main()
