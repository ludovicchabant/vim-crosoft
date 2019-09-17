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
    parser.add_argument('-f', '--full-names',
                        action='store_true',
                        help="Print full names for nested projects.")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Show verbose information.")
    args = parser.parse_args(args)
    setup_logging(args.verbose)

    cache, _ = SolutionCache.load_or_rebuild(args.solution, args.cache)
    slnobj = cache.slnobj
    logger.debug("Found {0} projects:".format(len(slnobj.projects)))

    non_folder_projs = list(filter(lambda p: not p.is_folder,
                                   slnobj.projects))
    if args.full_names:
        parenting = {}
        nesting_sec = slnobj.globalsection("NestedProjects")
        if nesting_sec:
            for entry in nesting_sec.entries:
                child_guid, parent_guid = (entry.name.strip('{}'),
                                           entry.value.strip('{}'))
                child = slnobj.find_project_by_guid(child_guid, False)
                parent = slnobj.find_project_by_guid(parent_guid, False)
                parenting[child] = parent

        for p in non_folder_projs:
            full_name = p.name
            cur_p = p
            while True:
                cur_p = parenting.get(cur_p)
                if not cur_p:
                    break
                full_name = cur_p.name + "\\" + full_name
            print(full_name)
    else:
        for p in non_folder_projs:
            print(p.name)


if __name__ == '__main__':
    main()

