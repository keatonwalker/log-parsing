import re
import os
import csv
from time import strftime, strptime

date_time_run = strftime("%Y%m%d")  # _%H%M%S")

time_matcher = re.compile(r'(\d{2}:\d{2}:\d{2})')
crate_matcher = re.compile(r"destination': u*'([^']+)")
coord_sys_matcher = re.compile(r"destination_coordinate_system': u'([^']+)")
pallet_matcher = re.compile(r"lift:   39 processing crates for pallet: ([^\r]+)")


def seconds_from_one(time_string):
    t = strptime(time_string, "%H:%M:%S")
    seconds_from_1 = 0
    seconds_from_1 += (t.tm_hour - 1) * 3600
    seconds_from_1 += t.tm_min * 60
    seconds_from_1 += t.tm_sec
    return seconds_from_1


class CrateParser(object):
    '''
        Common data and utilities for crate pasring types
    '''
    match_functions = {}  # match string: line parse functions
    store_functions = {}  # class name: store functions for end of a parse

    def __init__(self):
        self.output_filename = '{}_{}.csv'.format(self.__class__.__name__, date_time_run)

        self.pallet = None
        self.add_match_function('processing crates for pallet:', self.set_pallet)

        self.crate = None
        self.add_match_function("{   'destination': ", self.set_crate)

        self.destination_coord_sys = None
        self.add_match_function('destination_coordinate_system', self.set_destination_coord_sys)

        self.records = []

    def add_match_function(self, match_string, function):
        '''
        match_string: string to match log line
        function: function(line:string): store function | None
        '''
        funcs = CrateParser.match_functions.get(match_string, [])
        funcs.append(function)
        CrateParser.match_functions[match_string] = funcs

    def set_pallet(self, line):
        '''
            Line: line containing pallet name
        '''
        self.reset_fields()
        self.pallet = pallet_matcher.search(line).group(1)

    def set_crate(self, line):
        '''
            Line: line containing crate name
        '''
        self.reset_fields()
        crate = crate_matcher.search(line).group(1)
        self.crate = crate

    def set_destination_coord_sys(self, line):
        '''
            Line: line containing destination coordinate system
        '''
        self.destination_coord_sys = coord_sys_matcher.search(line).group(1)

    def store_record(self):
        '''
            Store fields for output and reset them.
        '''
        self.records.append(self.get_record())
        self.reset_fields()

    def reset_fields(self):
        """
            reset all fields for the type

            implemented in subclasses"""
        pass

    @staticmethod
    def call_match_functions(match_string, line):
        '''
            match_string: string
                String that matched the line. Key to get match function
            line: string
                matched line
        '''
        for f in CrateParser.match_functions[match_string]:
            #: record storing function returned if line triggers a store
            store_func = f(line)
            if store_func:
                #: Keep store function so it can be called after all parse functions for current line
                CrateParser.store_functions[store_func.im_class] = store_func

    @staticmethod
    def get_search_strings():
        '''
            return: list[string]
                list of match strings each line is tested against
        '''
        return CrateParser.match_functions.keys()

    @staticmethod
    def store_records():
        '''
            Store records for type that got triggered by a line
        '''
        for f in CrateParser.store_functions.values():
            if f:
                f()
        CrateParser.store_functions = {}


class HashInsertTemp(CrateParser):

    def __init__(self):
        super(HashInsertTemp, self).__init__()

        self.output_fields = [
            'pallet',
            'dest',
            'dest_coord_sys',
            'start',
            'end',
            'duration',
            'added']

        self.start = 'checking for changes...'
        self.add_match_function(self.start, self.start_parse)
        self.start_time = None

        self.adds = 'Number of rows to be added:'
        self.adds_matcher = re.compile(r'added: (\d+)')
        self.add_match_function(self.adds, self.set_adds)
        self.add_number = None

        self.stop = 'Number of rows to be added:'
        self.add_match_function(self.stop, self.end_parse)
        self.stop_time = None

    def start_parse(self, line):
        time = time_matcher.search(line).group()
        self.start_time = time

    def end_parse(self, line):
        time = time_matcher.search(line).group()
        self.stop_time = time
        return self.store_record

    def set_adds(self, line):
        self.add_number = self.adds_matcher.search(line).group(1)

    def reset_fields(self):
        self.crate = None
        self.start_time = None
        self.stop_time = None
        self.add_number = None

    def get_record(self):
        return (
            self.pallet,
            self.crate,
            self.destination_coord_sys,
            self.start_time,
            self.stop_time,
            seconds_from_one(self.stop_time) - seconds_from_one(self.start_time),
            self.add_number)

    def __str__(self):
        return '{},{},{},{},{},{},{}'.format(
            self.pallet,
            self.crate,
            self.destination_coord_sys,
            self.start_time,
            self.stop_time,
            seconds_from_one(self.stop_time) - seconds_from_one(self.start_time),
            self.add_number)


