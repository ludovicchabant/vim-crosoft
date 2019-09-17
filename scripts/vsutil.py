import copy
import logging
import os.path
import pickle
import re
import xml.etree.ElementTree as etree


# Known VS project types.
PROJ_TYPE_FOLDER = '2150E333-8FDC-42A3-9474-1A3956D46DE8'
PROJ_TYPE_NMAKE = '8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942'
PROJ_TYPE_CSHARP = 'FAE04EC0-301F-11D3-BF4B-00C04F79EFBC'

PROJ_TYPE_NAMES = {
    PROJ_TYPE_FOLDER: 'folder',
    PROJ_TYPE_NMAKE: 'nmake',
    PROJ_TYPE_CSHARP: 'csharp'
}

# Known VS item types.
ITEM_TYPE_CPP_SRC = 'ClCompile'
ITEM_TYPE_CPP_HDR = 'ClInclude'

ITEM_TYPE_CS_REF = 'Reference'
ITEM_TYPE_CS_PROJREF = 'ProjectReference'
ITEM_TYPE_CS_SRC = 'Compile'

ITEM_TYPE_NONE = 'None'

ITEM_TYPE_SOURCE_FILES = (ITEM_TYPE_CPP_SRC, ITEM_TYPE_CPP_HDR,
                          ITEM_TYPE_CS_SRC)


# Known VS properties.
PROP_CONFIGURATION_TYPE = 'ConfigurationType'
PROP_NMAKE_PREPROCESSOR_DEFINITIONS = 'NMakePreprocessorDefinitions'
PROP_NMAKE_INCLUDE_SEARCH_PATH = 'NMakeIncludeSearchPath'


logger = logging.getLogger(__name__)


def _strip_ns(tag):
    """ Remove the XML namespace from a tag name. """
    if tag[0] == '{':
        i = tag.index('}')
        return tag[i+1:]
    return tag


re_msbuild_var = re.compile(r'\$\((?P<var>[\w\d_]+)\)')


def _resolve_value(val, env):
    """ Expands MSBuild property values given a build environment. """
    def _repl_vars(m):
        varname = m.group('var')
        varval = env.get(varname, '')
        return varval

    if not val:
        return val
    return re_msbuild_var.sub(_repl_vars, val)


def _evaluate_condition(cond, env):
    """ Expands MSBuild property values in a condition and evaluates it. """
    left, right = _resolve_value(cond, env).split('==')
    return left == right


class VSBaseGroup:
    """ Base class for VS project stuff that has conditional stuff inside.

        For instance, a property group called 'Blah' might have some common
        (always valid) stuff, but a bunch of other stuff that should only
        be considered when the solution configuration is Debug, Release, or
        whatever else. In that case, each 'conditional' (i.e. values for Debug,
        values for Release, etc.) is listed and tracked separately until
        we are asked to 'resolve' ourselves based on a given build environment.
    """
    def __init__(self, label):
        self.label = label
        self.conditionals = {}

    def get_conditional(self, condition):
        """ Adds a conditional sub-group. """
        return self.conditionals.get(condition)

    def get_or_create_conditional(self, condition):
        """ Gets or creates a new conditional sub-group. """
        c = self.get_conditional(condition)
        if not c:
            c = self.__class__(self.label)
            self.conditionals[condition] = c
        return c

    def resolve(self, env):
        """ Resolves this group by evaluating each conditional sub-group
            based on the given build environment. Returns a 'flattened'
            version of ourselves.
        """
        c = self.__class__(self.label)
        c._collapse_child(self, env)

        for cond, child in self.conditionals.items():
            if _evaluate_condition(cond, env):
                c._collapse_child(child, env)

        return c


class VSProjectItem:
    """ A VS project item, like a source code file. """
    def __init__(self, include, itemtype=None):
        self.include = include
        self.itemtype = itemtype
        self.metadata = {}

    def resolve(self, env):
        c = VSProjectItem(_resolve_value(self.include), self.itemtype)
        c.metadata = {k: _resolve_value(v, env)
                      for k, v in self.metadata.items()}
        return c

    def __str__(self):
        return "(%s)%s" % (self.itemtype, self.include)


