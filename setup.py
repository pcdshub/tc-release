from setuptools import setup, find_packages
import versioneer


with open('requirements.txt', 'rt') as f:
    requirements = f.read().splitlines()

requirements = [r for r in requirements if not r.startswith('git+')]

setup(
    name='tc_release',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license='BSD',
    author='SLAC National Accelerator Laboratory',
    install_requires=requirements,
    packages= find_packages(),
    description='A TwinCAT project release tool',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'tc_release = tc_release.tc_release:main'
        ]
    }
  )
