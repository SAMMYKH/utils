# setup.py for ax-utils
#

import sys, glob, sqlite3

from distutils.core import setup

con = sqlite3.connect('config.db')

# Get the configuration template file.
with open('package/config_template', 'r') as template_file:
    config_template = template_file.read()

# Generate config.db from config_template file.
try:
    con.executescript(config_template)
except sqlite3.OperationalError:
    pass
else:
    con.commit()

con.close()

setup(
    name = 'ax-displayutils',
    description = 'Minimal display-only utilities for Axent controllers',
    version = '1.0.1',
    author = 'Daniel Dyer',
    author_email = 'daniel_dyer@axent.com.au',
    url = 'http://www.axent.com.au/',
    license = 'Proprietary',
    platforms = 'any',
    packages = ['axdisplay'],
    package_dir = {'axdisplay': 'display/lib'},
    scripts = ['package/ax-package',
               'display/ax-display'],
    data_files=[
        ('/usr/share/ax-utils', ['package/config_template']),
        ('/usr/share/ax-utils/configs', ['display/configs/refresh_db']),
        ('/usr/share/ax-utils/configs/bitstream',
            glob.glob('display/configs/bitstream/*.xml')),
        ('/usr/share/ax-utils/configs/board',
            glob.glob('display/configs/board/*.xml')),
        ('/usr/share/ax-utils/configs/display',
            glob.glob('display/configs/display/*.xml')),
        ('/usr/share/ax-utils/configs/module',
            glob.glob('display/configs/module/*.xml')),
        ('/usr/share/db', ['config.db']),
        ('/etc/init.d', ['S98axdisplayutils'])]
)
