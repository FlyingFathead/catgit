import re
from setuptools import setup, find_packages

# Extract the version number from catgit.py
def get_version():
    with open('catgit/catgit.py', 'r') as file:
        for line in file:
            match = re.search(r'^version_number\s*=\s*[\'"]([^\'"]+)[\'"]', line)
            if match:
                return match.group(1)
    raise RuntimeError("Unable to find version string in catgit.py! Make sure you have the git repo cloned properly from: https://github.com/FlyingFathead/catgit")

setup(
    name='catgit',
    version=get_version(),  # Use the extracted version
    author='FlyingFathead',
    author_email='flyingfathead@protonmail.com',
    packages=find_packages(),
    package_data={
        'catgit': ['config.ini'],  # Include config.ini within the catgit package
    },
    entry_points={
        'console_scripts': [
            'catgit = catgit.catgit:main'
        ]
    },
    url='https://github.com/FlyingFathead/catgit',
    license='LICENSE',
    description='A utility to display Git repository contents in a terminal or an editor.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        # Dependencies coming if need be
    ],
)
