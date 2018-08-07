#!/usr/bin/env python3
# Copyright (C) 2017  Ghent University
# Copyright (C) 2017  Qrama
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# pylint: disable=C0111,C0103,c0325
from base64 import b64decode
from subprocess import call, check_call
from os.path import expanduser

# Charm pip dependencies
import yaml

from charmhelpers.core.hookenv import (
    config,
)
from charms.reactive import set_state, when_not, when

USER = config()['user']
HOME = expanduser('~{}'.format(USER))


@when_not('juju.installed')
@when('snap.installed.juju')
def set_juju_installed_state():
    # Allows the use of the juju cli command in new sessions
    call(['ln', '-s', '/snap/bin/juju', '/usr/bin/juju'])
    # Run juju once to generate initial config
    check_call([
        'su', USER, '-c',
        'juju'])
    set_state('juju.installed')


@when('juju.installed')
@when('config.changed.accounts_yaml')
def import_accounts():
    accounts_file = "{}/.local/share/juju/accounts.yaml".format(HOME)
    data = config()['accounts_yaml']
    if data != '':
        accounts = yaml.load(b64decode(data))
        merge_yaml_file_and_dict(accounts_file, accounts)
    set_state('juju.accounts.available')


@when('juju.installed')
@when('config.changed.controllers_yaml')
def import_controllers():
    controllers_file = "{}/.local/share/juju/controllers.yaml".format(HOME)
    data = config()['controllers_yaml']
    if data != '':
        controllers = yaml.load(b64decode(data))
        merge_yaml_file_and_dict(controllers_file, controllers)
    set_state('juju.controller.available')


@when('juju.installed')
@when('config.changed.models_yaml')
def import_models():
    models_file = "{}/.local/share/juju/models.yaml".format(HOME)
    data = config()['models_yaml']
    if data != '':
        models = yaml.load(b64decode(data))
        merge_yaml_file_and_dict(models_file, models)
    set_state('juju.model.available')


def merge_yaml_file_and_dict(filepath, datadict):
    open(filepath, "a").close()  # to fix "file doesn't exist"
    with open(filepath, 'r+') as e_file:
        filedict = yaml.load(e_file) or {}
        filedict = deep_merge(filedict, datadict)
        e_file.seek(0)  # rewind
        e_file.write(yaml.dump(filedict, default_flow_style=False))


class MergerError(Exception):
    pass


def deep_merge(a, b):
    """merges b into a and return merged result

    NOTE: tuples and arbitrary objects are not handled as it is totally
    ambiguous what should happen
    source: https://stackoverflow.com/questions/7204805"""
    key = None
    # ## debug output
    # sys.stderr.write("DEBUG: {} to {}\n".format(b,a))
    try:
        if (a is None or
                isinstance(a, str) or
                isinstance(a, str) or
                isinstance(a, int) or
                isinstance(a, float)):
            # border case for first run or if a is a primitive
            a = b
        elif isinstance(a, list):
            # lists can be only appended
            if isinstance(b, list):
                # merge lists
                a.extend(b)
            else:
                # append to list
                a.append(b)
        elif isinstance(a, dict):
            # dicts must be merged
            if isinstance(b, dict):
                for key in b:
                    if key in a:
                        a[key] = deep_merge(a[key], b[key])
                    else:
                        a[key] = b[key]
            else:
                raise MergerError(
                    'Cannot merge non-dict "{}" into dict "{}"'.format(b, a)
                )
        else:
            raise MergerError('NOT IMPLEMENTED "{}" into "{}"'.format(b, a))
    except TypeError as e:
        raise MergerError('TypeError "{}" in key "{}" when merging "{}" \
                           into "{}"'.format(e, key, b, a))
    return a
