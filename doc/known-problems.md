# Known Problems

## Use of smartctl

Invoking `smartctl` to retrieve hard drive temperatures requires root
privileges.
It is a very BAD idea to run python code with such privileges.

The [Docker installation](install-docker.md) document contains
a detailed explanation of which flags to use to limit the
permissions granted to `psmqtt` and to `smartctl` to the minimum
(see `SYS_RAWIO` Linux capability in particular).

