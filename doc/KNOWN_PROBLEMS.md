# Known Problems

## Use of smartctl

Invoking `smartctl` to retrieve hard drive temperatures requires root
privileges.  It is a very BAD idea to run python code with such privileges.
