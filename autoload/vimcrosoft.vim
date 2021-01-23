" vimcrosoft.vim - A wrapper for Visual Studio solutions

" Utilities {{{

let s:basedir = expand('<sfile>:p:h:h')

function! vimcrosoft#throw(message)
    throw "vimcrosoft: ".a:message
endfunction

function! vimcrosoft#error(message)
    let v:errmsg = "vimcrosoft: ".a:message
    echoerr v:errmsg
endfunction

function! vimcrosoft#warning(message)
    echohl WarningMsg
    echom "vimcrosoft: ".a:message
    echohl None
endfunction

function! vimcrosoft#trace(message)
    if g:vimcrosoft_trace
        echom "vimcrosoft: ".a:message
    endif
endfunction

function! vimcrosoft#ensure_msbuild_found() abort
    if !empty(g:vimcrosoft_msbuild_path)
        return 1
    endif

    let l:programfilesdir = get(environ(), 'ProgramFiles(x86)')
    let l:vswhere = l:programfilesdir.'\Microsoft Visual Studio\Installer\vswhere.exe'
    if !executable(l:vswhere)
        call vimcrosoft#error("Can't find `vswhere` -- you must set `g:vimcrosoft_msbuild_path` yourself.")
        return 0
    endif

    let l:vswhere_cmdline = '"'.l:vswhere.'" '.
                \'-prerelease -latest -products * '.
                \'-requires Microsoft.Component.MSBuild '.
                \'-property installationPath'
    call vimcrosoft#trace("Trying to find MSBuild, running: ".l:vswhere_cmdline)
    let l:installdirs = split(system(l:vswhere_cmdline), '\n')
    call vimcrosoft#trace("Got: ".string(l:installdirs))
    for installdir in l:installdirs
        let l:msbuild = installdir.'\MSBuild\Current\Bin\MSBuild.exe'
        if executable(l:msbuild)
            let g:vimcrosoft_msbuild_path = l:msbuild
            return 1
        endif
		let l:msbuild = installdir.'\MSBuild\15.0\Bin\MSBuild.exe'
		if executable(l:msbuild)
            let g:vimcrosoft_msbuild_path = l:msbuild
            return 1
        endif
    endfor

    call vimcrosoft#error("Couldn't find MSBuild anywhere in:\n".
                \string(l:installdirs))
    return 0
endfunction

function! vimcrosoft#get_msbuild_errorformat() abort
    " MSBuild error formats look like this:
    " Path\To\Source\Filename.cpp|53| error C2065: 'MyClass': undeclared identifier [Path\To\MyProject.vcxproj]
    return '%*[^\ ]\ %f\|%l\|\ %trror\ \D%n:\ %m\ [%o]'
                " \'\|\|\ %f\|%l\|\ %tarning\ \D%n:\ %m\ [%o]'
endfunction

" }}}

" Cache Files {{{

function! vimcrosoft#get_sln_cache_dir(...) abort
    if empty(g:vimcrosoft_current_sln)
        if a:0 && a:1
            call vimcrosoft#throw("No solution is currently set.")
        endif
        return ''
    endif
    let l:cache_dir = fnamemodify(g:vimcrosoft_current_sln, ':h')
    let l:cache_dir .= '\.vimcrosoft'
    return l:cache_dir
endfunction

function! vimcrosoft#get_sln_cache_file(filename) abort
    let l:cache_dir = vimcrosoft#get_sln_cache_dir()
    if empty(l:cache_dir)
        return ''
    else
        return l:cache_dir.'\'.a:filename
    endif
endfunction

" }}}

" Configuration Files {{{

let s:config_format = 2

