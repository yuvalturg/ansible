#!/usr/bin/python

# https://github.com/ansible/ansible/issues/21185

# Copyright: (c) 2018, Dusty Mabe <dusty@dustymabe.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish
from __future__ import absolute_import, division, print_function

import json
import shlex

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import b
from ansible.module_utils.yumdnf import YumDnf, yumdnf_argument_spec

__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: rpm_ostree

short_description: A module for a few rpm-ostree operations

version_added: "2.X"

description:
    - "A module for a few rpm-ostree operations"

options:
    name:
        description:
            - This is the message to send to the sample module
        required: true
    state:
    install:
        description:
            - Packages to install on the system
    new:
        description:
            - Control to demo if the result of this module is changed or not
        required: false

author:
    - Dusty Mabe <dusty@dustymabe.com>
'''

EXAMPLES = '''
# pass in a message and have changed true
- name: Test with a message and changed output
  rpm-ostree:
    name: hello world
    new: true
'''

RETURN = '''
original_message:
    description: The original name param that was passed in
    type: str
message:
    description: The output message that the sample module generates
'''


class RpmOSTreeModule(YumDnf):
    def __init__(self, module):
        super(RpmOSTreeModule, self).__init__(module)
        self.pkg_mgr_name = 'rpm_ostree'

    def _list_packages(self, res):
        rpmbin = self.module.get_bin_path('rpm', required=True)
        qfmt = ('\{'
                '"epoch":"%{epochnum}",'
                '"name":"%{name}",'
                '"version":"%{version}",'
                '"release":"%{release}",'
                '"arch":"%{arch}",'
                '"nevra":"%{nevra}"'
                '\},')
        cmd = [rpmbin, '-q', '--qf', qfmt, self.list]
        if self.installroot != '/':
            cmd.extend(['--root', self.installroot])
        
        lang_env = dict(LANG='C', LC_ALL='C', LC_MESSAGES='C')
        rc, out, err = self.module.run_command(cmd, environ_update=lang_env)
        if rc != 0 and 'is not installed' not in out:
            self.module.fail_json(msg='Error from rpm: %s: %s' % (cmd, err))
        if 'is not installed' in out:
            out = ''
        res["results"] = json.loads("[{}]".format(out[:-1]))

    def _rpm_ostree_cmd(self, action, res):
        rpm_ostree = self.module.get_bin_path('rpm-ostree', required=True)
        cmd = [rpm_ostree, action, "--allow-inactive", "--idempotent",
               "--unchanged-exit-77"] + self.names
        
        rc, out, err = self.module.run_command(cmd, encoding=None)
        if out is None:
            out = b('')
        if err is None:
            err = b('')
        
        res.update(dict(
            rc     = rc,
            cmd    = cmd,
            stdout = out.rstrip(b("\r\n")),
            stderr = err.rstrip(b("\r\n")),
        ))

        if rc == 0:  # succeeded in making a change
            res['changed'] = True
            res['reboot_required'] = True
        elif rc == 77:  # no change was needed
            res['changed'] = False
            res['rc'] = 0
            res['reboot_required'] = False
        else:
            self.module.fail_json(msg='non-zero return code', **res)

    def run(self):
        res = dict(changed=False, original_message='', message='')
        
        if self.module.check_mode:
            return self.module.exit_json(**res)
        
        if self.list:
            self._list_packages(res)
        elif self.names:
            if self.state in ('installed', 'present', 'latest'):
                self._rpm_ostree_cmd('install', res)
            elif self.state in ('absent', 'removed'):
                self._rpm_ostree_cmd('uninstall', res)
        
        self.module.exit_json(**res)

    def is_lockfile_pid_valid(self):
        return False


def main():
    yumdnf_argument_spec['argument_spec']['use_backend'] = dict(default='auto', choices=['auto', 'yum', 'yum4', 'dnf'])

    module = AnsibleModule(
        **yumdnf_argument_spec
    )

    module_implementation = RpmOSTreeModule(module)
    module_implementation.run()

if __name__ == '__main__':
    main()
