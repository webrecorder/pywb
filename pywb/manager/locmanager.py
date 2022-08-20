import os
import os.path
import shutil

try:
    from babel.messages.frontend import CommandLineInterface

    from translate.convert.po2csv import main as po2csv
    from translate.convert.csv2po import main as csv2po
    loc_avail = True
except:
    loc_avail = False


ROOT_DIR = 'i18n'

TRANSLATIONS = os.path.join(ROOT_DIR, 'translations')

MESSAGES = os.path.join(ROOT_DIR, 'messages.pot')

# ============================================================================
class LocManager:
    def process(self, r):
        if r.name == 'list':
            r.loc_func(self)
        elif r.name == 'remove':
            r.loc_func(self, r.locale)
        else:
            r.loc_func(self, r.locale, r.no_csv)

    def extract_loc(self, locale, no_csv):
        self.extract_text()

        for loc in locale:
            loc_dir = os.path.join(TRANSLATIONS, loc)
            if os.path.isdir(loc_dir):
                self.update_catalog(loc)
            else:
                os.makedirs(loc_dir)
                self.init_catalog(loc)

            if not no_csv:
                base = os.path.join(TRANSLATIONS, loc, 'LC_MESSAGES')
                po = os.path.join(base, 'messages.po')
                csv = os.path.join(base, 'messages.csv')
                po2csv([po, csv])

        self.compile_catalog()

    def update_loc(self, locale, no_csv):
        for loc in locale:
            if not no_csv:
                loc_dir = os.path.join(TRANSLATIONS, loc)
                base = os.path.join(TRANSLATIONS, loc, 'LC_MESSAGES')
                po = os.path.join(base, 'messages.po')
                csv = os.path.join(base, 'messages.csv')

                if os.path.isfile(csv):
                    csv2po([csv, po])

        self.compile_catalog()

    def remove_loc(self, locale):
        for loc in locale:
            loc_dir = os.path.join(TRANSLATIONS, loc)
            if not os.path.isdir(loc_dir):
                print('Locale "{0}" does not exist'.format(loc))
                return

            shutil.rmtree(loc_dir)
            print('Removed locale "{0}"'.format(loc))

    def list_loc(self):
        print('Current locales:')
        print('\n'.join(' - ' + x for x in os.listdir(TRANSLATIONS)))
        print('')

    def extract_text(self):
        os.makedirs(ROOT_DIR, exist_ok=True)

        CommandLineInterface().run(['pybabel', 'extract', '-F', 'babel.ini', '-k', '_ _Q gettext ngettext', '-o', MESSAGES, './', '--omit-header'])

    def init_catalog(self, loc):
        CommandLineInterface().run(['pybabel', 'init', '-l', loc, '-i', MESSAGES, '-d', TRANSLATIONS])

    def update_catalog(self, loc):
        CommandLineInterface().run(['pybabel', 'update', '-l', loc, '-i', MESSAGES, '-d', TRANSLATIONS, '--previous'])

    def compile_catalog(self):
        CommandLineInterface().run(['pybabel', 'compile', '-d', TRANSLATIONS])


    @classmethod
    def init_parser(cls, parser):
        """Initializes an argument parser for acl commands

        :param argparse.ArgumentParser parser: The parser to be initialized
        :rtype: None
        """
        subparsers = parser.add_subparsers(dest='op')
        subparsers.required = True

        def command(name, func):
            op = subparsers.add_parser(name)
            if name != 'list':
                op.add_argument('locale', nargs='+')
                if name != 'remove':
                    op.add_argument('--no-csv', action='store_true')

            op.set_defaults(loc_func=func, name=name)

        command('extract', cls.extract_loc)
        command('update', cls.update_loc)
        command('remove', cls.remove_loc)
        command('list', cls.list_loc)
