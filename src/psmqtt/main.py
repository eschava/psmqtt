#!/usr/bin/env python
#
# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.
#
# This is the entrypoint of the project which just allocates the PsmqttApp class
# and calls its setup() and run() methods. It also exits with the right exit code.
#
# Note that the main() function of this module is referenced by pyproject.toml and used
# to build the Python wheel package

from .psmqtt_app import PsmqttApp
import sys

def main() -> None:
    app = PsmqttApp()
    ret = app.setup()
    if ret > 0:
        sys.exit(ret)
    if ret == -1:  # version has been requested (and already printed)
        sys.exit(0)
    sys.exit(app.run())


if __name__ == '__main__':
    main()