class Reproject(CrateParser):

    def __init__(self):
        super(Reproject, self).__init__()

        self.output_fields = [
            'pallet',
            'dest',
            'dest_coord_sys',
            'start',
            'end',
            'duration',
            'added']

        self.start = 'Number of rows to be added'
        self.add_match_function(self.start, self.start_parse)
        self.start_time = None

        self.adds = 'Number of rows to be added'
        self.adds_matcher = re.compile(r'added: (\d+)')
        self.add_match_function(self.adds, self.set_adds)
        self.add_number = None

        self.stop = 'starting edit session...'
        self.add_match_function(self.stop, self.end_parse)
        self.stop_time = None

    def start_parse(self, line):
        time = time_matcher.search(line).group()
        self.start_time = time

    def end_parse(self, line):
        time = time_matcher.search(line).group()
        self.stop_time = time
        return self.store_record

    def set_adds(self, line):
        self.add_number = self.adds_matcher.search(line).group(1)

    def reset_fields(self):
        self.crate = None
        self.start_time = None
        self.stop_time = None
        self.add_number = None

    def get_record(self):
        return (
            self.pallet,
            self.crate,
            self.destination_coord_sys,
            self.start_time,
            self.stop_time,
            seconds_from_one(self.stop_time) - seconds_from_one(self.start_time),
            self.add_number)

    def __str__(self):
        return '{},{},{},{},{},{},{}'.format(
            self.pallet,
            self.crate,
            self.destination_coord_sys,
            self.start_time,
            self.stop_time,
            seconds_from_one(self.stop_time) - seconds_from_one(self.start_time),
            self.add_number)


class SourceDestination(CrateParser):

    def __init__(self):
        super(SourceDestination, self).__init__()

        self.output_fields = [
            'pallet',
            'dest_path',
            'src_path',
            'name']

        self.src_line = 'source\':'
        self.src_matcher = re.compile(r"source': u*'([^']+)")
        self.add_match_function(self.src_line, self.src_parse)
        self.source = None

        self.dest_line = 'destination_name'
        self.dest_name_matcher = re.compile(r"destination_name': u*'([^']+)")
        self.add_match_function(self.dest_line, self.dest_name_parse)
        self.destination_name = None

        self.src_line = 'source\':'
        self.src_matcher = re.compile(r"source': u*'([^']+)")
        self.add_match_function(self.src_line, self.src_parse)
        self.source = None

        self.src_line = 'source_name'
        self.src_name_matcher = re.compile(r"source_name': u*'([^']+)")
        self.add_match_function(self.src_line, self.src_name_parse)
        self.source_name = None

    def dest_name_parse(self, line):
        dest_name = self.dest_name_matcher.search(line).group(1)
        self.destination_name = dest_name

    def src_parse(self, line):
        src = self.src_matcher.search(line).group(1)
        self.source = src

    def src_name_parse(self, line):
        src_name = self.src_name_matcher.search(line).group(1)
        self.source_name = src_name
        return self.store_record

    def reset_fields(self):
        self.crate = None
        self.destination_name = None
        self.source = None
        self.source_name = None

    def get_record(self):
        return (
            self.pallet,
            self.crate,
            self.source,
            self.destination_name)

    def __str__(self):
        return '{},{},{},{},{}'.format(
            self.pallet,
            self.crate,
            self.source,
            self.destination_name)


if __name__ == '__main__':
    log_file = os.path.normpath('data/logs/forklift_6_1_17.log')

    parsed_sections = [
        SourceDestination()]
    print 'Parsing Log file: {}'.format(log_file)
    with open(log_file, 'r') as log:
            for line in log:
                for substring in CrateParser.get_search_strings():
                    if substring in line:
                        try:
                            CrateParser.call_match_functions(substring, line)
                        except Exception as e:
                            print line
                            raise(e)

                CrateParser.store_records()

    for p in parsed_sections:
        print len(set(p.records))
        for r in p.records:
            print """Crate('{1}',\n{0}'{2}',\n{0}'{3}'),""".format(' ' * 6, r[1], r[2], r[3])

        # output_path = os.path.normpath(os.path.join('data/output', p.output_filename))
        # print 'Writing output CSV: {}'.format(output_path)
        # with open(output_path, 'w') as out_file:
        #     writer = csv.writer(out_file)
        #     writer.writerow(p.output_fields)
        #     writer.writerows(p.records)
