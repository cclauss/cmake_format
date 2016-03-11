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

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

def build_attr_dict_r(regular_dict):
    attr_dict = AttrDict()
    for key, value in regular_dict.iteritems():
        if isinstance(value, dict):
            attr_dict[key] = build_attr_dict_r(value)
        else:
            attr_dict[key] = value
    return attr_dict

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


def format_args(line_width, args):
    """Format arguments into a block with at most line_width chars."""
    return [arg.contents for arg in args]

def format_command(config, command, line_width):
    """Formats a cmake command call into a block with at most line_width chars.
       Returns a list of lines."""

    
    command_start = command.name + '('

    # If there are no args then return just the command
    if len(command.body) < 1:
        return [command_start + ')']
    else:
        # Format args into a block that is aligned with the end of the 
        # parenthesis after the command name
        lines_a = format_args(line_width - len(command_start), command.body)

        # Format args into a block that is aligned with the command start
        # plus one tab size
        lines_b = format_args(line_width - config.tab_size, command.body)
        
        # TODO(josh) : handle inline comment for the command
        # If the version aligned with the comand start + indent has *alot*
        # fewer lines than the version aligned with the command end, then
        # use this one
        if len(lines_a) > 4 * len(lines_b):
            lines = [command_start]
            indent_str = ' '*config.tab_size
            for line in lines_b:
                lines.append(indent_str + line)
            if(len(lines[-1]) < line_width):
                lines[-1] += ')'
            else:
                lines.append(indent_str[:-1] + ')')
            
        # Otherwise use the version that is alinged with the command ending
        else:
            lines = [command_start + lines_a[0]]
            indent_str = ' '*len(command_start)
            for line in lines_a:
                lines.append(indent_str + line)
            if(len(lines[-1]) < line_width):
                lines[-1] += ')'
            else:
                lines.append(indent_str[:-1] + ')')
    return lines

def write_indented(outfile, indent_str, lines):
    for line in lines:
        outfile.write(indent_str)
        outfile.write(line)
        outfile.write('\n')

class PrettyPrinter(object):
    """Manages state during processing of file lines. Accumulates newlines and
       comment lines so that they can be reflowed / reformatted as text."""

    def __init__(self, config, outfile):
        self.config = config
        self.outfile = outfile
        self.scope_depth = 0
        self.indent = config.tab_size
        self.line_width = config.line_width
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
            command = part
            if command.name in SCOPE_DECREASE:
                self.scope_depth -= 1

            indent_str = ' '*(self.config.tab_size*self.scope_depth)
            lines = format_command(self.config, command, 
                                   self.config.line_width - len(indent_str))
            write_indented(self.outfile, indent_str, lines)

            if command.name in SCOPE_INCREASE:
                self.scope_depth += 1

        else:
            raise ValueError('Unrecognized parse type {}'.format(type(part)))

    def consume_parts(self, parsed_listfile):
        for part in parsed_listfile:
            self.consume_part(part)
        self.flush_comment()
        self.flush_blanks()

def process_file(config, infile, outfile):
    """Iterates through lines in the file and watches for cmake_format on/off
       sentinels. Consumes lines for formatting when active, and passes through
       to the outfile when not."""
    pretty_printer = PrettyPrinter(config, outfile)

    active = True
    format_me = ''
    for line in iter(infile.readline, b''):
        if active:
            if line.find('cmake_format: off') != -1:
                parsed_listfile = cmp.parse(format_me)
                pretty_printer.consume_parts(parsed_listfile)
                parsed_listfile = cmp.parse(line)
                pretty_printer.consume_parts(parsed_listfile)
                format_me = ''
                active = False
            else:
                format_me += line
        else:

            if line.find('cmake_format: on') != -1:
                parsed_listfile = cmp.parse(line)
                pretty_printer.consume_parts(parsed_listfile)
                active = True
                format_me = ''
            else:
                outfile.write(line)

    if format_me:
        parsed_listfile = cmp.parse(format_me)
        pretty_printer.consume_parts(parsed_listfile)

DEFAULT_CONFIG = build_attr_dict_r(dict(
    line_width=80,
    tab_size=2,
    ))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-i', '--in-place', action='store_true')
    parser.add_argument('-o', '--outfile-path', default='-')
    parser.add_argument('-w', '--line-width', type=int, default=80)
    parser.add_argument('-t', '--tab-size', type=int, default=2)
    parser.add_argument('infilepaths', nargs='+')
    args = parser.parse_args()

    config = DEFAULT_CONFIG
    config.line_width = args.line_width
    config.tab_size = args.tab_size

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
                process_file(config, infile, outfile)
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
