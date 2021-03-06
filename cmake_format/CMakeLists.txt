set(cmake_format_py_files
    __init__.py
    __main__.py
    commands.py
    formatter.py
    lexer.py
    parser.py
    tests.py)

add_custom_command(OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/cmake_format_format.stamp
                   COMMAND autopep8 -i ${cmake_format_py_files}
                   COMMAND python -Bm cmake_format -i CMakeLists.txt
                           doc/CMakeLists.txt test/CMakeLists.txt
                   COMMAND touch
                           ${CMAKE_CURRENT_BINARY_DIR}/cmake_format_format.stamp
                   DEPENDS ${cmake_format_py_files}
                   WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})
add_custom_target(cmake_format_format
                  DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/cmake_format_format.stamp)
add_dependencies(format cmake_format_format)

add_custom_command(OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/cmake_format_lint.stamp
                   COMMAND pylint ${cmake_format_py_files}
                   COMMAND touch
                           ${CMAKE_CURRENT_BINARY_DIR}/cmake_format_lint.stamp
                   DEPENDS ${cmake_format_py_files}
                   WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})
add_custom_target(cmake_format_lint
                  DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/cmake_format_lint.stamp)

# NOTE(josh): format before lint-check, avoid formatting lint
add_dependencies(cmake_format_lint cmake_format_format)
add_dependencies(lint cmake_format_lint)

add_test(NAME cmake_format-tests
         COMMAND python -m cmake_format.tests
         WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

add_subdirectory(doc)
add_subdirectory(test)
