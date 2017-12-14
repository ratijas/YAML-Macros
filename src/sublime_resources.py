from os import path, walk, sep
from zipfile import ZipFile
import glob
import fnmatch
try_st = False # set to False for easier testing of our custom methods when using ST

class SublimeResources():
    platform_data_paths = {
        'Windows': r'%APPDATA%\Sublime Text 3',
        'Linux': r'~/.config/sublime-text-3',
        'Darwin': r'~/Library/Application Support/Sublime Text 3'
    }

    # TODO: probably it would be useful if this method also took an optional argument for a path to check,
    #       to see if it could be part of a data folder, to allow it to also work with portable instances of ST
    #       i.e. given an arg value of H:/STPortable/3156/Data/Packages/JavaScript/JavaScript.sublime-syntax, it
    #       could return H:/STPortable/3156/Data by seeing the /Data/Packages/ part of the path.
    @classmethod
    def get_data_path(cls):
        import platform
        return path.expandvars(SublimeResources.platform_data_paths[platform.system()])

    @classmethod
    def find_resources(cls, glob_pattern):
        """
            find all files that match the given glob, by searching through:
            - loose files in the data Packages folder
            - files in a .sublime-package file in the Installed Packages folder
            - files in a .sublime-package file in the ST installation Packages folder
              (where no .sublime-package file with the same name exists in the Installed Packages folder)
            and then sort them according to lexographical order (ignoring duplicates results)
             (except with Default coming first and User last)
        """
        try:
            if try_st:
                from sublime import find_resources as sublime_find_resources
                return sublime_find_resources(glob_pattern)
        except ImportError:
            pass

        data_path = SublimeResources.get_data_path()
        matches = list()
        
        # loose files in the data Packages folder
        package_name = ''
        # if the glob pattern contains a package name, then only search the relevant package
        if glob_pattern.startswith('Packages/') and not glob_pattern.startswith('Packages/*'):
            package_name, glob_pattern = SublimeResources.split_package_filepath(glob_pattern)
        #matches += glob.glob(path.join(data_path, 'Packages', package_name), glob_pattern, recursive=True) # Python 3.3 doesn't support this arg - https://stackoverflow.com/a/2186565/4473405
        for root, dirnames, filenames in walk(path.join(data_path, 'Packages', package_name), followlinks=True):
            for match in fnmatch.filter([path.join(root, filename)[len(path.join(data_path, '')):] for filename in filenames], glob_pattern):
                # switch matches to use `/` folder sep if necessary (i.e. on Windows)
                if sep == '\\':
                    match = match.replace('\\', '/')
                matches.append(match)
        
        # for each .sublime-package file in the Installed Packages folder
        if package_name == '':
            package_name = '*'
        for zipfile_path in glob.iglob(path.join(data_path, 'Installed Packages', package_name + '.sublime-package')):
            matches += SublimeResources.find_files_matching_glob_in_zip(zipfile_path, glob_pattern)
        
        # TODO: search Packages subfolder of ST installation folder, where no .sublime-package file with the same name exists in the Installed Packages folder)
        pass
        
        # use a set to remove duplicates - no such thing as an ordered set in Python 3.3, so convert back to a list
        matches = list(set(matches))
        return sorted(matches, key=SublimeResources.get_sortkey_for_package_filepath)

    @classmethod
    def find_files_matching_glob_in_zip(cls, zipfile_path, glob_pattern):
        package_name = path.splitext(path.basename(zipfile_path))[0]
        # get a list of files in the zip
        files = SublimeResources.get_files_in_zip(zipfile_path)
        # format the path to be relative from the Packages folder
        files = ['Packages/' + package_name + '/' + file for file in files]
        # find any that match the glob
        return [file for file in files if fnmatch.fnmatchcase(file, glob_pattern)]

    @classmethod
    def split_package_filepath(cls, package_path):
        """Return a tuple with 2 args - the package name and the sub path inside the package."""
        return package_path[len('Packages/'):].split('/', 1)

    @classmethod
    def get_sortkey_for_package_filepath(cls, file_path):
        package_name, sub_path = SublimeResources.split_package_filepath(file_path)
        index = 1
        if package_name == 'Default':
            index = 0
        elif package_name == 'User':
            index = 2
        return str(index) + '/' + package_name + '/' + sub_path

    @classmethod
    def load_resource(cls, package_path):
        try:
            if try_st:
                from sublime import load_resource as sublime_load_resource
                return sublime_load_resource(package_path)
        except ImportError:
            pass

        if package_path.startswith('Packages/'):
            data_path = SublimeResources.get_data_path()
            
            # if the file exists in the Packages folder, return that
            full_path = path.join(data_path, package_path)
            if path.isfile(full_path):
                with open(full_path, 'r', encoding='utf-8') as file:
                    return file.read()
            
            # otherwise, it must exist in a .sublime-package file, if at all
            # so find the Package name, and the path inside the zip file
            package_name, sub_path = SublimeResources.split_package_filepath(package_path)
            
            # look in the relevant Installed Packages .sublime-package file, if it exists
            full_path = path.join(data_path, 'Installed Packages', package_name + '.sublime-package')
            if path.isfile(full_path):
                return SublimeResources.get_file_from_zip(full_path, sub_path)
            
            # TODO: otherwise, try the ST installation path
            pass

        raise IOError('resource not found')

    @classmethod
    def get_files_in_zip(cls, zipfile_path):
        with ZipFile(zipfile_path, 'r') as z:
            return z.namelist()

    @classmethod
    def get_file_from_zip(cls, zipfile_path, path_inside_zip):
        with ZipFile(zipfile_path, 'r') as z:
            with z.open(path_inside_zip, 'r') as file:
                return file.read()