function! vimcrosoft#save_config() abort
    if empty(g:vimcrosoft_current_sln)
        return
    endif

    call vimcrosoft#trace("Saving config for: ".g:vimcrosoft_current_sln)
    let l:lines = [
                \'format='.string(s:config_format),
                \g:vimcrosoft_current_sln,
                \g:vimcrosoft_current_config,
                \g:vimcrosoft_current_platform,
                \g:vimcrosoft_active_project]
    let l:configfile = vimcrosoft#get_sln_cache_file('config.txt')
    call writefile(l:lines, l:configfile)
endfunction

function! vimcrosoft#load_config() abort
    if empty(g:vimcrosoft_current_sln)
        return
    endif

    let l:configfile = vimcrosoft#get_sln_cache_file('config.txt')
    if !filereadable(l:configfile)
        return
    endif

    let l:lines = readfile(l:configfile)
    let l:format_line = l:lines[0]
    if l:format_line == 'format='.string(s:config_format)
        let g:vimcrosoft_current_sln = l:lines[1]
        let g:vimcrosoft_current_config = l:lines[2]
        let g:vimcrosoft_current_platform = l:lines[3]
        let g:vimcrosoft_active_project = l:lines[4]
    else
        call vimcrosoft#warning("Solution configuration format has changed ".
                    \"since you last opened this solution in Vim. ".
                    \"You previous configuration/platform has NOT been ".
                    \"restored.")
    endif
endfunction

" }}}

" {{{ Scripts

let s:scriptsdir = s:basedir.'\scripts'

function! vimcrosoft#get_script_path(scriptname) abort
    return s:scriptsdir.'\'.a:scriptname
endfunction

function! vimcrosoft#exec_script_job(scriptname, ...) abort
    let l:scriptpath = vimcrosoft#get_script_path(a:scriptname)
    let l:cmd = ['python', l:scriptpath] + a:000
    return job_start(l:cmd)
endfunction

let s:scriptsdir_added_to_sys = 0
let s:scripts_imported = []

function! s:install_scriptsdir() abort
    if !s:scriptsdir_added_to_sys
        execute 'python3 import sys'
        execute 'python3 sys.path.append("'.escape(s:scriptsdir, "\\").'")'
        execute 'python3 import vimutil'
        let s:scriptsdir_added_to_sys = 1
    endif
endfunction

