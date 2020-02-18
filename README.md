Intro
=====

https://confluence.slac.stanford.edu/display/PCDS/Automated+Tagging+for+TwinCAT+Projects

Building the exe
================

1. Install pyinstaller and pywin32
    ```
    conda install -c conda-forge pyinstaller
    conda install -c anaconda pywin32
    ```

2. Build exe
    ```
    pyinstaller --onefile tc_release.py
    ```
