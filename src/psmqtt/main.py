#!/usr/bin/env python
#
# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.
#
# This is the entrypoint of the project:
# 1. Reads configuration pointed to by PSMQTTCONFIG env var, or use `psmqtt.conf`
#    by default.
# 2. Extracts from config file settings, e.g. mqtt broker and schedule.
# 2. Executes schedule...
# 3. Performs tasks from the schedule, which involves reading sensors and sending
#    values to the broker
#

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
