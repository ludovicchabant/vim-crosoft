import argparse
import logging
import os.path
import shutil
import sys


if True: # 'vim' in sys.modules:
    sys.path.append(os.path.dirname(__file__))


from logutil import setup_logging
from vshelpers import load_vimcrosoft_auto_env, find_vimcrosoft_slncache, find_item_project
from vsutil import SolutionCache, ITEM_TYPE_CPP_SRC, ITEM_TYPE_CPP_HDR


logger = logging.getLogger(__name__)


def _split_paths_property(val):
    if val:
        return val.strip(';').split(';')
    return []


def _split_paths_property_and_make_absolute(basedir, val):
    return [os.path.abspath(os.path.join(basedir, p))
            for p in _split_paths_property(val)]


def _get_item_specific_flags(projdir, clcompileitems, filename):
    logger.debug("Looking through %d items to find: %s" % (len(clcompileitems), filename))
    filename_lower = filename.lower()
    for item in clcompileitems:
        absiteminclude = os.path.normpath(os.path.join(projdir, item.include))
        if absiteminclude.lower() != filename_lower:
            continue
        logger.debug("Found file-specific flags for: %s" % filename)
        incpaths = _split_paths_property_and_make_absolute(
                projdir, item.metadata.get('AdditionalIncludeDirectories'))
        incfiles = _split_paths_property_and_make_absolute(
                projdir, item.metadata.get('ForcedIncludeFiles'))
        return (incpaths, incfiles)
    return ([], [])


def _find_any_possible_item_specific_flags(
        solution, slncache, projdir, clcompileitems, filename, incpaths, incfiles, *,
        search_neighbours=True):
    # First, find any actual flags for this item.
    item_incpaths, item_incfiles = _get_item_specific_flags(projdir, clcompileitems, filename)
    if item_incpaths or item_incfiles:
        incpaths += item_incpaths
        incfiles += item_incfiles
        return True

    logger.debug("Requested item didn't have any flags, looking for related items")
    from find_companion import _find_companion_item
    companion_item = _find_companion_item(solution, filename, slncache=slncache)
    if companion_item:
        item_incpaths, item_incfiles = _get_item_specific_flags(projdir, clcompileitems, companion_item)
        if item_incpaths or item_incfiles:
            logger.debug("Found flags on companion item: %s" % companion_item)
            incpaths += item_incpaths
            incfiles += item_incfiles
            return True

    #logger.debug("No companion item found, see if we can find flags for a neighbour")
    #dirname = os.path.dirname(filename)
    #neighbournames = os.listdir(dirname)
    #neighbournames.remove(os.path.basename(filename))
    #for neighbourname in neighbournames:
    #    neighbourpath = os.path.join(dirname, neighbourname)
    #    item_incpaths, item_incfiles = _get_item_specific_flags(projdir, clcompileitems, neighbourpath)
    #    if item_incpaths or item_incfiles:
    #        logger.debug("Found flags on: %d" % neighbourpath)
    #        incpaths += item_incpaths
    #        incfiles += item_incfiles
    #        return True

    #    neighbour_companion = _find_companion_item(solution, filename, slncache=slncache)
    #    if neighbour_companion:
    #        item_incpaths, item_incfiles = _get_item_specific_flags(projdir, clcompileitems, neighbour_companion)
    #        if item_incpaths or item_incfiles:
    #            logger.debug("Found flags on: %s" % neighbour_companion)
    #            incpaths += item_incpaths
    #            incfiles += item_incfiles
    #            return True

    #logger.debug("No flags found anywhere...")
    return False


def _expand_extra_flags_with_solution_extra_flags(solution, extraflags):
    argfilename = os.path.join(
            os.path.dirname(solution),
            '.vimcrosoft',
            (os.path.basename(solution) + '.flags'))
    try:
        with open(argfilename, 'r', encoding='utf8') as fp:
            lines = fp.readlines()
            logger.debug("Read extra flags from: %s (%d lines)" % (argfilename, len(lines)))
    except OSError:
        return extraflags

    extraflags = extraflags or []
    for line in lines:
        if not line.startswith('#'):
            extraflags.append(line.strip())
    return extraflags


