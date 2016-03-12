# cmake format

Can format your cmake files nicely so that they don't look like crap.

## Usage

~~~
usage: cmake_format.py [-h] [-i] [-o OUTFILE_PATH] [-c CONFIG_FILE]
                       infilepaths [infilepaths ...]

Parse cmake listfiles and format them nicely.

positional arguments:
  infilepaths

optional arguments:
  -h, --help            show this help message and exit
  -i, --in-place
  -o OUTFILE_PATH, --outfile-path OUTFILE_PATH
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        path to json config
~~~

## Example
Will turn this:
~~~.cmake
# The following multiple newlines should be collapsed into a single newline


# This multiline-comment should be joined
# together into a single comment
# on one line

# This comment should remain right before the command call. Furthermore, the command call should
# be formatted to a single line.
foo(arg1 arg2 arg3
    arg4 arg5)

# This very long command should be split to multiple lines
foo(very_long_argument1 very_long_argument2 very_long_argument3 very_long_argument4 very_long_argument5 very_long_argument_6)

# The string in this command should not be split
foo(very_long_argument1 very_long_argumetn2 very_long_argument3 "This is a string that should not be split into multiple lines")

foo(very_long_argument1 very_long_argument2 # This comment should be preserved, moreover it should be split across two lines.
    arg3)


# This part of the comment should
# be formatted
# but...
#
# cmake_format: off
# This comment should
#    remain unformatted
#        by cmake_format
# cmake_format: on
#
#          while this part should be formatted again

# This is a paragraph
#
# This is a second paragraph
#
# This is a third paragraph

# This is a comment
# that should be joined but
# TODO(josh): This todo should not be joined with the previous line. Also this
# NOTE(josh): should not be joined either.

if(something)
if(something_else)
# This comment is in-scope.
foo(arg1, arg2 # this is a comment for arg2
               # this is more comment for arg2, it should be joined with the first.
    arg3)
endif()
endif()


# This very long command should be broken up along keyword arguments
foo(some_thing HEADERS foo.h bar.h baz.h foo.h bar.h baz.h foo.h bar.h SOURCES some_directory/*.cc
    some_other_directory/with_a_subdirectory/*.cc 
    and_yet_one_more/directry_with_sub/*.cc DEPENDS foo bar)
~~~

into this:
~~~.cmake
# The following multiple newlines should be collapsed into a single newline

# This multiline-comment should be joined together into a single comment on one
# line

# This comment should remain right before the command call. Furthermore, the
# command call should be formatted to a single line.
foo(arg1 arg2 arg3 arg4 arg5)

# This very long command should be split to multiple lines
foo(very_long_argument1 very_long_argument2 very_long_argument3
    very_long_argument4 very_long_argument5 very_long_argument_6)

# The string in this command should not be split
foo(very_long_argument1 very_long_argumetn2 very_long_argument3
    "This is a string that should not be split into multiple lines")

foo(very_long_argument1 very_long_argument2 # This comment should be preserved,
                                            # moreover it should be split across
                                            # two lines. arg3)

# This part of the comment should be formatted but...
#
# cmake_format: off
# This comment should
#    remain unformatted
#        by cmake_format
# cmake_format: on
#
# while this part should be formatted again

# This is a paragraph
#
# This is a second paragraph
#
# This is a third paragraph

# This is a comment that should be joined but
# TODO(josh): This todo should not be joined with the previous line. Also this
# NOTE(josh): should not be joined either.

if(something)
  if(something_else)
    # This comment is in-scope.
    foo(arg1, arg2 # this is a comment for arg2 this is more comment for arg2,
                   # it should be joined with the first. arg3)
  endif()
endif()

# This very long command should be broken up along keyword arguments
foo(some_thing
    HEADERS foo.h bar.h baz.h foo.h bar.h baz.h foo.h bar.h
    SOURCES some_directory/*.cc some_other_directory/with_a_subdirectory/*.cc
            and_yet_one_more/directry_with_sub/*.cc
    DEPENDS foo bar)

~~~