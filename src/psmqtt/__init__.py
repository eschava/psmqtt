import psmqtt
from psmqtt.psmqtt_app import PsmqttApp
import sys

def main() -> None:
    app = PsmqttApp()
    ret = app.setup()
    if ret != 0:
        sys.exit(ret)
    sys.exit(app.run())


if __name__ == '__main__':
    main()