def _build_cflags(filename, solution, buildenv=None, slncache=None, extraflags=None,
                  force_fwd_slashes=True, short_flags=True):
    # Find the current file in the solution.
    cache, proj = find_item_project(filename, solution, slncache)
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
    incfiles = []
    projdir = os.path.dirname(proj.abspath)

    if cfgtype == 'Makefile':
        # It's a 'Makefile' project, which means we know as little about
        # compiler flags as whatever information was given to VS. As
        # such, if the solution setup doesn't give enough info, VS
        # intellisense won't work, and neither will YouCompleteMe.
        defaultpropgroup = proj.defaultpropertygroup(proj_buildenv)

        nmake_preproc = defaultpropgroup.get('NMakePreprocessorDefinitions')
        preproc += _split_paths_property(nmake_preproc)

        vs_incpaths = defaultpropgroup.get('IncludePath')
        if vs_incpaths:
            incpaths += _split_paths_property_and_make_absolute(
                    projdir, vs_incpaths)

        nmake_incpaths = defaultpropgroup.get('NMakeIncludeSearchPath')
        if nmake_incpaths:
            incpaths += _split_paths_property_and_make_absolute(
                    projdir, nmake_incpaths)

        nmake_forcedincs = defaultpropgroup.get('NMakeForcedIncludes')
        if nmake_forcedincs:
            incfiles += _split_paths_property_and_make_absolute(
                    projdir, nmake_forcedincs)

        # Find stuff specific to the file we are working on.
        defaultitemgroup = proj.defaultitemgroup(proj_buildenv)
        clcompileitems = list(defaultitemgroup.get_items_of_types([ITEM_TYPE_CPP_SRC, ITEM_TYPE_CPP_HDR]))
        _find_any_possible_item_specific_flags(
                solution, slncache, projdir, clcompileitems, filename, incpaths, incfiles)

    else:
        # We should definitely support standard VC++ projects here but
        # I don't need it yet :)
        raise Exception("Don't know how to handle configuration type: %s" %
                        cfgtype)

    # We need to duplicate all the forced-included files because they could
    # have a VS-generated PCH file next to them. Clang then tries to pick it
    # up and complains that it doesn't use a valid format... :(
    incfiles = _cache_pch_files(incfiles)

    # Build the clang/YCM flags with what we found.
    flags = ['-x', 'c++']  # TODO: check language type from project file.

    for symbol in preproc:
        flags.append('-D%s' % symbol)
    for path in incpaths:
        flagname = '-I'
        if path.startswith("C:\\Program Files"):
            flagname = '-isystem'
        flagval = path.replace('\\', '/') if force_fwd_slashes else path
        if short_flags:
            flags.append('%s%s' % (flagname, flagval))
        else:
            flags.append(flagname)
            flags.append(flagval)
    # For some reason it seems VS applies those in last-to-first order.
    incfiles = list(reversed(incfiles))
    for path in incfiles:
        if force_fwd_slashes:
            flags.append('--include=%s' % path.replace('\\', '/'))
        else:
            flags.append('--include=%s' % path)

    if extraflags:
        flags += extraflags

    return {'flags': flags}


_clang_shadow_pch_suffix = '-for-clang'


def _cache_pch_files(paths):
    outpaths = []
    for path in paths:
        name, ext = os.path.splitext(path)
        outpath = "%s%s%s" % (name, _clang_shadow_pch_suffix, ext)

        do_cache = False
        orig_mtime = os.path.getmtime(path)
        try:
            out_mtime = os.path.getmtime(outpath)
            if orig_mtime >= out_mtime:
                do_cache = True
        except OSError:
            do_cache = True

        if do_cache:
            logger.debug("Creating shadow PCH file: %s" % path)
            shutil.copy2(path, outpath)

        outpaths.append(outpath)
    return outpaths


def _build_env_from_vim(client_data):
    buildenv = {}
    buildenv['Configuration'] = client_data.get('g:vimcrosoft_current_config', '')
    buildenv['Platform'] = client_data.get('g:vimcrosoft_current_platform', '')
    return buildenv


_dump_debug_file = True


