from setuptools import find_packages, setup

import versioneer

with open('requirements.txt', 'rt') as f:
    requirements = f.read().splitlines()

requirements = [r for r in requirements if not r.startswith('git+')]

# package_data is required for source distributions
with open('MANIFEST.in', 'rt') as f:
    manifest = f.read().splitlines()

# Remove the "include" from the manifest to get filenames
files = [m.split(' ')[1] for m in manifest]
# Only include contents of tc_release folder
files = [f.split('/')[1] for f in files if 'tc_release' in f]
package_data = {'tc_release': files}

setup(
    name='tc_release',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license='BSD',
    author='SLAC National Accelerator Laboratory',
    install_requires=requirements,
    packages=find_packages(),
    description='A TwinCAT project release tool',
    include_package_data=True,
    package_data=package_data,
    entry_points={
        'console_scripts': [
            'tc-release = tc_release.tc_release:main'
        ]
    }
  )
