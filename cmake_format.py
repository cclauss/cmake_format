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


def format_args_old(chars_available, args):
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


def write_block(outfile, indent, lines, skip_first=True):
    indent_str = ' '*indent
    for line in lines:
        outfile.write(indent_str)
        outfile.write(line)
        outfile.write('\n')

def format_args(line_width, args):
    """Format arguments into a block with at most line_width chars."""
    return [arg.contents for arg in args]

def pretty_print_command(pretty_printer, command):
    """Formats a cmake command call"""

    outfile = pretty_printer.outfile

    if command.name in SCOPE_DECREASE:
        pretty_printer.scope_depth -= 1

    # No matter what, we can go ahead and print the command name. This also helps us figure out
    # how much space we have for indents
    scope_indent = (pretty_printer.indent * pretty_printer.scope_depth)
    scope_indent_str = ' ' * scope_indent
    outfile.write(scope_indent_str)
    outfile.write(command.name)
    outfile.write('(')

    if command.name in SCOPE_INCREASE:
        pretty_printer.scope_depth += 1

    # If there are no args then just print the command
    if len(command.body) < 1:
        pretty_printer.outfile.write(')\n')
    else:
        # If the whole thing doesn't fit on one line, then try to break arguments 
        # onto new lines
        lines_a = format_args(pretty_printer.line_width - len(command.name) - 1, 
                              command.body)
        lines_b = format_args(pretty_printer.line_width - scope_indent - 4, 
                              command.body)
        # TODO(josh) : handle inline comment for the command
        if len(lines_a) > 4 * len(lines_b):
            indent = scope_indent + 4
            indent_str = ' '*indent
            outfile.write('\n')
            for line in lines_b[:-1]:
                outfile.write(indent_str)
                outfile.write(line)
                outfile.write('\n')
            line = lines_b[-1]
            outfile.write(indent_str)
            outfile.write(line)
            if len(line) + len(indent_str) + 1 > pretty_printer.line_width:
                outfile.write('\n')
                outfile.write(indent_str[:-1])
            outfile.write(')\n')

        else:
            indent = scope_indent + len(command.name) + len('(')
            indent_str = ' '*indent

            outfile.write(lines_b[0])
            outfile.write('\n')
            for line in lines_b[1:-1]:
                outfile.write(indent_str)
                outfile.write(line)
                outfile.write('\n')
            line = lines_b[-1]
            outfile.write(indent_str)
            outfile.write(line)
            if len(line) + len(scope_indent_str) + 1 > pretty_printer.line_width:
                outfile.write('\n')
                outfile.write(indent_str[:-1])
            outfile.write(')\n')

# TODO(josh): handle comment at end of argument line

    if command.name in SCOPE_DECREASE:
        pretty_printer.scope_depth -= 1

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

def process_file(infile, outfile):
    line_width = 80
    active = True
    format_me = ''
    for line in iter(infile.readline, b''):
        if active:
            if line.find('cmake_format: off') != -1:
                parsed_listfile = cmp.parse(format_me)
                pretty_print(outfile, parsed_listfile, line_width)
                parsed_listfile = cmp.parse(line)
                pretty_print(outfile, parsed_listfile, line_width)
                format_me = ''
                active = False
            else:
                format_me += line
        else:

            if line.find('cmake_format: on') != -1:
                parsed_listfile = cmp.parse(line)
                pretty_print(outfile, parsed_listfile, line_width)
                active = True
                format_me = ''
            else:
                outfile.write(line)

    if format_me:
        parsed_listfile = cmp.parse(format_me)
        pretty_print(outfile, parsed_listfile, line_width)

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
                process_file(infile, outfile)
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
