#!/bin/python

"""Check Mock Usage in Tests

Usage:
  check_mock_usage [--path=<root>] [--suffix=<filesuffix>] [--suite_pat=<suitepat>] [--test_pat=<testpat>] [--mock_pat=<mockpat>]
  check_mock_usage -h | --help
  check_mock_usage --version

Options:
  -h --help                Show this screen.
  --version                Show version.
  --path=<root>            Directory to scan (default is current working directory)
  --suffix=<filesuffix>    File name suffix to restrict to (default is '.ts')
  --suite_pat=<suitepat>   A pattern to use to detect start of a test suite and extract name.
  --test_pat=<testpat>     A pattern to use to detect start of a test and extract name.
  --mock_pat=<mockpat>     A pattern to user to detect the creation of a mock.

Note that if helper functions are used, results are approximate. Any mock pattern matches defined 
between the start of the suite and the first test are assumed to accrue to every test in the 
suite.
"""

import docopt
import glob
import os
import re


def count(root, suffix, suite_pat, test_pat, mock_pat):
    if root is None:
        root = '.'
    filepat = '*.ts' if suffix is None else '*.' + suffix[suffix.find('.')+1:]
    if suite_pat is None:
        suite_pat = '^[ \t]*suite\([\'\"](.*)[\'\"],'
    if test_pat is None:
        test_pat = '^[ \t]*test\([\'\"](.*)[\'\"],'
    if mock_pat is None:
        mock_pat = '\.Mock\.ofType'

    try:
        suite_re = re.compile(suite_pat)
    except Exception as e:
        print(f"Invalid suite pattern {suite_pat}: {e}")
        return

    try:
        test_re = re.compile(test_pat)
    except Exception as e:
        print(f"Invalid test pattern {test_pat}: {e}")
        return

    try:
        mock_re = re.compile(mock_pat)
    except Exception as e:
        print(f"Invalid mock pattern {mock_pat}: {e}")
        return

    pathpat = root + '/**/' + filepat
    results = []
    file_results = {}
    histo = {}
    total_mocks = 0
    total_tests = 0
    total_mocks_in_file = 0
    total_tests_in_file = 0
    suite_mock_count = 0
    test_mock_count = 0
    suite_name = ''
    test_name = None

    def log_result():
        nonlocal results, total_tests, total_tests_in_file, total_mocks, total_mocks_in_file, histo
        if test_name:
            mocks = suite_mock_count + test_mock_count
            results.append(f'{name}:{suite_name}:{test_name} uses {mocks} mocks')
            total_tests += 1
            total_tests_in_file += 1
            total_mocks += mocks
            total_mocks_in_file += mocks
            if mocks in histo:
                histo[mocks] += 1
            else:
                histo[mocks] = 1
        
    for name in glob.iglob(pathpat, recursive=True):
        n = 0
        if os.path.isdir(name): 
            continue
        try:
            with open(name) as f:
                total_mocks_in_file = 0
                total_tests_in_file = 0
                suite_mock_count = 0
                test_mock_count = 0
                suite_name = ''
                test_name = None
                for line in f:
                    n += 1
                    m = suite_re.search(line)
                    if m:
                        log_result()
                        test_name = None
                        suite_name = m.group(1)
                        suite_mock_count = 0
                    m = test_re.search(line)
                    if m:
                        log_result()
                        test_name = m.group(1)
                        test_mock_count = 0
                    m = mock_re.search(line)
                    if m:
                        if test_name:
                            test_mock_count += 1
                        else:
                            suite_mock_count += 1
          
                # Theoretically we could have an issue with tests in a suite followed by tests
                # outside a suite in the same file, but I assume that is rare. We will wrongly
                # assume they are part of the prior suite. This isn't a big deal.

                log_result()
                file_avg = round(total_mocks_in_file / total_tests_in_file) if total_tests_in_file > 0 else 0
                if total_mocks_in_file > 0:
                    file_results[name] = file_avg

        except Exception as e:
            print(f"Couldn't process file {name}: {e} at line {n}")
     
    if total_tests == 0:
        print('No tests found')
        return

    print(f'Overall results: {total_tests} tests with {total_mocks} mocks; average of {total_mocks/total_tests} mocks per test')
    
    results = sorted(results)
    for name, value in sorted(file_results.items(), key=lambda item: item[1], reverse=True):
        if value == 0:
            continue

        print(f'\nFile {name} has average {value} mocks per test')

        k = name + ':'
        got_group = False
        for r in results:
            if r.startswith(k):
                got_group = True
                print(r)
            elif got_group:
                break
        
    print('\n\nNumber of tests having x number of mocks:\n')
    #print(histo.keys())

    for i in sorted(histo.keys()):
        print(f'{i}: {histo[i]}')


if __name__ == "__main__":
    args = docopt.docopt(__doc__, version='Check Mock Usage 0.1')
    count(root=args['--path'], suffix=args['--suffix'], suite_pat=args['--suite_pat'], test_pat=args['--test_pat'], mock_pat=args['--mock_pat'])
