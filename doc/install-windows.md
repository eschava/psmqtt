# Running `psmqtt` on Windows

## Prerequisites

Check for `python` and `pip`:

```
PS C:\Users\asoko\Projects\psmqtt> python --version
Python 3.10.8
PS C:\Users\asoko\Projects\psmqtt> which python
/c/Users/asoko/AppData/Local/Microsoft/WindowsApps/python
PS C:\Users\asoko\Projects\psmqtt> python -m pip --version
pip 22.0.3 from C:\Users\asoko\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\LocalCache\local-packages\Python310\site-packages\pip (python 3.10)
```

Install [smartctl](https://sourceforge.net/projects/smartmontools/files/).
Check for `smartctl`:

```
PS C:\Users\asoko\Projects\psmqtt> smartctl --scan
/dev/sda -d ata # /dev/sda, ATA device
/dev/sdb -d nvme # /dev/sdb, NVMe device
```

## Installation

```
git clone https://github.com/eschava/psmqtt.git
python3 -m pip install -r requirements.txt
```

## First Run

TO BE WRITTEN
