*vimcrosoft.txt*  Work with Visual Studio solutions in Vim


$$\    $$\$$$$$$\$$\      $$\ $$$$$$\ $$$$$$$\  $$$$$$\  $$$$$$\  $$$$$$\ $$$$$$$$\$$$$$$$$\ 
$$ |   $$ \_$$  _$$$\    $$$ $$  __$$\$$  __$$\$$  __$$\$$  __$$\$$  __$$\$$  _____\__$$  __|
$$ |   $$ | $$ | $$$$\  $$$$ $$ /  \__$$ |  $$ $$ /  $$ $$ /  \__$$ /  $$ $$ |        $$ |   
\$$\  $$  | $$ | $$\$$\$$ $$ $$ |     $$$$$$$  $$ |  $$ \$$$$$$\ $$ |  $$ $$$$$\      $$ |   
 \$$\$$  /  $$ | $$ \$$$  $$ $$ |     $$  __$$<$$ |  $$ |\____$$\$$ |  $$ $$  __|     $$ |   
  \$$$  /   $$ | $$ |\$  /$$ $$ |  $$\$$ |  $$ $$ |  $$ $$\   $$ $$ |  $$ $$ |        $$ |   
   \$  /  $$$$$$\$$ | \_/ $$ \$$$$$$  $$ |  $$ |$$$$$$  \$$$$$$  |$$$$$$  $$ |        $$ |   
    \_/   \______\__|     \__|\______/\__|  \__|\______/ \______/ \______/\__|        \__|   


                                   VIM-CROSOFT

                                                                  *vimcrosoft*

==============================================================================
Configuration                                       *vimcrosoft-configuration*

                                                          *g:vimcrosoft_trace*
g:vimcrosoft_trace
                        Enables debugging information.
                        Default: `0`

                                                  *g:vimcrosoft_auto_find_sln*
g:vimcrosoft_auto_find_sln
                        Try and find a solution for the current working
                        directory on Vim startup. This effectively executes
                        |:VimcrosoftAutoFindSln| upon startup.
                        Default: `0`

                                                     *g:vimcrosoft_sln_finder*
g:vimcrosoft_sln_finder
                        The name of a function to call to find a solution file
                        from a given current path. If not set, Vimcrosoft will
                        use its own default finder, which just walks up the
                        directory tree until it finds any `*.sln` files.
                        Default: `""`

                                                   *g:vimcrosoft_msbuild_path*
g:vimcrosoft_msbuild_path
                        By default, Vimcrosoft automatically finds where
                        MSBuild is installed. If that fails, you can specify
                        the path to the MSBuild executable directly.
                        Default: `""`

                                                   *g:vimcrosoft_make_command*
g:vimcrosoft_make_command
                        The command to run when starting builds. If empty,
                        Vimcrosoft will use |:make|, unless the vim-dispatch
                        plugin is detected, in which case it will use |:Make|.
                        If the option is not empty, it will use whatever you
                        specified.
                        Default: `""`

==============================================================================
Commands                                                 *vimcrosoft-commands*

                                                *vimcrosoft-solution-commands*
Here's a list of solution-related commands:

                                                      *:VimcrosoftAutoFindSln*
:VimcrosoftAutoFindSln
                        Finds a solution file (`*.sln`) in the current working
                        directory, or any of its parent directories, and sets
                        it as the current solution file (see 
                        |:VimcrosoftSetSln|). If any solution files are found,
                        the first one is used.

                                                           *:VimcrosoftSetSln*
:VimcrosoftSetSln <file>
                        Sets the currently active solution file. All
                        vim-crosoft commands will relate to this solution.

                                                         *:VimcrosoftUnsetSln*
:VimcrosoftUnsetSln
                        Unsets the currently active solution file.

                                                *:VimcrosoftSetConfigPlatform*
:VimcrosoftSetConfigPlatform <configplatform>
                        Sets the currently active configuration and platform
                        for the active solution. The argument is a combo of
                        configuration and platform, in the form of
                        `Configuration|Platform`.

                                                         *:VimcrosoftBuildSln*
:VimcrosoftBuildSln
                        Starts a build on the current solution, using the
                        current configuration and platform.

                                                       *:VimcrosoftRebuildSln*
:VimcrosoftRebuildSln
                        Rebuilds the current solution, using the current
                        configuration and platform.

                                                         *:VimcrosoftCleanSln*
:VimcrosoftCleanSln
                        Cleans the current solution for the current
                        configuration and platform.


                                                 *vimcrosoft-project-commands*
Here are some project-related commands:

                                                     *:VimcrosoftBuildProject*
:VimcrosoftBuildProject
                        Builds the active project for the current
                        configuration and platform. MSBuild will typically
                        build all its dependencies first.

                                                 *:VimcrosoftBuildProjectOnly*
:VimcrosoftBuildProjectOnly
                        Builds the active project for the current
                        configuration and platform, but skips building any
                        dependencies.

                                                   *:VimcrosoftRebuildProject*
:VimcrosoftRebuildProject
                        Rebuilds the active project for the current
                        configuration and platform.

                                                     *:VimcrosoftCleanProject*
:VimcrosoftCleanProject
                        Cleans the active project for the current
                        configuration and platform.


                                          *vimcrosoft-active-project-commands*
Vimcrosoft lets you specify an "active project" that makes it quicker to
build/clean/etc.

                                                 *:VimcrosoftSetActiveProject*
:VimcrosoftSetActiveProject
                        Sets the active project for the current solution. This
                        enables a few "shortcut" commands that operate on it
                        directly.

                                               *:VimcrosoftBuildActiveProject*
:VimcrosoftBuildActiveProject
                        Builds the active project for the current
                        configuration and platform. MSBuild will typically
                        build all its dependencies first.

                                           *:VimcrosoftBuildActiveProjectOnly*
:VimcrosoftBuildActiveProjectOnly
                        Builds the active project for the current
                        configuration and platform, but skips building any
                        dependencies.

                                             *:VimcrosoftRebuildActiveProject*
:VimcrosoftRebuildActiveProject
                        Rebuilds the active project for the current
                        configuration and platform.

                                               *:VimcrosoftCleanActiveProject*
:VimcrosoftCleanActiveProject
                        Cleans the active project for the current
                        configuration and platform.


==============================================================================
Statusline                                             *vimcrosoft-statusline*

You can show some vimcrosoft-related information in your 'statusline' by
calling the `vimcrosoft#statusline()` function.


" vim:tw=78:et:ft=help:norl:
