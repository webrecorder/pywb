import os
import re
import sys

from pywb.manager.manager import CollectionsManager
from pywb.utils.canonicalize import canonicalize
from pywb.warcserver.access_checker import AccessChecker
from pywb.warcserver.index.cdxobject import CDXObject


# ============================================================================
class ACLManager(CollectionsManager):
    SURT_RX = re.compile('([^:.]+[,)])+')

    VALID_ACCESS = ('allow', 'block', 'exclude', 'allow_ignore_embargo')

    DEFAULT_FILE = 'access-rules.aclj'

    def __init__(self, r):
        """
        :param argparse.Namespace r: Parsed result from ArgumentParser
        :rtype: None
        """
        self.rules = []

        coll_name = r.coll_name
        if not self.is_valid_auto_coll(r.coll_name):
            coll_name = ''

        self.target = r.coll_name

        super(ACLManager, self).__init__(coll_name, must_exist=False)

        self.acl_file = None

    def process(self, r):
        """
        Process acl command

        :param argparse.Namespace r: Parsed result from ArgumentParser
        :rtype: None
        """

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
        """Returns T/F indicating if the supplied collection name
        is a valid collection

        :param coll_name: The collection name to check
        :return: T/F indicating a valid collection
        :rtype: bool
        """
        if not self.COLL_RX.match(coll_name):
            return False

        if not os.path.isdir(os.path.join(self.COLLS_DIR, coll_name)):
            return False

        return True

    def load_acl(self, must_exist=True):
        """Loads the access control list

        :param bool must_exist: Does the acl file have to exist
        :return: T/F indicating load success
        :rtype: bool
        """
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
        """Save the contents of the rules as cdxj entries to
        the access control list file

        :param argparse.Namespace|None r: Not used
        :rtype: None
        """
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

        :param str url_or_surt: The url or surt to be converted to an acl key
        :param bool exact_match: Should the exact match suffix be added to key
        :rtype: str
        """
        if self.SURT_RX.search(url_or_surt):
            result = url_or_surt
        else:
            result = canonicalize(url_or_surt)

        if exact_match:
            result += AccessChecker.EXACT_SUFFIX

        return result

    def validate_access(self, access):
        """Returns true if the supplied access value is valid
        otherwise terminates the process

        :param str access: The access value to be validated
        :return: True if valid
        :rtype: bool
        """
        if access not in self.VALID_ACCESS:
            print('Valid access values are: ' + ', '.join(self.VALID_ACCESS))
            sys.exit(1)

        return True

    def add_rule(self, r):
        """Adds a rule the ACL manager

        :param argparse.Namespace r: The argparse namespace representing the rule to be added
        :rtype: None
        """
        return self._add_rule(r.url, r.access, r.exact_match, r.user)

    def _add_rule(self, url, access, exact_match=False, user=None):
        """Adds an rule to the acl file

        :param str url: The URL for the rule
        :param str access: The access value for the rule
        :param bool exact_match: Is the rule to be added an exact match
        :rtype: None
        """
        if not self.validate_access(access):
            return

        acl = CDXObject()
        acl['urlkey'] = self.to_key(url, exact_match)
        acl['timestamp'] = '-'
        acl['access'] = access
        acl['url'] = url
        if user:
            acl['user'] = user

        i = 0
        replace = False

        for rule in self.rules:
            if acl['urlkey'] == rule['urlkey'] and acl['timestamp'] == rule['timestamp'] and acl.get('user') == rule.get('user'):
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

    def validate_save(self, r=None, log=False):
        """Validates the acl rules and saves the file

        :param argparse.Namespace|None r: Not used
        :param bool log: Should a report be printed to stdout
        :rtype: None
        """
        self.validate(log=log, correct=True)

    def validate(self, log=False, correct=False):
        """Validates the acl rules returning T/F if the list should be saved

        :param bool log: Should the results of validating be logged to stdout
        :param bool correct: Should invalid results be corrected and saved
        :rtype: None
        """
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
            if correct:
                self.rules.sort(reverse=True)
                self.save_acl()
        elif log:
            print('Rules in order')

    def remove_rule(self, r):
        """Removes a rule from the acl file

        :param argparse.Namespace r: Parsed result from ArgumentParser
        :rtype: None
        """
        i = 0
        urlkey = self.to_key(r.url, r.exact_match)
        for rule in self.rules:
            if urlkey == rule['urlkey'] and r.user == rule.get('user'):
                acl = self.rules.pop(i)
                print('Removed Rule:')
                self.print_rule(acl)
                self.save_acl()
                return

            i += 1

        print('Rule to remove not found!')

    def list_rules(self, r):
        """Print the acl rules to the stdout

        :param argparse.Namespace|None r: Not used
        :rtype: None
        """
        print('Rules for {0} from {1}:'.format(self.target, self.acl_file))
        print('')
        for rule in self.rules:
            sys.stdout.write(rule.to_cdxj())
        print('')

    def find_match(self, r):
        """Finds a matching acl rule

        :param argparse.Namespace r: Parsed result from ArgumentParser
        :rtype: None
        """
        access_checker = AccessChecker(self.acl_file, '<default>')
        rule = access_checker.find_access_rule(r.url, acl_user=r.user)

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

        :param argparse.Namespace r: Parsed result from ArgumentParser
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
        """Prints the supplied rule to the std out

        :param CDXObject rule: The rule to be printed
        :rtype: None
        """
        print('    ' + rule.to_cdxj())

    @classmethod
    def init_parser(cls, parser):
        """Initializes an argument parser for acl commands

        :param argparse.ArgumentParser parser: The parser to be initialized
        :rtype: None
        """
        subparsers = parser.add_subparsers(dest='op')
        subparsers.required = True

        def command(name, *args, **kwargs):
            op = subparsers.add_parser(name)
            for arg in args:
                if arg == 'default_access':
                    op.add_argument(arg, nargs='?', default='allow')
                else:
                    op.add_argument(arg)

            if kwargs.get('user_opt'):
                op.add_argument('-u', '--user')

            if kwargs.get('exact_opt'):
                op.add_argument('-e', '--exact-match', action='store_true', default=False)

            op.set_defaults(acl_func=kwargs['func'])

        command('add', 'coll_name', 'url', 'access', func=cls.add_rule, exact_opt=True, user_opt=True)
        command('remove', 'coll_name', 'url', func=cls.remove_rule, exact_opt=True, user_opt=True)
        command('list', 'coll_name', func=cls.list_rules)
        command('validate', 'coll_name', func=cls.validate_save)
        command('match', 'coll_name', 'url', 'default_access', func=cls.find_match, user_opt=True)
        command('importtxt', 'coll_name', 'filename', 'access', func=cls.add_excludes)

