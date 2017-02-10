import re
import os


time_matcher = re.compile(r'(\d{2}:\d{2}:\d{2})')
name_matcher = re.compile(r"destination': '([^']+)")
coord_sys_matcher = re.compile(r"destination_coordinate_system': u'([^']+)")
pallet_matcher = re.compile(r"lift:   39 processing crates for pallet: ([^\r]+)")


class CrateParser(object):

    def __init__(self):
        self.re_funcs = {}

        self.pallet = None
        self.add_match_function('lift:   39', self.set_pallet)

        self.name = None
        self.add_match_function('lift:   56', self.set_name)

        self.destination_coord_sys = None
        self.add_match_function('destination_coordinate_system', self.set_destination_coord_sys)

        self.matcher = None
        self.records = []

    def add_match_function(self, match_string, function):
        funcs = self.re_funcs.get(match_string, [])
        funcs.append(function)
        self.re_funcs[match_string] = funcs

    def call_match_functions(self, match_string, line):
        for f in self.re_funcs[match_string]:
            f(line)

    def set_pallet(self, line):
        self.pallet = pallet_matcher.search(line).group(1)

    def set_name(self, line):
        self.reset_fields()
        name = name_matcher.search(line).group(1)
        self.name = name

    def set_destination_coord_sys(self, line):
        self.destination_coord_sys = coord_sys_matcher.search(line).group(1)

    def get_re(self):
        group_sep = r'|'
        re_string = group_sep.join(self.re_funcs.keys())
        re_string = group_sep.join('(%s)' % s for s in self.re_funcs.keys())
        return re_string

    def store_record(self):
        self.records.append(str(self))
        self.reset_fields()

    def reset_fields(self):
        pass


class HashInsertTemp(CrateParser):

    def __init__(self):
        super(HashInsertTemp, self).__init__()
        # self.name = 'test'
        self.start = 'core:  237'
        self.add_match_function(self.start, self.start_parse)
        self.start_time = None

        self.adds = 'core:  147'
        self.adds_matcher = re.compile(r'added: (\d+)')
        self.add_match_function(self.adds, self.set_adds)
        self.add_number = None
        # add reset method at the end
        self.stop = 'core:  147'
        self.add_match_function(self.stop, self.end_parse)
        self.stop_time = None

        self.matcher = re.compile(self.get_re())

    def start_parse(self, line):
        time = time_matcher.search(line).group()
        self.start_time = time

    def end_parse(self, line):
        time = time_matcher.search(line).group()
        self.stop_time = time
        self.store_record()

    def set_adds(self, line):
        self.add_number = self.adds_matcher.search(line).group(1)

    def reset_fields(self):
        self.name = None
        self.start_time = None
        self.stop_time = None
        self.add_number = None

    def __str__(self):
        return '{},{},{},{},{},{}'.format(
            self.pallet,
            self.name,
            self.destination_coord_sys,
            self.start_time,
            self.stop_time,
            self.add_number)


class Reproject(CrateParser):

    def __init__(self):
        super(Reproject, self).__init__()
        #self.name = 'test'
        self.start = 'core:  237'
        self.re_funcs[self.start] = self.start_parse
        self.start_time = None
        self.stop = 'core:  147'
        self.re_funcs[self.stop] = self.end_parse
        self.stop_time = None

        self.matcher = re.compile(self.get_re())

    def start_parse(self, line):
        time = '5'
        self.start_time = int(time)

    def end_parse(self, line):
        time = '6'
        self.stop_time = int(time)
        self.store_record()

    def reset_fields(self):
        self.start_time = None
        self.stop_time = None

    def __str__(self):
        return '{},{},{}'.format(self.name, self.start_time, self.stop_time)


if __name__ == '__main__':
    output_filename = os.path.normpath("output/parsed_lines.log")
    log_file = os.path.normpath('5.0.3_add_all_forklift.log')
    # testlines = [
    #     "DEBUG   02-08 01:02:11       lift:   56 {   'destination': 'C:\\Scheduled\\staging\\economy.gdb\\EnterpriseZones'",
    #     'INFO    02-08 01:01:02       core:  237 checking for changes...',
    #     'empty',
    #     'DEBUG   02-08 01:01:04       core:  147 Number of rows to be added: 1666',
    #     'INFO    02-08 01:01:02       core:  237 checking for changes...',
    #     'empty',
    #     'DEBUG   02-08 01:01:04       core:  147 Number of rows to be added: 200'
    #     ]
    t = HashInsertTemp()
    reproject = Reproject()
    search_expressions = [t]#, reproject]

    with open(log_file, 'r') as log:
            for line in log:
                for s in search_expressions:
                    m = s.matcher.search(line)
                    if m is not None:
                        s.call_match_functions(m.group(), line)

    with open(output_filename, 'w') as out_file:
        out_file.write('pallet,dest,dest_coord_sys,start,end,added\n')
        for rec in t.records:
            out_file.write(rec + '\n')
