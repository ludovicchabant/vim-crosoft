import os.path
import logging
from vsutil import SolutionCache


logger = logging.getLogger(__name__)

config_format = 2  # Keep in sync with vimcrosoft.vim


def load_vimcrosoft_auto_env(sln_file, build_env):
    cache_file = os.path.join(os.path.dirname(sln_file), '.vimcrosoft', 'config.txt')
    if not os.path.isfile(cache_file):
        logger.warn("No Vimcrosoft cache file found, you will probably have to specify "
                    "all configuration values in the command line!")
        return

    with open(cache_file, 'r', encoding='utf8') as fp:
        lines = fp.readlines()

    tokens = [
            '_VimcrosoftConfigFormat',
            '_VimcrosoftCurrentSolution',
            'Configuration',
            'Platform',
            '_VimcrosoftActiveProject']
    for i, line in enumerate(lines):
        token = tokens[i]
        build_env[token] = line.strip()

    try:
        found_conffmt = int(build_env['_VimcrosoftConfigFormat'].split('=')[-1])
    except:
        raise Exception("Invalid Vimcrosoft cache file found.")
    if found_conffmt != config_format:
        raise Exception("Incompatible Vimcrosoft cache file found. "
                        "Expected format %d but got %d" % (config_format, found_conffmt))

    logger.info("Loaded cached configuration|platform: %s|%s" %
                (build_env['Configuration'], build_env['Platform']))


def find_vimcrosoft_slncache(sln_file):
    return os.path.join(os.path.dirname(sln_file), '.vimcrosoft', 'slncache.bin')


def get_solution_cache(solution, slncache=None):
    if not solution:
        raise Exception(
            "No solution path was provided!")

    cache, loaded = SolutionCache.load_or_rebuild(solution, slncache)
    if not loaded:
        cache.build_cache()
        if slncache:
            logger.debug(f"Saving solution cache: {slncache}")
            cache.save(slncache)

    return cache


def find_item_project(item_path, solution, slncache=None):
    # Load the solution
    cache = get_solution_cache(solution, slncache)

    # Find the primary file in the solution.
    item_path_lower = item_path.lower()
    projpath = None
    for pp, pi in cache.index.items():
        if item_path_lower in pi:
            projpath = pp
            break
    else:
        raise Exception("File doesn't belong to the solution: %s" % item_path)

    # Find the project that our file belongs to.
    proj = cache.slnobj.find_project_by_path(projpath)
    if not proj:
        raise Exception("Can't find project in solution: %s" % projpath)

    return cache, proj
