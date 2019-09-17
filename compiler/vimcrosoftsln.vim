" Compiler file for Visual Studio
" Compiler: Visual Studio
" Maintainer: Ludovic Chabant <https://ludovic.chabant.com>

if exists("current_compiler")
    finish
endif
let current_compiler = "vimcrosoftsln"

let s:keepcpo = &cpo

let s:prgargs = ''
if !empty(g:vimcrosoft_temp_compiler_args__)
    let s:tmpargs = map(
                \copy(g:vimcrosoft_temp_compiler_args__),
                \{idx, val -> escape(val, ' \"')})
    let s:prgargs = '\ '.join(s:tmpargs, '\ ')
endif

let s:prgcmdline = fnameescape('"'.g:vimcrosoft_msbuild_path.'"').s:prgargs
call vimcrosoft#trace("Setting makeprg to: ".s:prgcmdline)
execute "CompilerSet makeprg=".s:prgcmdline

CompilerSet errorformat&

let &cpo = s:keepcpo
unlet s:keepcpo

