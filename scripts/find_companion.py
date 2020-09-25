import argparse
import logging
import os.path
import sys


if True: # 'vim' in sys.modules:
    sys.path.append(os.path.dirname(__file__))


from logutil import setup_logging
from vshelpers import load_vimcrosoft_auto_env, find_vimcrosoft_slncache, find_item_project
from vsutil import SolutionCache, ITEM_TYPE_CPP_SRC, ITEM_TYPE_CPP_HDR


logger = logging.getLogger(__name__)


def _find_companion_item(solution, item_path, companion_name=None, companion_type=None, slncache=None):
    # Try to guess the default companion file if needed.
    if companion_name == None or companion_type == None:
        primary_name, primary_ext = os.path.splitext(item_path)
        primary_name = os.path.basename(primary_name)
        if primary_ext == '.cpp':
            companion_name = primary_name + '.h'
            companion_type = ITEM_TYPE_CPP_HDR
        elif primary_ext == '.h':
            companion_name = primary_name + '.cpp'
            companion_type = ITEM_TYPE_CPP_SRC
        else:
            raise Exception("Can't guess the companion file for: %s" % item_path)

    # Find the primary file in the solution.
    cache, proj = find_item_project(item_path, solution, slncache)
    logger.debug("Found project %s: %s" % (proj.name, proj.abspath))

    # Look for the companion file in that project:
    candidates = []
    dfgroup = proj.defaultitemgroup()
    for cur_item in dfgroup.get_items_of_type(companion_type):
        cur_item_name = os.path.basename(cur_item.include)
        if cur_item_name == companion_name:
            cur_item_path = proj.get_abs_item_include(cur_item)
            candidates.append((cur_item, _get_companion_score(cur_item_path, item_path)))
    candidates = sorted(candidates, key=lambda i: i[1], reverse=True)
    logger.debug("Found candidates: %s" % [(c[0].include, c[1]) for c in candidates])
    if candidates:
        return proj.get_abs_item_include(candidates[0][0])
    return None


def _get_companion_score(item_path, ref_path):
    for i, c in enumerate(zip(item_path, ref_path)):
        if c[0] != c[1]:
            return i
    return min(len(item_path, ref_path))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('solution',
                        help="The solution file")
    parser.add_argument('filename',
                        help="The filename for which to get the companion")
    parser.add_argument('--no-auto-env',
                        action='store_true',
                        help="Don't read configuration information from Vimcrosoft cache")
    parser.add_argument('-c', '--cache',
                        help="The solution cache to use")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Show debugging information")
    args = parser.parse_args()
    setup_logging(args.verbose)

    build_env = {}
    slncache = args.cache
    if not args.no_auto_env:
        load_vimcrosoft_auto_env(args.solution, build_env)
        if not slncache:
            slncache = find_vimcrosoft_slncache(args.solution)

    companion = _find_companion_item(args.solution, args.filename,
                                     slncache=slncache)
    print(companion)

if __name__ == '__main__':
    main()
