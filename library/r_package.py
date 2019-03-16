#!/usr/bin/python

# Copyright: (c) 2018, Evan Van Dam <evandam92@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
from ansible.module_utils.basic import AnsibleModule
from rpy2 import robjects
from rpy2.robjects.packages import importr


__metaclass__ = type


class RInterface(object):
    """All R communication is done through this class."""
    BASE = importr('base')
    UTILS = importr('utils')
    NULL = robjects.r('NULL')

    def __init__(self, module):
        self.module = module

    def call_r(self, func, *args, **kwargs):
        """Call the R function, with error handling"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.module.fail_json(msg=str(e))

    def require(self, name, lib, **kwargs):
        """Import a package. Return True/False if successful."""
        return self.call_r(self.BASE.require, name, lib_loc=lib, **kwargs)[0]

    def package_version(self, name, lib, **kwargs):
        """Get the version of the package"""
        return self.call_r(
            self.UTILS.packageVersion, name, lib_loc=lib, **kwargs
        )[0]

    def is_present(self, name, lib, version=None):
        """Check if the package is installed.

        Compare versions of the target and installed package if specified.
        """
        if not self.require(name, lib):
            return False
        if version is not None:
            installed_version = self.package_version(name, lib)
            return version == installed_version[:len(version)]
        return True

    def install_packages(self, packages, lib, **kwargs):
        """Install a list of packages into the lib"""
        # install.packages only throws warnings if a package fails...
        # Set warns to act as errors
        pkg_vector = robjects.StrVector(packages)
        self.BASE.options(warn=2)
        res = self.call_r(
            self.UTILS.install_packages, pkg_vector, lib=lib, **kwargs
        )
        self.BASE.options(warn=1)
        return res

    def install_version(self, package, version, lib, **kwargs):
        """Install a specific version of a package"""
        return self.call_r(
            robjects.r('devtools::install_version'), package, version=version, lib=lib, **kwargs
        )

    def remove_packages(self, packages, lib, **kwargs):
        """Remove packages from the lib"""
        pkg_vector = robjects.StrVector(packages)
        return self.call_r(
            self.UTILS.remove_packages, pkg_vector, lib=lib, **kwargs
        )

    def get_present_packages(self, packages, lib, check_version=True):
        """Return the subset of packages that are already present."""
        present_packages = []
        for p in packages:
            if self.is_present(p['name'], lib, p['version'] if not check_version else None):
                present_packages.append(p)
        return present_packages

    def get_absent_packages(self, packages, lib, check_version=True):
        """Return the subset of packages that are already absent."""
        absent_packages = []
        for p in packages:
            if not self.is_present(p['name'], lib, p['version'] if not check_version else None):
                absent_packages.append(p)
        return absent_packages


def split_version_names(packages, default_version):
    """Split versioned names like dplyr=0.5 into a dict with name and version."""
    split_default = default_version.split('.') if default_version else None
    for package in packages:
        if '=' in package:
            name, version = package.split('=')
            yield {'name': name, 'version': version.split('.')}
        else:
            yield {'name': package, 'version': split_default}


def install_packages(R, packages, lib, **kwargs):
    """Install packages and specific versions if needed."""
    # Check if any versions are specified
    unversioned_packages = [p for p in packages if not p['version']]
    versioned_packages = [p for p in packages if p['version']]
    if unversioned_packages:
        R.install_packages([p['name'] for p in unversioned_packages], lib, **kwargs)
    if versioned_packages:
        for package in versioned_packages:
            version_str = '.'.join(package['version'])
            R.install_version(package['name'], version_str, lib, **kwargs)


def remove_packages(R, packages, lib):
    """Remove packages from R."""
    R.remove_packages([p['name'] for p in packages], lib)


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        name=dict(required=True, type='list'),
        state=dict(choices=['present', 'absent'], default='present'),
        src=dict(required=False),
        version=dict(required=False),
        type=dict(default='source'),
        repos=dict(type='list', default='http://cran.r-project.org'),
        lib=dict(required=False),
        ncpus=dict(default=1, type='int')
    )

    # seed the result dict in the object
    result = dict(
        changed=False,
        packages=[],
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    R = RInterface(module)

    names = module.params['name']
    state = module.params['state']
    src = module.params['src']
    package_type = module.params['type']
    repos = robjects.StrVector(module.params['repos'])
    lib = module.params['lib']
    ncpus = module.params['ncpus']

    if len(names) > 1 and src:
        module.fail_json(msg='Specifying a list of packages and a src together is not supported.')
    if lib is None:
        lib = R.NULL

    packages = split_version_names(names, module.params['version'])

    # Install packages
    if state == 'present':
        absent_packages = R.get_absent_packages(packages, lib)
        if absent_packages:
            if not module.check_mode:
                try:
                    install_packages(R, absent_packages,
                                     type=package_type,
                                     repos=repos,
                                     lib=lib,
                                     Ncpus=ncpus)
                except ValueError as e:
                    module.fail_json(msg=str(e))
            result['changed'] = True
            result['packages'] = absent_packages
    # Remove packages
    elif state == 'absent':
        present_packages = R.get_present_packages(packages, lib, check_version=False)
        if present_packages:
            if not module.check_mode:
                remove_packages(R, present_packages, lib)
            result['changed'] = True
            result['packages'] = present_packages

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
