import argparse
import logging
import os.path
import sys


if True: # 'vim' in sys.modules:
    sys.path.append(os.path.dirname(__file__))


from logutil import setup_logging
from vsutil import SolutionCache


logger = logging.getLogger(__name__)


def _build_cflags(filename, solution, buildenv=None, slncache=None):
    # Load the solution.
    if not solution:
        raise Exception(
            "No solution path was provided in the client data!")

    cache, loaded = SolutionCache.load_or_rebuild(solution, slncache)
    if not loaded:
        cache.build_cache()

    # Find the current file in the solution.
    filename_lower = filename.lower()
    projpath = None
    for pp, pi in cache.index.items():
        if filename_lower in pi:
            projpath = pp
            break
    else:
        raise Exception("File doesn't belong to the solution: %s" % filename)

    # Find the project that our file belongs to.
    proj = cache.slnobj.find_project_by_path(projpath)
    if not proj:
        raise Exception("Can't find project in solution: %s" % projpath)
    logger.debug("Found project %s: %s" % (proj.name, proj.abspath))

    # Get the provided config/platform combo, which represent a solution
    # configuration, and find the corresponding project configuration.
    # For instance, a solution configuration of "Debug|Win64" could map
    # to a "MyDebug|AnyCPU" configuration on a specific project.
    sln_config_platform = '%s|%s' % (buildenv['Configuration'],
                                     buildenv['Platform'])
    proj_config_platform = cache.slnobj.find_project_configuration(
        proj.guid, sln_config_platform)
    if not proj_config_platform:
        raise Exception("Can't find project configuration and platform for "
                        "solution configuration and platform: %s" %
                        sln_config_platform)

    # Make a build environment for the project, and figure out what
    # kind of project it is.
    proj_config, proj_platform = proj_config_platform.split('|')

    proj_buildenv = buildenv.copy()
    proj_buildenv['Configuration'] = proj_config
    proj_buildenv['Platform'] = proj_platform

    cfggroup = proj.propertygroup('Configuration', proj_buildenv)
    cfgtype = cfggroup.get('ConfigurationType')
    if not cfgtype:
        raise Exception("Can't find configuration type. Did you specify a "
                        "configuration name and platform? Got: %s" %
                        proj_buildenv)
    logger.debug("Found configuration type: %s" % cfgtype)

    # Let's prepare a list of standard stuff for C++.
    preproc = []
    incpaths = []
    projdir = os.path.dirname(proj.abspath)

    if cfgtype == 'Makefile':
        # It's a 'Makefile' project, which means we know as little about
        # compiler flags as whatever information was given to VS. As
        # such, if the solution setup doesn't give enough info, VS
        # intellisense won't work, and neither will YouCompleteMe.
        defaultpropgroup = proj.defaultpropertygroup(proj_buildenv)

        nmake_preproc = defaultpropgroup.get('NMakePreprocessorDefinitions')
        preproc += nmake_preproc.strip(';').split(';')

        nmake_incpaths = defaultpropgroup.get('NMakeIncludeSearchPath')
        incpaths += [os.path.abspath(os.path.join(projdir, p))
                     for p in nmake_incpaths.strip(';').split(';')]

    else:
        # We should definitely support standard VC++ projects here but
        # I don't need it yet :)
        raise Exception("Don't know how to handle configuration type: %s" %
                        cfgtype)

    # Build the clang/YCM flags with what we found.
    flags = ['-x', 'c++']  # TODO: check language type from project file.

    for symbol in preproc:
        flags.append('-D%s' % symbol)
    for path in incpaths:
        if path.startswith("C:\\Program Files"):
            flags.append('-isystem')
        else:
            flags.append('-I')
        flags.append(path)

    return {'flags': flags}


def _build_env_from_vim(client_data):
    buildenv = {}
    buildenv['Configuration'] = client_data.get('g:vimcrosoft_current_config', '')
    buildenv['Platform'] = client_data.get('g:vimcrosoft_current_platform', '')
    return buildenv


def Settings(**kwargs):
    language = kwargs.get('language')
    filename = kwargs.get('filename')

    client_data = kwargs.get('client_data', {})
    from_cli = kwargs.get('from_cli', False)
    if from_cli:
        solution = client_data.get('solution')
        slncache = client_data.get('slncache')
        buildenv = client_data.get('env', {})
    else:
        solution = client_data.get('g:vimcrosoft_current_sln')
        slncache = client_data.get('g:vimcrosoft_current_sln_cache')
        buildenv = _build_env_from_vim(client_data)

    flags = None

    if language == 'cfamily':
        try:
            flags = _build_cflags(filename, solution,
                                  buildenv=buildenv, slncache=slncache)
        except Exception as exc:
            if from_cli:
                raise
            flags = {'error': str(exc)}
    else:
        flags = {'error': f"Unknown language: {language}"}

    with open("D:\\P4\\DevEditor\\debug.txt", 'w') as fp:
        fp.write("kwargs:")
        fp.write(str(kwargs))
        fp.write("client_data:")
        fp.write(str(list(kwargs['client_data'].items())))
        fp.write("flags:")
        fp.write(str(flags))
    return flags


languages = {
    'cfamily': ['h', 'c', 'hpp', 'cpp', 'inl']
}


def _get_language(filename):
    _, ext = os.path.splitext(filename)
    ext = ext.lstrip('.')
    for lang, exts in languages.items():
        if ext in exts:
            return lang
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('solution',
                        help="The solution file")
    parser.add_argument('filename',
                        help="The filename for which to get flags")
    parser.add_argument('-p', '--property',
                        action="append",
                        help="Specifies a build property")
    parser.add_argument('-c', '--cache',
                        help="The solution cache to use")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Show debugging information")
    args = parser.parse_args()
    setup_logging(args.verbose)

    lang = _get_language(args.filename)
    logger.debug(f"Got language {lang} for {args.filename}")

    build_env = {}
    if args.property:
        for p in args.property:
            pname, pval = p.split('=', 1)
            build_env[pname] = pval
    logger.debug(f"Got build environment: {build_env}")
    client_data = {'solution': args.solution,
                   'slncache': args.cache,
                   'env': build_env}

    params = {'from_cli': True,
              'language': lang,
              'filename': args.filename,
              'client_data': client_data
              }
    flags = Settings(**params)
    logger.info("Flags:")
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(flags)


if __name__ == '__main__':
    main()