def _do_dump_debug_file(args, flags, debug_filename):
    import pprint

    with open(debug_filename, 'w') as fp:
        fp.write("  args:  \n")
        fp.write("=========\n")
        pp = pprint.PrettyPrinter(indent=2, stream=fp)
        pp.pprint(args)
        fp.write("\n\n")

        fp.write("  flags:  \n")
        fp.write("==========\n")
        flags = flags.get('flags')
        if flags:
            fp.write(flags[0])
            for flag in flags[1:]:
                if flag[0] == '-':
                    fp.write("\n")
                else:
                    fp.write("  ")
                fp.write(flag)
        else:
            fp.write("<no flags found>\n")
        fp.write("\n\n")


def Settings(**kwargs):
    language = kwargs.get('language')
    filename = kwargs.get('filename')

    client_data = kwargs.get('client_data', {})
    from_cli = kwargs.get('from_cli', False)
    if from_cli:
        solution = client_data.get('solution')
        slncache = client_data.get('slncache')
        buildenv = client_data.get('env', {})
        extraflags = client_data.get('extra_flags')
    else:
        if not client_data:
            raise Exception("No client data provided by Vim host!")
        solution = client_data.get('g:vimcrosoft_current_sln')
        slncache = client_data.get('g:vimcrosoft_current_sln_cache')
        buildenv = _build_env_from_vim(client_data)
        extraflags = client_data.get('g:vimcrosoft_extra_clang_args')

    extraflags = _expand_extra_flags_with_solution_extra_flags(solution, extraflags)

    flags = None

    if language == 'cfamily':
        try:
            flags = _build_cflags(filename, solution,
                                  buildenv=buildenv, slncache=slncache,
                                  extraflags=extraflags)
        except Exception as exc:
            if from_cli:
                raise
            flags = {'error': str(exc)}
    else:
        flags = {'error': f"Unknown language: {language}"}

    if _dump_debug_file:
        debug_filename = os.path.join(
                os.path.dirname(solution), '.vimcrosoft', 'debug_flags.txt')
        _do_dump_debug_file(kwargs, flags, debug_filename)

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
    parser.add_argument('--no-auto-env',
                        action='store_true',
                        help="Don't read configuration information from Vimcrosoft cache")
    parser.add_argument('-p', '--property',
                        action="append",
                        help="Specifies a build property")
    parser.add_argument('-c', '--cache',
                        help="The solution cache to use")
    parser.add_argument('--cmdline',
                        action='store_true',
                        help="Output flags in a command-line form")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Show debugging information")
    args = parser.parse_args()
    setup_logging(args.verbose)

    lang = _get_language(args.filename)
    logger.debug(f"Got language {lang} for {args.filename}")

    build_env = {}
    slncache = args.cache
    if not args.no_auto_env:
        load_vimcrosoft_auto_env(args.solution, build_env)
        if not slncache:
            slncache = find_vimcrosoft_slncache(args.solution)
    if args.property:
        for p in args.property:
            pname, pval = p.split('=', 1)
            build_env[pname] = pval
    logger.debug(f"Got build environment: {build_env}")
    client_data = {'solution': args.solution,
                   'slncache': slncache,
                   'env': build_env}

    params = {'from_cli': True,
              'language': lang,
              'filename': args.filename,
              'client_data': client_data
              }
    flags = Settings(**params)
    if args.cmdline:
        import shlex
        if hasattr(shlex, 'join'):
            joinargs = shlex.join
        else:
            joinargs = lambda a: ' '.join(a)

        with open('clang_ycm_args.rsp', 'w', encoding='utf8') as fp:
            fp.write("%s -fsyntax-only \"%s\"" % (
                joinargs(sanitizeargs(flags['flags'])),
                args.filename.replace('\\', '/')
                ))
        with open('clang_ycm_invoke.cmd', 'w', encoding='utf8') as fp:
            fp.write("\"c:\\Program Files\\LLVM\\bin\\clang++.exe\" @clang_ycm_args.rsp > clang_ycm_invoke.log 2>&1")

        logger.info("Command line written to: clang_ycm_invoke.cmd")
    else:
        logger.info("Flags:")
        import pprint
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(flags)


def sanitizeargs(args):
    for arg in args:
        if ' ' in arg:
            yield '"%s"' % arg
        else:
            yield arg


if __name__ == '__main__':
    main()
