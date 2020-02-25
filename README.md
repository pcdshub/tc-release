Intro
=====

https://confluence.slac.stanford.edu/display/PCDS/Releasing+Pytmc+TwinCAT+Project+IOCs

and more specifically:
https://confluence.slac.stanford.edu/display/PCDS/Automated+Tagging+for+TwinCAT+Projects


Installing
==========

```bash
$ git clone https://github.com/pcdshub/tc_release
$ cd tc_release
$ pip install .
```

Running
=======

```bash
$ tc-release
usage: tc-release [-h] [--plcproj PLCPROJ] [--dry-run] VERSION NUMBER repo_url
```

Building the exe
================

1. Install pyinstaller and pywin32
    ```
    conda install -c conda-forge pyinstaller
    conda install -c anaconda pywin32
    ```

2. Build exe
    ```
    pyinstaller tc_release
    ```
