from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='cursedmongo',
      version='0.1',
      description="A curses based MongoDB browser",
      long_description=readme(),
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Environment :: Console :: Curses',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Programming Language :: Python :: 2.7',
          'Topic :: Database :: Front-Ends',
      ],
      keywords='curses ncurses mongo mongodb browser',
      url='http://github.com/gnublade/cursedmongo',
      author='Andy Kilner',
      author_email='gnublade@gmail.com',
      license='GPL',
      packages=['cursedmongo'],
      entry_points = {
          'console_scripts': ['cursedmongo=cursedmongo:main'],
      },
      install_requires=[
          'pymongo >= 2.3',
          'urwid >= 1.0.2',
      ],
      test_suite='unittest2.collector',
      tests_require=[
          'unittest2', 'mock'
      ],
      zip_safe=False)
