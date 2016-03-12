# The following multiple newlines should be collapsed into a single newline




cmake_minimum_required(VERSION 2.8.11)
project(cmake_format_test)

# This multiline-comment should be reflowed
# into a single comment
# on one line

# This comment should remain right before the command call. 
# Furthermore, the command call should be formatted 
# to a single line.
add_subdirectories(foo bar baz
  foo2 bar2 baz2)

# This very long command should be split to multiple lines
set(HEADERS very_long_header_name_a.h very_long_header_name_b.h very_long_header_name_c.h)

# This command should be split into one line per entry because it has a long 
# argument list.
set(SOURCES source_a.cc source_b.cc source_d.cc source_e.cc source_f.cc source_g.cc)

# The string in this command should not be split
set_target_properties(foo bar baz PROPERTIES COMPILE_FLAGS "-std=c++11 -Wall -Wextra")
set(CMAKE_CXX_FLAGS "-std=c++11 -Wall -Wextra -Wno-sign-compare -Wno-unused-parameter")

set(HEADERS header_a.h header_b.h # This comment should 
                                  # be preserved, moreover it should be split 
                                  # across two lines.
    header_c.h header_d.h)


# This part of the comment should
# be formatted
# but...
# cmake_format: off
# This bunny should remain untouched:
# . 　 ＿　∩
# 　　ﾚﾍヽ| |
# 　　　 (・ｘ・)
# 　　 c( uu}
# cmake_format: on
#          while this part should 
#          be formatted again

# This is a paragraph
#
# This is a second paragraph
#
# This is a third paragraph

# This is a comment
# that should be joined but
# TODO(josh): This todo should not be joined with the previous line.
# NOTE(josh): Also this should not be joined with the todo.

if(foo)
if(sbar)
# This comment is in-scope.
add_library(foo_bar_baz foo.cc bar.cc # this is a comment for arg2
               # this is more comment for arg2, it should be joined with the first.
    baz.cc)
endif()
endif()


# This very long command should be broken up along keyword arguments
foo(nonkwarg_a nonkwarg_b HEADERS a.h b.h c.h d.h e.h f.h SOURCES a.cc b.cc d.cc DEPENDS foo bar baz)
