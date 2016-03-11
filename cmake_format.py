"""Parse cmake listfiles and format them nicely."""

import argparse
import cmakelists_parsing.parsing as cmp
import re
import shutil
import sys
import tempfile
import textwrap

SCOPE_INCREASE = ['if', 'foreach', 'while', 'function', 'macro']
SCOPE_DECREASE = ['endif', 'endforeach', 'endwhile', 'endfunction', 'endmacro']


TODO_REGEX = re.compile(r'^TODO\([^)]+\):.*')
NOTE_REGEX = re.compile(r'^NOTE\([^)]+\):.*')
KWARG_REGEX = re.compile(r'[A-Z0-9_]+')

def pretty_print_comment_block(pretty_printer, comment_lines):
    stripped_lines = [line[1:].strip() for line in comment_lines]

    paragraph_lines = list()
    paragraphs = list()
    # A new "paragraph" starts at a paragraph boundary (double newline), or at the start of a
    # TODO(...): or NOTE(...):
    for line in stripped_lines:
        if TODO_REGEX.match(line) or NOTE_REGEX.match(line):
            paragraphs.append(' '.join(paragraph_lines))
            paragraph_lines = [line]
        elif line:
            paragraph_lines.append(line)
        else:
            if paragraph_lines:
                paragraphs.append(' '.join(paragraph_lines))
            paragraphs.append('')
            paragraph_lines = list()
    if paragraph_lines:
        paragraphs.append(' '.join(paragraph_lines))

    for paragraph_text in paragraphs:
        if not paragraph_text:
            pretty_printer.outfile.write('#\n')
            continue
        indent = ' ' * (pretty_printer.indent * pretty_printer.scope_depth) + '# '
        wrapper = textwrap.TextWrapper(width=pretty_printer.line_width,
                                       expand_tabs=True,
                                       replace_whitespace=True,
                                       drop_whitespace=True,
                                       initial_indent=indent,
                                       subsequent_indent=indent)
        pretty_printer.outfile.write(wrapper.fill(paragraph_text))
        pretty_printer.outfile.write('\n')


def format_args(chars_available, args):
    # Now split the arguments into groups based on KWARGS which are identified by all caps
    arg_split = [[]]
    current_list = arg_split[-1]
    for arg in args:
        if KWARG_REGEX.match(arg.contents):
            arg_split.append([])
            current_list = arg_split[-1]
        current_list.append(arg)

    if not arg_split[0]:
        arg_split.pop(0)


    lines = []
    for arg_list in arg_split:
        lines.append(arg_list[0].contents)
        indent_str = ' '*(len(arg_list[0].contents) + 1)
        # If the list is "long" put one element on each line
        if len(arg_list) > 4:
            lines[-1] += ' ' + arg_list[1].contents
            for arg in arg_list[2:]:
              lines.append(indent_str + arg.contents)
        else:
          for arg in arg_list[1:]:
              if len(arg.contents) + len(lines[-1]) + 1 < chars_available:
                  lines[-1] += ' ' + arg.contents
              else:
                  lines.append(indent_str + arg.contents)

    return lines

def pretty_print_command(pretty_printer, command):
    """Formats a command (in the most expanded form) as:
        command(normal_arg normal_arg
                KWARG normal_arg normal_arg normal_arg
                KWARG normal_arg
                      normal_arg
                      normal_arg # Has a comment
                                 # That extends multiple lines
                      normal_arg
                      normal_arg)
    """
    if command.name in SCOPE_DECREASE:
        pretty_printer.scope_depth -= 1

    # No matter what, we can go ahead and print the command name. This also helps us figure out
    # how much space we have for indents
    indent_str = ' ' * (pretty_printer.indent * pretty_printer.scope_depth)
    pretty_printer.outfile.write(indent_str)
    pretty_printer.outfile.write(command.name)
    pretty_printer.outfile.write('(')

    if command.name in SCOPE_INCREASE:
        pretty_printer.scope_depth += 1

    # This is the new indent, which ensures that all arguments are aligned with the opening
    # parenthesis of the command
    indent_str += ' '*(len(command.name) + 1)

    # Check if the whole thing fits on one line
    arg_strs = [arg.contents for arg in command.body]
    single_line = ' '.join(arg_strs)
    if len(indent_str) + len(single_line) + 1 < pretty_printer.line_width:
        pretty_printer.outfile.write(single_line)
        pretty_printer.outfile.write(')\n')
        return

    # If the whole thing doesn't fit on one line, then try to break arguments onto new lines,
    # but prefer breaking on KWARGS (all caps)
    chars_available = pretty_printer.line_width - len(indent_str)
    lines = format_args(chars_available, command.body)
    pretty_printer.outfile.write(lines[0])
    pretty_printer.outfile.write('\n')
    for line in lines[1:-1]:
        pretty_printer.outfile.write(indent_str)
        pretty_printer.outfile.write(line)
        pretty_printer.outfile.write('\n')
    pretty_printer.outfile.write(indent_str)
    pretty_printer.outfile.write(lines[-1])
    if len(indent_str) + len(lines[-1]) < pretty_printer.line_width:
        pretty_printer.outfile.write(')\n')
    else:
        pretty_printer.outfile.write('\n')
        pretty_printer.outfile.write(indent_str)
        pretty_printer.outfile.write(')\n')