function! vimcrosoft#exec_script_now(scriptname, ...) abort
    if g:vimcrosoft_use_external_python
        let l:cmd = 'python '.shellescape(vimcrosoft#get_script_path(a:scriptname.'.py'))
        " TODO: shellescape arguments?
        let l:cmd .= ' '.join(a:000, " ")
        let l:output = system(l:cmd)
    else
        call s:install_scriptsdir()
        if index(s:scripts_imported, a:scriptname) < 0
            execute 'python3 import '.a:scriptname
            call add(s:scripts_imported, a:scriptname)
        endif
        let l:line = 'vimutil.runscript('.a:scriptname.'.main'
        if a:0 > 0
            let l:args = copy(a:000)
            call map(l:args, {idx, val -> escape(val, '\"')})
            let l:line .= ', "'.join(l:args, '", "').'"'
        endif
        let l:line .= ')'
        call vimcrosoft#trace("Executing: ".l:line)
        let l:output = py3eval(l:line)
    endif
    return l:output
endfunction

" }}}

" Module Management {{{

let s:modulesdir = s:basedir.'\autoload\vimcrosoft'
let s:modules = glob(s:modulesdir.'\*.vim', 0, 1)

function! vimcrosoft#call_modules(funcname, ...) abort
    for modpath in s:modules
        let l:modname = fnamemodify(modpath, ':t:r')
        let l:fullfuncname = 'vimcrosoft#'.l:modname.'#'.a:funcname
        if exists("*".l:fullfuncname)
            call vimcrosoft#trace("Module ".l:modname.": calling ".a:funcname)
            call call(l:fullfuncname, a:000)
        else
            call vimcrosoft#trace("Skipping ".l:fullfuncname.": doesn't exist.")
        endif
    endfor
endfunction

" }}}

" Solution Management {{{

function! vimcrosoft#set_sln(slnpath, ...) abort
    let g:vimcrosoft_current_sln = a:slnpath

    let l:sln_was_set = !empty(a:slnpath)
    if l:sln_was_set
        let g:vimcrosoft_current_sln_cache = vimcrosoft#get_sln_cache_file("slncache.bin")
        call vimcrosoft#call_modules('on_sln_changed', a:slnpath)
    else
        let g:vimcrosoft_current_sln_cache = ''
        call vimcrosoft#call_modules('on_sln_cleared')
    endif

    let l:silent = a:0 && a:1
    if !l:silent
        call vimcrosoft#save_config()

        if l:sln_was_set
            echom "Current solution: ".a:slnpath
        else
            echom "No current solution anymore"
        endif
    endif
endfunction

function! vimcrosoft#auto_find_sln(...) abort
    let l:path = getcwd()
    try
        let l:slnpath = vimcrosoft#find_sln(l:path)
    catch /^vimcrosoft:/
        let l:slnpath = ''
    endtry
    let l:silent = a:0 && a:1
    call vimcrosoft#set_sln(l:slnpath, l:silent)
endfunction

function! vimcrosoft#find_sln(curpath) abort
    if g:vimcrosoft_sln_finder != ''
        return call(g:vimcrosoft_sln_finder, [a:curpath])
    endif
    return vimcrosoft#default_sln_finder(a:curpath)
endfunction

function! vimcrosoft#default_sln_finder(path) abort
    let l:cur = a:path
    let l:prev = ""
    while l:cur != l:prev
        let l:slnfiles = globpath(l:cur, '*.sln', 0, 1)
        if !empty(l:slnfiles)
            call vimcrosoft#trace("Found solution file: ".l:slnfiles[0])
            return l:slnfiles[0]
        endif
        let l:prev = l:cur
        let l:cur = fnamemodify(l:cur, ':h')
    endwhile
    call vimcrosoft#throw("No solution file found.")
endfunction

function! vimcrosoft#set_active_project(projname, ...) abort
    " Strip trailing spaces in the project name.
    let l:projname = substitute(a:projname, '\v\s+$', '', 'g')

    let g:vimcrosoft_active_project = l:projname
    call vimcrosoft#call_modules('on_active_project_changed', l:projname)

    let l:silent = a:0 && a:1
    if !l:silent
        call vimcrosoft#save_config()
        echom "Active project changed"
    endif
endfunction

function! vimcrosoft#build_sln(target) abort
    if g:vimcrosoft_save_all_on_build
        wall
    endif

    let l:args = []
    if !empty(a:target)
        call add(l:args, '/t:'.a:target)
    endif
    call vimcrosoft#run_make(l:args)
endfunction

function! vimcrosoft#build_project(projname, target, only) abort
    if g:vimcrosoft_save_all_on_build
        wall
    endif

    let l:projname = !empty(a:projname) ? a:projname : g:vimcrosoft_active_project
    if empty(l:projname)
        call vimcrosoft#error("No project name given, and no active project set.")
        return
    endif

    " Strip trailing spaces in the project name.
    let l:projname = substitute(l:projname, '\v\s+$', '', 'g')
    let l:target = '/t:'.tr(l:projname, '.', '_')
    if !empty(a:target)
        let l:target .= ':'.a:target
    endif

    let l:args = []
    call add(l:args, l:target)
    if a:only
        call add(l:args, '/p:BuildProjectReferences=false')
    endif
    call vimcrosoft#run_make(l:args)
endfunction

function! vimcrosoft#run_make(customargs) abort
    if !vimcrosoft#ensure_msbuild_found()
        return
    endif

    " Add some common arguments for MSBuild.
    let l:fullargs = copy(a:customargs)
    call add(l:fullargs, '"/p:Configuration='.g:vimcrosoft_current_config.'"')
    call add(l:fullargs, '"/p:Platform='.g:vimcrosoft_current_platform.'"')
    " Add the solution file itself.
    call add(l:fullargs, '"'.g:vimcrosoft_current_sln.'"')

    " Setup the backdoor args list for our compiler to pick-up, and run
    " the make process.
    let g:vimcrosoft_temp_compiler_args__ = l:fullargs
    compiler vimcrosoftsln
    if !empty(g:vimcrosoft_make_command)
        execute g:vimcrosoft_make_command
    elseif exists(":Make")  " Support for vim-dispatch.
        Make
    else
        make
    endif
endfunction

function! vimcrosoft#set_config_platform(configplatform)
    let l:bits = split(substitute(a:configplatform, '\\ ', ' ', 'g'), '|')
    if len(l:bits) != 2
        call vimcrosoft#throw("Expected a value of the form: Config|Platform")
    endif

    let g:vimcrosoft_current_config = l:bits[0]
    let g:vimcrosoft_current_platform = l:bits[1]
    call vimcrosoft#call_modules('on_config_platform_changed', 
                \g:vimcrosoft_current_config, g:vimcrosoft_current_platform)

    call vimcrosoft#save_config()
