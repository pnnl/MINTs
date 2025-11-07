from setuptools import setup

package_structure = [
    'mints'
]

requirements = ['simpy',
                'numpy',
                'pandas',
                'recordtype',
                'matplotlib'
]

setup(
    version='1.0',
    name='mints',
    packages=package_structure,
    setup_requires=requirements,
    install_requires=requirements,
)