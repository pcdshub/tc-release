import argparse
import contextlib
import shutil
import subprocess
import os, re, fnmatch, getpass, stat, os.path
import logging
import uuid
from lxml import etree

username = getpass.getuser()
local_git_install = 'C:\\Users\\{user}\\AppData\\Local\\Programs\\Git\\'.format(
        user = username
    )

if os.path.exists(local_git_install):
    os.environ['GIT_PYTHON_GIT_EXECUTABLE'] = local_git_install+'mingw64\\bin\\git.exe'
    os.environ['GIT_SSH'] = local_git_install+'usr\\bin\\ssh.exe'
from git import Repo


#Working directory
dirname = '~tc-release-tmp'
working_dir =os.path.join(os.getcwd(), dirname)

GlobalVersion_TcGVL = '''\
<TcPlcObject Version="1.1.0.1" ProductVersion="3.1.4022.10">
  <GVL Name="Global_Version" Id="{c1e6c8db-11ef-4bd5-8510-07e605ee5d06}">
    <Declaration><![CDATA[{attribute 'TcGenerated'}
// This function has been automatically generated from the project information.
VAR_GLOBAL CONSTANT
    {attribute 'const_non_replaced'}
    {attribute 'linkalways'}
    stLibVersion_LCLS_General : ST_LibVersion := (iMajor := 0, iMinor := 1, iBuild := 4, iRevision := 0, sVersion := '0.1.4');
END_VAR
]]></Declaration>
  </GVL>
</TcPlcObject>
'''


def parse_args():
    parser = argparse.ArgumentParser(description='Properly tags/version your TC project with GIT')
    parser.add_argument('version_string', metavar='VERSION NUMBER', type=str,
                            help='Version number must be vMAJOR.MINOR.BUGFIX')
    parser.add_argument('repo_url', type=str,
                        help='URL or path to the repo (for cloning)')
    parser.add_argument('--plcproj', default='',
                        help=('If multiple PLC projects in the repo, specify '
                              'which one to set the version number on.'))
    parser.add_argument('--deploy', action='store_true',
                        help=('Also make and deploy the IOC if applicable.'))
    parser.add_argument('--dry-run', action='store_true',
                        help=('Run without pushing back to the repo and '
                              'without cleaning up the checkout directory.'))
    return parser.parse_args()


def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

#Workaround for Windows file lock issues
def remove_readonly(func, path, _):
    "Clear the readonly bit and reattempt the removal"
    os.chmod(path, stat.S_IWRITE)
    func(path)


@contextlib.contextmanager
def pushd(new_dir):
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    yield
    os.chdir(previous_dir)


def find_makefiles(directory):
    """
    Find the subdirectories that contain Makefiles.

    This will do a depth-first walk of the directory tree, accumulating a
    directory name whenever a file named "Makefile" is found, and pruning the
    search path at these directories to avoid double-counting any
    sub-Makefiles.

    An assumption is made that a Makefile will, in itself, trigger any
    Makefiles in subdirectories from that point in the directory tree.

    Parameters
    ----------
    directory : str
        The parent directory to use as the starting point for the depth-first
        search.

    Returns
    -------
    make_dirs : list of str
        The highest-level directories that contain files named "Makefile".
    """
    walker = os.walk(directory)
    make_dirs = []

    # Find the first Makefile in every branch of the directory tree
    for dirpath, dirnames, filenames in walker:
        if 'Makefile' in filenames:
            make_dirs.append(dirpath)
            # Stop searching this branch if we found a Makefile
            dirnames.clear()
            continue
        # Skip the version control directory
        try:
            dirnames.remove('.git')
        except ValueError:
            pass

    return make_dirs


def deploy(repo_url, tag, directory):
    """
    Clone a repo to a specific directory at a specific tag, then build the IOC

    This will find the highest-level Makefile in the directory tree, then
    shell out to call 'make'.

    If more than one such file exists, we will make all of them.

    Parameters
    ----------
    repo_url : str
        The repo specification to clone from.
        For example: git@github.com:pcdshub/tc_release.git

    tag : str
        The tag to deploy, e.g. v1.0.0

    directory : str
        The parent directory to deploy to. We will automatically create a
        subdirectory with the name of the tag.
        For example: directory=/cds/group/epics/ioc/kfe/my_plc
        would deploy to /cds/group/epics/ioc/kfe/my_plc/v1.0.0
    """
    # Clone the repo
    deploy_dir = os.path.join(directory, tag)
    Repo.clone_from(repo_url, deploy_dir, depth=1, branch=tag)

    # Find the makefiles
    make_dirs = find_makefiles(deploy_dir)

    # Make all the makefiles
    for make_dir in make_dirs:
        with pushd(make_dir):
            subprocess.run('make')


