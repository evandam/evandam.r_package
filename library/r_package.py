#!/usr/bin/python

# Copyright: (c) 2018, Evan Van Dam <evandam92@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import os
import json
from ansible.module_utils.basic import AnsibleModule
from rpy2 import robjects
from rpy2.robjects.packages import importr

__metaclass__ = type


R_BASE = importr('base')
R_UTILS = importr('utils')


def split_version_names(packages, default_version):
    """Split versioned names like dplyr=0.5 into a dict with name and version."""
    split_default = default_version.split('.') if default_version else None
    for package in packages:
        if '=' in package:
            name, version = package.split('=')
            yield {'name': name, 'version': version.split('.')}
        else:
            yield {'name': package, 'version': split_default}


def is_present(name, version=None):
    """Check if the package is installed.

    Compare versions of the target and installed package if specified.
    """
    if not R_BASE.require(name)[0]:
        print('%s is not installed!' % name)
        return False
    elif version is not None:
        installed_version = R_UTILS.packageVersion(name)[0]
        return version == installed_version[:len(version)]
    return True


def get_present_packages(packages, check_version=True):
    """Return the subset of packages that are already present."""
    present_packages = []
    for p in packages:
        if is_present(p['name'], p['version'] if not check_version else None):
            present_packages.append(p)
    return present_packages


def get_absent_packages(packages, check_version=True):
    """Return the subset of packages that are already absent."""
    absent_packages = []
    for p in packages:
        if not is_present(p['name'], p['version'] if not check_version else None):
            absent_packages.append(p)
    return absent_packages


def install_packages(packages, repo):
    """Install packages and specific versions if needed."""
    # Check if any versions are specified
    unversioned_packages = [p for p in packages if not p['version']]
    versioned_packages = [p for p in packages if p['version']]
    if unversioned_packages:
        pkg_vector = robjects.StrVector([p['name'] for p in unversioned_packages])
        R_UTILS.install_packages(pkg_vector,repo=repo)
    if versioned_packages:
        devtools = importr('devtools')
        for package in versioned_packages:
            devtools.install_version(package['name'], '.'.join(package['version']))


def remove_packages(packages):
    """Remove packages from R."""
    R_UTILS.remove_packages([p['name'] for p in packages])


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        name=dict(required=True, type='list'),
        state=dict(choices=['present', 'absent'], default='present'),
        version=dict(required=False),
        repo=dict(default='http://cran.r-project.org')
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

    names = module.params['name']
    state = module.params['state']
    repo = module.params['repo']

    packages = split_version_names(names, module.params['version'])

    # Install packages
    if state == 'present':
        absent_packages = get_absent_packages(packages)
        if absent_packages:
            if not module.check_mode:
                install_packages(absent_packages, repo)
            result['changed'] = True
            result['packages'] = absent_packages
    # Remove packages
    elif state == 'absent':
        present_packages = get_present_packages(packages, check_version=False)
        if present_packages:
            if not module.check_mode:
                remove_packages(present_packages)
            result['changed'] = True
            result['packages'] = present_packages

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()