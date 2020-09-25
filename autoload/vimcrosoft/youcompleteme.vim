
let g:vimcrosoft_extra_clang_args = get(g:, 'vimcrosoft_extra_clang_args', [])

function! vimcrosoft#youcompleteme#init() abort
endfunction

function! vimcrosoft#youcompleteme#on_sln_changed(slnpath) abort
    let g:ycm_global_ycm_extra_conf = vimcrosoft#get_script_path('ycm_extra_conf.py')
    let g:ycm_extra_conf_vim_data = [
                \'g:vimcrosoft_current_sln',
                \'g:vimcrosoft_current_sln_cache',
                \'g:vimcrosoft_current_config',
                \'g:vimcrosoft_current_platform',
				\'g:vimcrosoft_extra_clang_args'
                \]
endfunction

function! vimcrosoft#youcompleteme#on_sln_cleared() abort
    let g:ycm_global_ycm_extra_conf = ''
    let g:ycm_extra_conf_vim_data = []
endfunction

function! vimcrosoft#youcompleteme#on_config_platform_changed(config, platform) abort
    if exists(":YcmCompleter")
        YcmCompleter ClearCompilationFlagCache 
    endif
endfunction