def _main(args=None):
    #Create a temp directory, and clone the repo, and check out master

    logging.info('Creating working directory: %s', working_dir)
    logging.info('Initializing bare git repo, establishing remote, and checking out master')
    repo = Repo.init(working_dir)
    logging.info('Adding remote')
    logging.debug('Working directory: %s, Repo: %s' % (working_dir, args.repo_url) )
    origin = repo.create_remote('origin', str(args.repo_url))

    assert origin.exists()

    origin.fetch()

    repo.create_head('master', origin.refs.master)

    repo.heads.master.checkout()

    repo.heads.master.set_tracking_branch(origin.refs.master)

    #Check format of version_number
    projectVersion_pattern = re.compile(r'v([\d.]+)')
    version_string = re.search(projectVersion_pattern, args.version_string).group(1)
    if not version_string:
        print('Error, version string does not match format "vX.X.X"')
        exit(1)

    #Inject version_number into .tcproj
    #Find .tcproj

    logging.info('Looking for .plcproj')
    plcproj_path = find('*.plcproj', working_dir)

    if not len(plcproj_path):
        print('Error, did not find .plcproj file.')
        exit(1)
    elif args.plcproj:
        for i, proj in enumerate(plcproj_path):
            if args.plcproj == os.path.split(proj)[1].split('.')[0]:
                plcproj_file = plcproj_path[i]
                break
        else:
            print(('Error, did not find specified file '
                   '{}.plcproj'.format(args.plcproj)))
            exit(1)
    elif len(plcproj_path) > 1:
        print('Error, found multiple .plcproj files.')
        exit(1)
    else:
        plcproj_file = plcproj_path[0]

    #Getting our xml structure to work with
    logging.info('Parsing plcproj')
    plcproj_tree = etree.parse(plcproj_file)

    plcproj_root = plcproj_tree.getroot()

    nsmap = plcproj_root.nsmap

    #Getting the ProjectVersion, Company, Author and Title tags
    projectVersion_tag = plcproj_root.find('.//ProjectVersion', nsmap)
    company_tag = plcproj_root.find('.//Company', nsmap)
    author_tag = plcproj_root.find('.//Author', nsmap)
    title_tag = plcproj_root.find('.//Title', nsmap)

    logging.info('Updating plcproj with version number: %s', version_string)
    #Adding version string to plcproj
    projectVersion_tag.text = version_string

    #To make this verson number available in the PLC runtime, we must add the Version/Global_Version.TcGVL to the project
    #Whether one exists or not, doesn't matter. We always just create one.
    #To start, we need the TC version of the project and the current TcPlcObject version.
    #We can get this info for scanning for a .TcPOU in the project files (there has to be at least one), and extracting these tags

    logging.info('Creating Global_Version.TcGVL')
    pouFiles = find('*.TcPOU', working_dir)
    pouTree = etree.parse(pouFiles[0])
    pouRoot = pouTree.getroot()

    TcPlcObject_PRODUCT_VERSION = pouRoot.get('ProductVersion')
    TcPlcObject_VERSION = pouRoot.get('Version')

    GlobalVersion_TcGVL_root = etree.XML(GlobalVersion_TcGVL)
    GlobalVersion_TcGVL_tree = etree.ElementTree(element=GlobalVersion_TcGVL_root)

    GlobalVersion_TcGVL_attributes = GlobalVersion_TcGVL_root.attrib

    GlobalVersion_TcGVL_attributes['ProductVersion'] = TcPlcObject_PRODUCT_VERSION
    GlobalVersion_TcGVL_attributes['Version'] = TcPlcObject_VERSION

    #We should also change the GUID, just to be nice.
    gvl_attrib = GlobalVersion_TcGVL_root.find('.//GVL').attrib

    try:
        gvl_attrib['Id'] = str(uuid.uuid4())
    except KeyError:
        print('Error, could not find Id attribute in GVL tag...')
        exit(1)

    #Now we modify the title and version numbers
    declaration = GlobalVersion_TcGVL_root.find('.//Declaration')
    declaration_text = declaration.text

    split_version_string = version_string.split('.')
    major = split_version_string[0]
    minor = split_version_string[1]
    build = split_version_string[2]
    if len(split_version_string)>3:
        revision = split_version_string[4]
    else:
        revision = '0'


    pattern = re.compile(r"stLibVersion_(?P<title>.+)\s?:\s?ST_LibVersion.+iMajor.+(?P<major>\d+).+iMinor.+(?P<minor>\d+).+iBuild.+(?P<build>\d+).*iRevision.+(?P<revision>\d+).+sVersion.+'(?P<version_string>.+)'.+;")
    replacement_string = "stLibVersion_{title} : ST_LibVersion := (iMajor := {iMajor}, iMinor := {iMinor}, iBuild := {iBuild}, iRevision := {iRevision}, sVersion := '{sVersion}');".format(
        iMajor = major,
        iMinor = minor,
        iBuild = build,
        iRevision = revision,
        sVersion = version_string,
        title = str(title_tag.text).replace(' ', '_').replace('-', '_')
    )

    declaration.text = etree.CDATA( pattern.sub(replacement_string, declaration_text) )#Note, using the declaration.text not _ to write it back
    #Also note the use of the CDATA wrapper, this is stripped by .text, so we need to restore it.

    #Add this file to the project by adding a Version/ folder and Global_Version.TcGVL file and linking in the .tcproj
    #Creating file and folder
    logging.info('Writing Global_Version.TcGVL to file')
    version_dir = os.path.join( os.path.dirname(plcproj_file), 'Version' )
    os.makedirs( version_dir, exist_ok=True )
    GV_TcGVL_file = os.path.join(version_dir, 'Global_Version.TcGVL')

    GlobalVersion_TcGVL_tree.write(GV_TcGVL_file, encoding='utf-8', xml_declaration=True)
    logging.info('File created successfully: %s', GV_TcGVL_file)

    #Linking in the .plcproj
    logging.info('Linking Global_Version.TcGVL into plcproj')

    #Check if Version folder is already linked, if not add it
    if not plcproj_root.find(".//ItemGroup/Folder[@Include='Version']", nsmap):
        folder = plcproj_root.find('.//ItemGroup/Folder', nsmap)
        folder.addnext(etree.XML('<Folder Include="Version" />'))

    #Check if Compile Include if not add it (it better already be there)
    if not plcproj_root.find('.//ItemGroup/Compile[@Include="Version\Global_Version.TcGVL"]', nsmap):
        compile_include = plcproj_root.find('.//ItemGroup/Compile', nsmap)
        compile_include.addnext( etree.XML('''\
        <Compile Include="Version\Global_Version.TcGVL">
            <SubType>Code</SubType>
        </Compile>
        '''))

    #Writing new plcproj to disk
    logging.info('Writing updated .plcproj to file')
    plcproj_tree.write(plcproj_file, encoding='utf-8', xml_declaration=True)
    logging.info('.plc project has been updated')

    #Commit changes
    repoIndex = repo.index
    repoIndex.add([GV_TcGVL_file])
    repoIndex.add([plcproj_file])
    repoIndex.write()

    logging.info('Committing changes')
    commit_message = "Tagging version {version}".format(version=args.version_string)
    newCommit = repoIndex.commit(commit_message, skip_hooks=True)

    #Tag this commit
    repo.create_tag(args.version_string, ref='HEAD', message=commit_message)

    #Push commit
    #--tags is not ideal, but since this is the only tag we're creating in this temp area, it should be safe
    if not args.dry_run:
        pushStatus = origin.push(tags=True)
        logging.info('Push complete')
        repo.close()
        return pushStatus


def main():
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    try:
        _main(args)
    finally:
        if not args.dry_run:
            logging.info('Cleaning up')
            shutil.rmtree(working_dir, onerror=remove_readonly)


if __name__ == "__main__":
    main()
