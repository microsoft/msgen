try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# The version string is stored in only one place
#   so get it from msgen.py.
from msgen_cli.msgen import VERSION as msgen_version

with open('README.rst') as readme:
    long_description = ''.join(readme).strip()

setup(
    name='msgen',
    version=msgen_version,
    author='Microsoft Corporation, Microsoft Genomics Team',
    author_email='msgensupp@microsoft.com',
    description='Microsoft Genomics Command-line Client',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    platforms='any',
    url='https://github.com/MicrosoftGenomics/msgen',
    license='MIT',
    packages=['msgen_cli'],
    py_modules=['msgen_cli.msgen'],
    entry_points={
        'console_scripts': 'msgen=msgen_cli.msgen:main',
    },
    install_requires=[
        'azure-storage==0.32.0',
        'requests>=2.11.1',
    ],
    classifiers=[
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='azure genomics',
)
