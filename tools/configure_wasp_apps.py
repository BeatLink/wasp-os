#!/usr/bin/env python3
"""Configure the wasp distribution based on the provided wasp.toml config

    This script generates the following files and directories
        wasp/apps/user/
        wasp/boards/manifest_user_apps.py
        wasp/appregistry.py

    Apps and watch faces live in packages, apps/NAME/app.py and
    faces/NAME/app.py, and are copied to wasp/apps/user/NAME.py so the
    firmware sees them as the flat modules apps.user.NAME.
"""

import shutil
import sys
try:
    import tomllib as tomli
except ImportError:
    import tomli


def _snake_case_to_pascal_case(s):
    out = ''
    for word in s.split('_'):
        out = out + word[:1].upper() + word[1:]
    return out


def _module_name(path):
    # apps/NAME/app.py and apps/NAME.py both map to the module NAME.
    parts = path.split('/')
    if parts[-1] == 'app.py' and len(parts) > 1:
        return parts[-2]
    return parts[-1].split('.')[0]


def _class_name(path):
    return _snake_case_to_pascal_case(_module_name(path)) + 'App'


def _display_name(path):
    return _snake_case_to_pascal_case(_module_name(path))


with open(sys.argv[1:][0], 'rb') as config_file:
  config = tomli.load(config_file)

  # Copy selected apps and watch faces to the wasp app user directory
  for app in config.get('app') + config.get('watchface'):
      shutil.copy(app.get('file'), 'wasp/apps/user/' + _module_name(app.get('file')) + '.py')

  # Create the user app manifest containing all user apps and watch faces
  with open('wasp/boards/manifest_user_apps.py', 'w') as manifest_file:
      manifest_file.write('# This file is auto generated from the wasp.toml. Manual changes will be overwritten. \n\n')
      manifest_file.write('manifest = (\n')
      for app in config.get('app') + config.get('watchface'):
          manifest_file.write('    \'' + 'apps/user/' + _module_name(app.get('file')) + '.py\',\n')
      manifest_file.write(')')

  # Create a registry for the os to use to populate its lists
  with open('wasp/appregistry.py', 'w') as reg_file:

    # Software to display in the software app
    reg_file.write('# This file is auto generated from the wasp.toml. Manual changes will be overwritten. \n\n')
    reg_file.write('software_list = (\n')
    for app in config.get('app'):
        if not app.get('quick_ring'):
            app_module_name = 'apps.user.' + _module_name(app.get('file'))
            app_display_name = _display_name(app.get('file'))
            reg_file.write('    (\'' + app_module_name + '\', \'' + app_display_name + '\'),\n')
    reg_file.write(')\n\n')

    # Software to display in the faces app
    reg_file.write('faces_list = (\n')
    for face in config.get('watchface'):
        watchface_module = 'apps.user.' + _module_name(face.get('file'))
        watchface_class = _display_name(face.get('file'))
        reg_file.write('    (\'' + watchface_module + '\',\'' + watchface_class + '\'),\n')
    reg_file.write(')\n\n')


    # Software to be loaded at startup (default watch face, quick ring apps, any apps marked auto_load in the config)
    reg_file.write('autoload_list = (\n')

    # Fist app to autoload should be the default watch face
    default_watchface = None
    for watchface in config.get('watchface'):
        if watchface.get('default'):
            default_watchface = watchface
        elif not default_watchface:
            default_watchface = watchface
    watchface_path = 'apps.user.' + _module_name(default_watchface.get('file')) + '.' + _class_name(default_watchface.get('file'))
    reg_file.write('    (\'' + watchface_path + '\', True, False, True),\n')

    # The next apps should be the quick ring and any auto_load apps (in order specified in the config)
    for app in config.get('app'):
        if (app.get('quick_ring') or app.get('auto_load')):
            app_path = 'apps.user.' + _module_name(app.get('file')) + '.' + _class_name(app.get('file'))
            app_quick_ring = str(not (app.get('quick_ring') is None))
            app_no_except = str(not (app.get('no_except') is None))
            reg_file.write('    (\'' + app_path + '\', ' + app_quick_ring + ', False, ' + app_no_except + '),\n')
    reg_file.write(')\n\n')