class VSProjectItemGroup(VSBaseGroup):
    """ A VS project item group, like a list of source code files,
        or a list of resources.
    """
    def __init__(self, label):
        super().__init__(label)
        self.items = []

    def get_source_items(self):
        for i in self.items:
            if i.itemtype in ITEM_TYPE_SOURCE_FILES:
                yield i

    def _collapse_child(self, child, env):
        self.items += [i.resolve(env) for i in child.items]


class VSProjectProperty:
    """ A VS project property, like an include path or compiler flag. """
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def resolve(self, env):
        c = VSProjectProperty(self.name, _resolve_value(self.value, env))
        return c

    def __str__(self):
        return "%s=%s" % (self.name, self.value)


class VSProjectPropertyGroup(VSBaseGroup):
    """ A VS project property group, such as compiler macros or flags. """
    def __init__(self, label):
        super().__init__(label)
        self.properties = []

    def get(self, propname):
        try:
            return self[propname]
        except IndexError:
            return None

    def __getitem__(self, propname):
        for p in self.properties:
            if p.name == propname:
                return p.value
        raise IndexError()

    def _collapse_child(self, child, env):
        self.properties += [p.resolve(env) for p in child.properties]


class VSProject:
    """ A VS project. """
    def __init__(self, projtype, name, path, guid):
        self.type = projtype
        self.name = name
        self.path = path
        self.guid = guid
        self._itemgroups = None
        self._propgroups = None
        self._sln = None

    @property
    def is_folder(self):
        """ Returns whether this project is actually just a solution
            folder, used as a container for other projects.
        """
        return self.type == PROJ_TYPE_FOLDER

    @property
    def abspath(self):
        abspath = self.path
        if self._sln and self._sln.path:
            abspath = os.path.join(self._sln.dirpath, self.path)
        return abspath

    @property
    def absdirpath(self):
        return os.path.dirname(self.abspath)

    @property
    def itemgroups(self):
        self._ensure_loaded()
        return self._itemgroups.values()

    @property
    def propertygroups(self):
        self._ensure_loaded()
        return self._propgroups.values()

    def itemgroup(self, label, resolved_with=None):
        self._ensure_loaded()
        ig = self._itemgroups.get(label)
        if resolved_with is not None and ig is not None:
            logger.debug("Resolving item group '%s'." % ig.label)
            ig = ig.resolve(resolved_with)
        return ig

    def defaultitemgroup(self, resolved_with=None):
        return self.itemgroup(None, resolved_with=resolved_with)

    def propertygroup(self, label, resolved_with=None):
        self._ensure_loaded()
        pg = self._propgroups.get(label)
        if resolved_with is not None and pg is not None:
            logger.debug("Resolving property group '%s'." % pg.label)
            pg = pg.resolve(resolved_with)
        return pg

    def defaultpropertygroup(self, resolved_with=None):
        return self.propertygroup(None, resolved_with=resolved_with)

    def get_abs_item_include(self, item):
        return os.path.abspath(os.path.join(self.absdirpath, item.include))

    def resolve(self, env):
        self._ensure_loaded()

        propgroups = list(self._propgroups)
        itemgroups = list(self._itemgroups)
        self._propgroups[:] = []
        self._itemgroups[:] = []

        for pg in propgroups:
            rpg = pg.resolve(env)
            self._propgroups.append(rpg)

        for ig in itemgroups:
            rig = ig.resolve(env)
            self._itemgroups.append(rig)

    def _ensure_loaded(self):
        if self._itemgroups is None or self._propgroups is None:
            self._load()

    def _load(self):
        if not self.path:
            raise Exception("The current project has no path.")
        if self.is_folder:
            logger.debug(f"Skipping folder project {self.name}")
            self._itemgroups = {}
            self._propgroups = {}
            return

        ns = {'ms': 'http://schemas.microsoft.com/developer/msbuild/2003'}

        abspath = self.abspath
        logger.debug(f"Loading project {self.name} ({self.path}) from: {abspath}")
        tree = etree.parse(abspath)
        root = tree.getroot()
        if _strip_ns(root.tag) != 'Project':
            raise Exception(f"Expected root node 'Project', got '{root.tag}'")

        self._itemgroups = {}
        for itemgroupnode in root.iterfind('ms:ItemGroup', ns):
            label = itemgroupnode.attrib.get('Label')
            itemgroup = self._itemgroups.get(label)
            if not itemgroup:
                itemgroup = VSProjectItemGroup(label)
                self._itemgroups[label] = itemgroup
                logger.debug(f"Adding itemgroup '{label}'")

            condition = itemgroupnode.attrib.get('Condition')
            if condition:
                itemgroup = itemgroup.get_or_create_conditional(condition)

            for itemnode in itemgroupnode:
                incval = itemnode.attrib.get('Include')
                item = VSProjectItem(incval, _strip_ns(itemnode.tag))
                itemgroup.items.append(item)
                for metanode in itemnode:
                    item.metadata[_strip_ns(metanode.tag)] = metanode.text

        self._propgroups = {}
        for propgroupnode in root.iterfind('ms:PropertyGroup', ns):
            label = propgroupnode.attrib.get('Label')
            propgroup = self._propgroups.get(label)
            if not propgroup:
                propgroup = VSProjectPropertyGroup(label)
                self._propgroups[label] = propgroup
                logger.debug(f"Adding propertygroup '{label}'")

            condition = propgroupnode.attrib.get('Condition')
            if condition:
                propgroup = propgroup.get_or_create_conditional(condition)

            for propnode in propgroupnode:
                propgroup.properties.append(VSProjectProperty(
                    _strip_ns(propnode.tag),
                    propnode.text))


