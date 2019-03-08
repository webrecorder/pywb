import os
import sys
import json
import re

from argparse import ArgumentParser, RawTextHelpFormatter
from collections import OrderedDict

from pywb.manager.manager import CollectionsManager
from pywb.warcserver.index.cdxobject import CDXObject
from pywb.utils.canonicalize import canonicalize

from pywb.warcserver.access_checker import AccessChecker


# ============================================================================
class ACLManager(CollectionsManager):
    SURT_RX = re.compile('([^:.]+[,)])+')

    VALID_ACCESS = ('allow', 'block', 'exclude')

    DEFAULT_FILE = 'access-rules.aclj'

    def __init__(self, r):
        self.rules = []

        coll_name = r.coll_name
        if not self.is_valid_auto_coll(r.coll_name):
            coll_name = ''

        self.target = r.coll_name

        super(ACLManager, self).__init__(coll_name, must_exist=False)

        # if target exists as a file, use that
        if os.path.isfile(self.target):
            self.acl_file = self.target

        # otherwise, if auto collection, use default file in ./collections/<coll>/acl/<DEFAULT_FILE>
        elif os.path.isdir(self.curr_coll_dir):
            self.acl_file = os.path.join(self.acl_dir, self.DEFAULT_FILE)

        # else, assume filename (may not exist yet)
        else:
            self.acl_file = self.target

        # for add/import, file doesn't have to exist
        if r.op in ('add', 'importtxt'):
            self.load_acl(False)

        # for other ops (except matching), ensure entire file loads successfully, log errors
        elif r.op not in ('match'):
            if not self.load_acl(True):
                sys.exit(2)
                return

        # if 'validate', the command itself is validation
        if r.op != 'validate':
            self.validate()

        r.acl_func(self, r)

    def is_valid_auto_coll(self, coll_name):
        if not self.COLL_RX.match(coll_name):
            return False

        if not os.path.isdir(os.path.join(self.COLLS_DIR, coll_name)):
            return False

        return True

    def load_acl(self, must_exist=True):
        try:
            with open(self.acl_file, 'rb') as fh:
                for line in fh:
                    if line:
                        self.rules.append(CDXObject(line))

            return True

        except IOError as io:
            if must_exist:
                print('Error Occured: ' + str(io))
            return False

        except Exception as e:
            print('Error Occured: ' + str(e))
            return False

    def save_acl(self, r=None):
        try:
            os.makedirs(os.path.dirname(self.acl_file))
        except OSError:
            pass

        try:
            with open(self.acl_file, 'wb') as fh:
                for acl in self.rules:
                    fh.write(acl.to_cdxj().encode('utf-8'))

        except Exception as e:
            print('Error Saving ACL Rules: ' + str(e))

    def to_key(self, url_or_surt, exact_match=False):
        """ If 'url_or_surt' already a SURT, use as is
        If exact match, add the exact match suffix
        """
        if self.SURT_RX.search(url_or_surt):
            result = url_or_surt
        else:
            result = canonicalize(url_or_surt)

        if exact_match:
            result += AccessChecker.EXACT_SUFFIX

        return result

    def validate_access(self, access):
        if access not in self.VALID_ACCESS:
            print('Valid access values are: ' + ', '.join(self.VALID_ACCESS))
            sys.exit(1)
            return False

        return True

    def add_rule(self, r):
        return self._add_rule(r.url, r.access, r.exact_match)

    def _add_rule(self, url, access, exact_match=False):
        if not self.validate_access(access):
            return

        acl = CDXObject()
        acl['urlkey'] = self.to_key(url, exact_match)
        acl['timestamp'] = '-'
        acl['access'] = access
        acl['url'] = url

        i = 0
        replace = False

        for rule in self.rules:
            if acl['urlkey'] == rule['urlkey'] and acl['timestamp'] == rule['timestamp']:
                replace = True
                break

            if acl > rule:
                break

            i += 1

        if replace:
            print('Existing Rule Found, Replacing:')
            self.print_rule(self.rules[i])
            print('with:')
            self.print_rule(acl)
            self.rules[i] = acl
        else:
            print('Added new Rule:')
            self.print_rule(acl)
            self.rules.insert(i, acl)

        self.save_acl()

    def validate_save(self, r=None):
        if self.validate(True):
            self.save_acl()

    def validate(self, log=False):
        last_rule = None
        out_of_order = False
        for rule in self.rules:
            if last_rule and rule > last_rule:
                out_of_order = True
                break

            last_rule = rule

        if out_of_order:
            if log:
                print('Rules out of order, resorting')
            self.rules.sort(reverse=True)
            return True
        else:
            if log:
                print('Rules in order')

            return False

    def remove_rule(self, r):
        i = 0
        urlkey = self.to_key(r.url, r.exact_match)
        for rule in self.rules:
            if urlkey == rule['urlkey']:# and r.timestamp == rule['timestamp']:
                acl = self.rules.pop(i)
                print('Removed Rule:')
                self.print_rule(acl)
                self.save_acl()
                return

            i += 1

        print('Rule to remove not found!')

    def list_rules(self, r):
        print('Rules for {0} from {1}:'.format(self.target, self.acl_file))
        print('')
        for rule in self.rules:
            sys.stdout.write(rule.to_cdxj())
        print('')

    def find_match(self, r):
        access_checker = AccessChecker(self.acl_file, '<default>')
        rule = access_checker.find_access_rule(r.url)

        print('Matched rule:')
        print('')
        if rule['urlkey'] == '':
            print('    <No Match, Using Default Rule>')
            print('')
        else:
            self.print_rule(rule)

    def add_excludes(self, r):
        """
        Import old-style excludes, in url-per-line format
        """
        if not self.validate_access(r.access):
            return

        try:
            with open(r.filename, 'rb') as fh:
                count = 0
                for url in fh:
                    url = url.decode('utf-8').strip()
                    self._add_rule(url, r.access)
                    count += 1

            print('Added or replaced {0} rules from '.format(count) + r.filename)

        except Exception as e:
            print('Error Importing: ' + str(e))
            sys.exit(1)

    def print_rule(self, rule):
        print('    ' + rule.to_cdxj())

    @classmethod
    def init_parser(cls, parser):
        subparsers = parser.add_subparsers(dest='op')
        subparsers.required = True

        def command(name, *args, **kwargs):
            op = subparsers.add_parser(name)
            for arg in args:
                if arg == 'default_access':
                    op.add_argument(arg, nargs='?', default='allow')
                else:
                    op.add_argument(arg)

            if kwargs.get('exact_opt'):
                op.add_argument('-e', '--exact-match', action='store_true', default=False)

            op.set_defaults(acl_func=kwargs['func'])

        command('add', 'coll_name', 'url', 'access', func=cls.add_rule, exact_opt=True)
        command('remove', 'coll_name', 'url', func=cls.remove_rule, exact_opt=True)
        command('list', 'coll_name', func=cls.list_rules)
        command('validate', 'coll_name', func=cls.validate_save)
        command('match', 'coll_name', 'url', 'default_access', func=cls.find_match)
        command('importtxt', 'coll_name', 'filename', 'access', func=cls.add_excludes)

