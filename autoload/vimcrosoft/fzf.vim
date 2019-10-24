
function! vimcrosoft#fzf#init() abort
endfunction

function! vimcrosoft#fzf#on_sln_changed(slnpath) abort
    let $FZF_DEFAULT_COMMAND = s:build_file_list_command(a:slnpath)
endfunction

function! vimcrosoft#fzf#on_sln_cleared() abort
    unlet $FZF_DEFAULT_COMMAND
endfunction

function! s:build_file_list_command(slnpath) abort
    let l:scriptpath = vimcrosoft#get_script_path('list_sln_files.py')
    let l:list_cache_path = vimcrosoft#get_sln_cache_file('fzffilelist.txt')
    return 'python '.shellescape(l:scriptpath).
                \' '.shellescape(a:slnpath).
                \' --cache '.shellescape(g:vimcrosoft_current_sln_cache).
                \' --list-cache '.shellescape(l:list_cache_path)
endfunction

