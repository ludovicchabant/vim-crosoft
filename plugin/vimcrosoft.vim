" vimcrosoft.vim - A wrapper for Visual Studio solutions
" Maintainer:    Ludovic Chabant <https://ludovic.chabant.com>

" Globals {{{

if (&cp || get(g:, 'vimcrosoft_dont_load', 0))
    finish
endif

let g:vimcrosoft_trace = get(g:, 'vimcrosoft_trace', 0)

let g:vimcrosoft_current_sln = get(g:, 'vimcrosoft_current_sln', '')
let g:vimcrosoft_current_config = get(g:, 'vimcrosoft_current_config', '')
let g:vimcrosoft_current_platform = get(g:, 'vimcrosoft_current_platform', '')
let g:vimcrosoft_active_project = get(g:, 'vimcrosoft_active_project', '')

let g:vimcrosoft_auto_find_sln = get(g:, 'vimcrosoft_auto_find_sln', 0)
let g:vimcrosoft_sln_finder = get(g:, 'vimcrosoft_sln_finder', '')

let g:vimcrosoft_current_sln_cache = ''

let g:vimcrosoft_msbuild_path = get(g:, 'vimcrosoft_msbuild_path', '')
let g:vimcrosoft_use_external_python = get(g:, 'vimcrosoft_use_external_python', 0)
let g:vimcrosoft_make_command = get(g:, 'vimcrosoft_make_command', '')

" }}}

" Commands {{{

command! VimcrosoftAutoFindSln :call vimcrosoft#auto_find_sln()
command! -nargs=1 -complete=file VimcrosoftSetSln :call vimcrosoft#set_sln(<f-args>)
command! VimcrosoftUnsetSln :call vimcrosoft#set_sln("")

command! -nargs=1 
            \ -complete=customlist,vimcrosoft#complete_current_sln_config_platforms 
            \ VimcrosoftSetConfigPlatform 
            \ :call vimcrosoft#set_config_platform(<f-args>)

command! VimcrosoftBuildSln :call vimcrosoft#build_sln('Build')
command! VimcrosoftRebuildSln :call vimcrosoft#build_sln('Rebuild')
command! VimcrosoftCleanSln :call vimcrosoft#build_sln('Clean')

command! -nargs=1 
            \ -complete=customlist,vimcrosoft#complete_current_sln_projects 
            \ VimcrosoftSetActiveProject 
            \ :call vimcrosoft#set_active_project(<f-args>)
command! VimcrosoftBuildActiveProject :call vimcrosoft#build_project('', '', 0)
command! VimcrosoftBuildActiveProjectOnly :call vimcrosoft#build_project('', '', 1)
command! VimcrosoftRebuildActiveProject :call vimcrosoft#build_project('', 'Rebuild', 0)
command! VimcrosoftCleanActiveProject :call vimcrosoft#build_project('', 'Clean', 0)

command! -nargs=1 
            \ -complete=customlist,vimcrosoft#complete_current_sln_projects 
            \ VimcrosoftBuildProject 
            \ :call vimcrosoft#build_project(<f-args>, '', 0)
command! -nargs=1 
            \ -complete=customlist,vimcrosoft#complete_current_sln_projects 
            \ VimcrosoftBuildProjectOnly 
            \ :call vimcrosoft#build_project(<f-args>, '', 1)
command! -nargs=1 
            \ -complete=customlist,vimcrosoft#complete_current_sln_projects 
            \ VimcrosoftRebuildProject 
            \ :call vimcrosoft#build_project(<f-args>, 'Rebuild', 1)
command! -nargs=1 -complete=customlist,vimcrosoft#complete_current_sln_projects 
            \ VimcrosoftCleanProject 
            \ :call vimcrosoft#build_project(<f-args>, 'Clean', 1)

" }}}

" Initialization {{{

call vimcrosoft#init()

" }}}