class MissingVSProjectError(Exception):
    pass


class VSGlobalSectionEntry:
    """ An entry in a VS solution's global section. """
    def __init__(self, name, value):
        self.name = name
        self.value = value


class VSGlobalSection:
    """ A global section in a VS solution. """
    def __init__(self, name):
        self.name = name
        self.entries = []


class VSSolution:
    """ A VS solution. """
    def __init__(self, path=None):
        self.path = path
        self.projects = []
        self.sections = []

    @property
    def dirpath(self):
        return os.path.dirname(self.path)

    def find_project_by_name(self, name, missing_ok=True):
        for p in self.projects:
            if p.name == name:
                return p
        if missing_ok:
            return None
        return MissingVSProjectError(f"Can't find project with name: {name}")

    def find_project_by_path(self, path, missing_ok=True):
        for p in self.projects:
            if p.abspath == path:
                return p
        if missing_ok:
            return None
        raise MissingVSProjectError(f"Can't find project with path: {path}")

    def find_project_by_guid(self, guid, missing_ok=True):
        for p in self.projects:
            if p.guid == guid:
                return p
        if missing_ok:
            return None
        raise MissingVSProjectError(f"Can't find project for guid: {guid}")

    def globalsection(self, name):
        for sec in self.sections:
            if sec.name == name:
                return sec
        return None

    def find_project_configuration(self, proj_guid, sln_config):
        configs = self.globalsection('ProjectConfigurationPlatforms')
        if not configs:
            return None

        entry_name = '{%s}.%s.Build.0' % (proj_guid, sln_config)
        for entry in configs.entries:
            if entry.name == entry_name:
                return entry.value
        return None


_re_sln_project_decl_start = re.compile(
    r'^Project\("\{(?P<type>[A-Z0-9\-]+)\}"\) \= '
    r'"(?P<name>[^"]+)", "(?P<path>[^"]+)", "\{(?P<guid>[A-Z0-9\-]+)\}"$')
_re_sln_project_decl_end = re.compile(
    r'^EndProject$')

_re_sln_global_start = re.compile(r'^Global$')
_re_sln_global_end = re.compile(r'^EndGlobal$')
_re_sln_global_section_start = re.compile(
    r'^\s*GlobalSection\((?P<name>\w+)\) \= (?P<step>\w+)$')
_re_sln_global_section_end = re.compile(r'^\s*EndGlobalSection$')


def parse_sln_file(slnpath):
    """ Parses a solution file, returns a solution object.
        The projects are not loaded (they will be lazily loaded upon
        first access to their items/properties/etc.).
    """
    logging.debug(f"Reading {slnpath}")
    slnobj = VSSolution(slnpath)
    with open(slnpath, 'r') as fp:
        lines = fp.readlines()
        _parse_sln_file_text(slnobj, lines)
    return slnobj


