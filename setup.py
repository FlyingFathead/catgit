from setuptools import setup, find_packages

setup(
    name='catgit',
    version='0.10',
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