endfunction

function! vimcrosoft#get_sln_project_names() abort
    if empty(g:vimcrosoft_current_sln)
        return []
    endif
    let l:output = vimcrosoft#exec_script_now("list_sln_projects",
                \g:vimcrosoft_current_sln,
                \'-c', g:vimcrosoft_current_sln_cache,
                \'--full-names')
    return split(l:output, "\n")
endfunction

function! vimcrosoft#get_sln_config_platforms() abort
    if empty(g:vimcrosoft_current_sln)
        return []
    endif
    let l:output = vimcrosoft#exec_script_now("list_sln_configs",
                \g:vimcrosoft_current_sln,
                \'-c', g:vimcrosoft_current_sln_cache)
    return split(l:output, "\n")
endfunction

" }}}

" {{{ Commands Auto-completion

function! vimcrosoft#complete_current_sln_projects(ArgLead, CmdLine, CursorPos)
    let l:proj_names = vimcrosoft#get_sln_project_names()
    let l:argpat = '^'.substitute(a:ArgLead, '\', '', 'g')
    let l:projnames = filter(l:proj_names,
                \{idx, val -> val =~? l:argpat})
    return l:projnames
endfunction

function! vimcrosoft#complete_current_sln_config_platforms(ArgLead, CmdLine, CursorPos)
    let l:argpat = '^'.substitute(a:ArgLead, '\', '', 'g')
    let l:cfgplats = vimcrosoft#get_sln_config_platforms()
    let l:cfgplats_filtered = filter(l:cfgplats, {idx, val -> val =~? l:argpat})
    call map(l:cfgplats_filtered, {idx, val -> escape(val, ' ')})
    return l:cfgplats_filtered
endfunction

" }}}

" {{{ Statusline Functions

function! vimcrosoft#statusline(...)
    if empty(g:vimcrosoft_current_sln)
        return ''
    endif

    let l:line = fnamemodify(g:vimcrosoft_current_sln, ':t')
    if !empty(g:vimcrosoft_active_project)
        let l:line .= '('.g:vimcrosoft_active_project.')'
    endif
    let l:line .= ' ['.
                \g:vimcrosoft_current_config.'|'.
                \g:vimcrosoft_current_platform.']'
    return l:line
endfunction

" }}}

" {{{ Initialization

function! vimcrosoft#init() abort
    call vimcrosoft#trace("Loading modules...")
    for modpath in s:modules
        execute 'source '.fnameescape(modpath)
    endfor

    call vimcrosoft#call_modules('init')

    if g:vimcrosoft_auto_find_sln
        call vimcrosoft#auto_find_sln(1)
        call vimcrosoft#load_config()
    endif
endfunction

" }}}
