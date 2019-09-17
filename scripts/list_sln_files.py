import argparse
import logging
import os.path
from logutil import setup_logging
from vsutil import SolutionCache


logger = logging.getLogger(__name__)


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('solution',
                        help="The path to the Visual Studio solution file.")
    parser.add_argument('-p', '--project',
                        help="Only list files in the named project.")
    parser.add_argument('-c', '--cache',
                        help="Use a cache file to store the file list.")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Show verbose information.")
    args = parser.parse_args(args)
    setup_logging(args.verbose)

    cache, _ = SolutionCache.load_or_rebuild(args.solution, args.cache)
    slnobj = cache.slnobj

    projs = slnobj.projects
    if args.project:
        projs = [slnobj.find_project_by_name(args.project)]
    projs = list(filter(lambda p: not p.is_folder, projs))

    for p in projs:
        ig = p.defaultitemgroup()
        for i in ig.get_source_items():
            file_path = os.path.abspath(os.path.join(p.absdirpath, i.include))
            print(file_path)


if __name__ == '__main__':
    main()
