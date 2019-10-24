import argparse
import logging
import os.path
from logutil import setup_logging
from vsutil import SolutionCache, ITEM_TYPE_SOURCE_FILES


logger = logging.getLogger(__name__)


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('solution',
                        help="The path to the Visual Studio solution file.")
    parser.add_argument('-c', '--cache',
                        help="The solution cache file to load.")
    parser.add_argument('--list-cache',
                        help=("If the solution cache is valid, use this "
                              "pre-saved file list. Otherwise, compute the "
                              "file list and save it to the given path."))
    parser.add_argument('-p', '--project',
                        help="Only list files in the named project.")
    parser.add_argument('-t', '--type',
                        action='append',
                        help="The type(s) of items to list.")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Show verbose information.")
    args = parser.parse_args(args)
    setup_logging(args.verbose)

    cache, loaded = SolutionCache.load_or_rebuild(args.solution, args.cache)
    if loaded and args.list_cache:
        cache_dt = os.path.getmtime(args.cache)
        list_cache_dt = os.path.getmtime(args.list_cache)
        if list_cache_dt > cache_dt:
            logger.debug("Solution cache was valid, re-using the file list cache.")
            try:
                with open(args.list_cache, 'r') as fp:
                    print(fp.read())
                return
            except OSError:
                logger.debug("File list cache unreachable, recomputing it.")
        else:
            logger.debug("Solution cache was valid but file list cache was older, "
                         "recomputing it.")

    slnobj = cache.slnobj

    projs = slnobj.projects
    if args.project:
        projs = [slnobj.find_project_by_name(args.project)]
    projs = list(filter(lambda p: not p.is_folder, projs))

    itemtypes = args.type or ITEM_TYPE_SOURCE_FILES
    items = []

    for p in projs:
        ig = p.defaultitemgroup()
        for i in ig.get_items_of_types(itemtypes):
            file_path = os.path.abspath(os.path.join(p.absdirpath, i.include))
            print(file_path)
            items.append(file_path + '\n')

    if args.list_cache:
        logger.debug("Writing file list cache: %s" % args.list_cache)
        with open(args.list_cache, 'w') as fp:
            fp.writelines(items)


if __name__ == '__main__':
    main()