#    first_arg_on_line = True
#    for arg in command.body:
#        if first_arg_on_line:
#            chars_written += len(arg.contents)
#            pretty_printer.outfile.write(arg.contents)
#            first_arg_on_line = False
#        elif chars_written + len(arg.contents) + 1 < pretty_printer.line_width:
#            chars_written += len(arg.contents) + 1
#            pretty_printer.outfile.write(' ')
#            pretty_printer.outfile.write(arg.contents)
#        else:
#            pretty_printer.outfile.write('\n')
#            pretty_printer.outfile.write(indent_str)
#            pretty_printer.outfile.write(arg.contents)
#            chars_written = len(indent_str) + len(arg.contents)

#        if arg.comments:
#            comment_text = ' '.join([str(comment)[2:] for comment in arg.comments])
#            available_width = pretty_printer.line_width - chars_written
#            wrapper = textwrap.TextWrapper(width=available_width,
#                                           drop_whitespace=True,
#                                           initial_indent=' # ',
#                                           subsequent_indent=' # ')
#            wrapped_comment = ('\n' + ' ' * chars_written).join(wrapper.wrap(comment_text))
#            pretty_printer.outfile.write(wrapped_comment)
#            pretty_printer.outfile.write('\n')
#            pretty_printer.outfile.write(indent_str)
#            chars_written = len(indent_str)

#    # TODO(josh): handle comment at end of argument line
#    pretty_printer.outfile.write(')\n')

    if command.name in SCOPE_INCREASE:
        pretty_printer.scope_depth += 1


class PrettyPrinter(object):

    def __init__(self, outfile, indent, line_width):
        self.outfile = outfile
        self.scope_depth = 0
        self.indent = indent
        self.line_width = line_width
        self.comment_parts = list()
        self.blank_parts = list()

    def flush_blanks(self):
        if self.blank_parts:
            self.outfile.write('\n')
            self.blank_parts = list()

    def flush_comment(self):
        # TODO(josh): Handle lines starting with TODO.
        if self.comment_parts:
            pretty_print_comment_block(self, self.comment_parts)
            self.comment_parts = list()

    def consume_part(self, part):
        if isinstance(part, cmp.BlankLine):
            self.flush_comment()
            self.blank_parts.append(part)
        elif isinstance(part, cmp.Comment):
            self.flush_blanks()
            self.comment_parts.append(part)

        elif isinstance(part, cmp._Command):
            self.flush_comment()
            self.flush_blanks()
            pretty_print_command(self, part)
        else:
            raise ValueError('Unrecognized parse type {}'.format(type(part)))


def pretty_print(outfile, parsed_listfile, line_width):
    indent = 2
    printer = PrettyPrinter(outfile, indent, line_width)

    for part in parsed_listfile:
        printer.consume_part(part)
    printer.flush_comment()
    printer.flush_blanks()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-i', '--in-place', action='store_true')
    parser.add_argument('-o', '--outfile-path', default='-')
    parser.add_argument('-w', '--line-width', type=int, default=100)
    parser.add_argument('infilepaths', nargs='+')
    args = parser.parse_args()

    for infile_path in args.infilepaths:
        if args.in_place:
            outfile = tempfile.NamedTemporaryFile(delete=False)
        else:
            if args.outfile_path == '-':
                outfile = sys.stdout
            else:
                outfile = open(args.outfile_path, 'w')

        parse_ok = True
        try:
            with open(infile_path, 'r') as infile:
                active = True
                format_me = ''
                for line in iter(infile.readline, b''):
                    if active:
                        if line.find('cmake_format: off') != -1:
                            parsed_listfile = cmp.parse(format_me)
                            pretty_print(outfile, parsed_listfile, args.line_width)
                            parsed_listfile = cmp.parse(line)
                            pretty_print(outfile, parsed_listfile, args.line_width)
                            format_me = ''
                            active = False
                        else:
                            format_me += line
                    else:

                        if line.find('cmake_format: on') != -1:
                            parsed_listfile = cmp.parse(line)
                            pretty_print(outfile, parsed_listfile, args.line_width)
                            active = True
                            format_me = ''
                        else:
                            outfile.write(line)

            if format_me:
                parsed_listfile = cmp.parse(format_me)
                pretty_print(outfile, parsed_listfile, args.line_width)
        except:
            parse_ok = False
            raise
        finally:
            if args.in_place:
                outfile.close()
                if parse_ok:
                    shutil.move(outfile.name, infile_path)
            else:
                if args.outfile_path != '-':
                    outfile.close()

if __name__ == '__main__':
    main()
