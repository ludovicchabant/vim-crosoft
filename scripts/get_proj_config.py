import argparse
import logging
import re
from vsutil import SolutionCache


re = _re_proj_cfg_suffix = re.compile(r'\.(ActiveCfg|Build\.0)$')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('solution',
                        help="The path to the Visual Studio solution file.")
    parser.add_argument('cache',
                        help="The path to the solution cache.")
    parser.add_argument('project',
                        help="The name of the project to check for.")
    parser.add_argument('slnconfig',
                        help="The solution configuration.")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Show verbose information.")
    args = parser.parse_args()

    loglevel = logging.INFO
    if args.verbose:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)
    logger = logging.getLogger()

    cache, loaded = SolutionCache.load_or_rebuild(args.solution, args.cache)
    logger.debug("Cache was %s" % ("valid" if loaded else "not valid"))

    proj = cache.slnobj.find_project_by_name(args.project)
    if proj is None:
        raise Exception("No such project: %s" % args.project)
    projguid = '{%s}' % proj.guid

    slnconfig = args.slnconfig.replace(' ', '_')
    sec = cache.slnobj.globalsection('ProjectConfigurationPlatforms')
    for e in sec.entries:
        if e.name.startswith(projguid):
            if slnconfig == e.value.replace(' ', '_'):
                projcfg = e.name[len(projguid) + 1:]
                projcfg = _re_proj_cfg_suffix.sub('', projcfg)
                print(projcfg)
                break


if __name__ == '__main__':
    main()