def _parse_sln_file_text(slnobj, lines):
    until = None
    in_global = False
    in_global_section = None

    for i, line in enumerate(lines):
        if until:
            # We need to parse something until a given token, so let's
            # do that and ignore everything else.
            m = until.search(line)
            if m:
                until = None
            continue

        if in_global:
            # We're in the 'global' part of the solution. It should contain
            # a bunch of 'global sections' that we need to parse individually.
            if in_global_section:
                # Keep parsing the current section until we reach the end.
                m = _re_sln_global_section_end.search(line)
                if m:
                    in_global_section = None
                    continue

                ename, evalue = line.strip().split('=')
                in_global_section.entries.append(VSGlobalSectionEntry(
                    ename.strip(),
                    evalue.strip()))
                continue

            m = _re_sln_global_section_start.search(line)
            if m:
                # Found the start of a new section.
                in_global_section = VSGlobalSection(m.group('name'))
                logging.debug(f"   Adding global section {in_global_section.name}")
                slnobj.sections.append(in_global_section)
                continue

            m = _re_sln_global_end.search(line)
            if m:
                # Found the end of the 'global' part.
                in_global = False
                continue

        # We're not in a specific part of the solution, so do high-level
        # parsing. First, ignore root-level comments.
        if not line or line[0] == '#':
            continue

        m = _re_sln_project_decl_start.search(line)
        if m:
            # Found the start of a project declaration.
            try:
                p = VSProject(
                    m.group('type'), m.group('name'), m.group('path'),
                    m.group('guid'))
            except:
                raise Exception(f"Error line {i}: unexpected project syntax.")
            logging.debug(f"  Adding project {p.name}")
            slnobj.projects.append(p)
            p._sln = slnobj

            until = _re_sln_project_decl_end
            continue

        m = _re_sln_global_start.search(line)
        if m:
            # Reached the start of the 'global' part, where global sections
            # are defined.
            in_global = True
            continue

        # Ignore the rest (like visual studio version flags).
        continue


class SolutionCache:
    """ A class that contains a VS solution object, along with pre-indexed
        lists of items. It's meant to be saved on disk.
    """
    VERSION = 3

    def __init__(self, slnobj):
        self.slnobj = slnobj
        self.index = None

    def build_cache(self):
        self.index = {}
        for proj in self.slnobj.projects:
            if proj.is_folder:
                continue
            itemgroup = proj.defaultitemgroup()
            if not itemgroup:
                continue

            item_cache = set()
            self.index[proj.abspath] = item_cache

            for item in itemgroup.get_source_items():
                item_path = proj.get_abs_item_include(item).lower()
                item_cache.add(item_path)

    def save(self, path):
        pathdir = os.path.dirname(path)
        if not os.path.exists(pathdir):
            os.makedirs(pathdir)
        with open(path, 'wb') as fp:
            pickle.dump(self, fp)

    @staticmethod
    def load_or_rebuild(slnpath, cachepath):
        if cachepath:
            res = _try_load_from_cache(slnpath, cachepath)
            if res is not None:
                return res

        slnobj = parse_sln_file(slnpath)
        cache = SolutionCache(slnobj)

        if cachepath:
            logger.debug(f"Regenerating cache: {cachepath}")
            cache.build_cache()
            cache.save(cachepath)

        return (cache, False)


def _try_load_from_cache(slnpath, cachepath):
    try:
        sln_dt = os.path.getmtime(slnpath)
        cache_dt = os.path.getmtime(cachepath)
    except OSError:
        logger.debug("Can't read solution or cache files.")
        return None

    # If the solution file is newer, bail out.
    if sln_dt >= cache_dt:
        logger.debug("Solution is newer than cache.")
        return None

    # Our cache is at least valid for the solution stuff. Some of our
    # projects might be out of date, but at least there can't be any
    # added or removed projects from the solution (otherwise the solution
    # file would have been touched). Let's load the cache.
    with open(cachepath, 'rb') as fp:
        cache = pickle.load(fp)

    # Check that the cache version is up-to-date with this code.
    loaded_ver = getattr(cache, 'VERSION')
    if loaded_ver != SolutionCache.VERSION:
        logger.debug(f"Cache was saved with older format: {cachepath}")
        return None

    slnobj = cache.slnobj

    # Check that none of the project files in the solution are newer
    # than this cache.
    proj_dts = []
    for p in slnobj.projects:
        if not p.is_folder:
            try:
                proj_dts.append(os.path.getmtime(p.abspath))
            except OSError:
                logger.debug(f"Found missing project: {p.abspath}")
                return None

    if all([cache_dt > pdt for pdt in proj_dts]):
        logger.debug(f"Cache is up to date: {cachepath}")
        return (cache, True)

    logger.debug("Cache has outdated projects.")
    return None
