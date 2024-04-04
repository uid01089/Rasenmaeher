from __future__ import annotations

from enum import Enum
import logging
from pathlib import Path
import time
import os
import paho.mqtt.client as pahoMqtt
from PythonLib.JsonUtil import JsonUtil
from PythonLib.Mqtt import Mqtt
from PythonLib.DateUtil import DateTimeUtilities
from PythonLib.Scheduler import Scheduler

# https://www.robonect.de/viewtopic.php?f=10&t=2535

logger = logging.getLogger('Automower')


class MowerMode(Enum):
    AUTO = 0
    MANUELL = 1
    HOME = 2
    DEMO = 3


class Module:
    def __init__(self) -> None:
        self.scheduler = Scheduler()
        self.mqttClient = Mqtt("koserver.iot", "/house/agents/Automower", pahoMqtt.Client("Automower"))

    def getScheduler(self) -> Scheduler:
        return self.scheduler

    def getMqttClient(self) -> Mqtt:
        return self.mqttClient

    def setup(self) -> None:
        self.scheduler.scheduleEach(self.mqttClient.loop, 500)

    def loop(self) -> None:
        self.scheduler.loop()


class Automower:

    def __init__(self, module: Module) -> None:
        self.mqttClient = module.getMqttClient()
        self.scheduler = module.getScheduler()
        self.module = module

        self.mode = None
        self.charge = None
        self.status = None
        self.lastReceivedMode = None
        self.errorMessage = None
        self.battVoltage = None
        self.commandMode = None
        self.commandStatus = None

    def setup(self) -> None:

        self.scheduler.scheduleEach(self.__keepAlive, 5000)
        self.scheduler.scheduleEach(self.__updateMqtt, 5000)

        self.mqttClient.subscribeIndependentTopic('/house/garden/automower/mower/status/plain', self.__receivedStatus)
        self.mqttClient.subscribeIndependentTopic('/house/garden/automower/mower/mode', self.__receivedMode)
        self.mqttClient.subscribeIndependentTopic('/house/garden/automower/mower/battery/charge', self.__receivedCharge)
        self.mqttClient.subscribeIndependentTopic('/house/garden/automower/mower/battery/charge', self.__receivedCharge)
        self.mqttClient.subscribeIndependentTopic('/house/garden/automower/mower/error/message', self.__receivedErrorMessage)
        self.mqttClient.subscribeIndependentTopic('/house/garden/automower/health/voltage/batt', self.__receivedBattVoltage)

        self.mqttClient.subscribe('control/mode[auto,home,eod,man]', self.__receivedCommandMode)
        self.mqttClient.subscribe('control/status[start,stop]', self.__receivedCommandStatus)

    def __keepAlive(self) -> None:
        self.mqttClient.publishIndependentTopic('/house/agents/Automower/heartbeat', DateTimeUtilities.getCurrentDateString())
        self.mqttClient.publishIndependentTopic('/house/agents/Automower/subscriptions', JsonUtil.obj2Json(self.mqttClient.getSubscriptionCatalog()))

    def __receivedStatus(self, payload: str) -> None:
        self.status = payload
        self.__updateMqtt()

    def __receivedCharge(self, payload: str) -> None:
        self.charge = float(payload) / 100
        self.__updateMqtt()

    def __receivedMode(self, payload: str) -> None:
        self.mode = MowerMode(int(payload))
        self.lastReceivedMode = DateTimeUtilities.getCurrentDateString()
        self.__updateMqtt()

    def __receivedErrorMessage(self, payload: str) -> None:
        self.errorMessage = payload
        self.__updateMqtt()

    def __receivedBattVoltage(self, payload: str) -> None:
        self.battVoltage = payload
        self.__updateMqtt()

    def __receivedCommandMode(self, payload: str) -> None:
        self.commandMode = payload
        self.__updateMqtt()

    def __receivedCommandStatus(self, payload: str) -> None:
        self.commandStatus = payload
        self.__updateMqtt()

    def __updateMqtt(self) -> None:
        self.mqttClient.publish('data/lastReceivedMode', self.lastReceivedMode)
        if self.mode:
            self.mqttClient.publish('data/mode/string', self.mode.name)
            self.mqttClient.publish('data/mode/number', str(self.mode.value))
        self.mqttClient.publish('data/charge', str(self.charge))
        self.mqttClient.publish('data/status', self.status)
        self.mqttClient.publish('data/errorMessage', self.errorMessage)
        self.mqttClient.publish('data/battVoltage', self.battVoltage)

        if self.commandMode:
            self.mqttClient.publishIndependentTopic('/house/garden/automower/control/mode', self.commandMode)

        if self.commandStatus:
            self.mqttClient.publishIndependentTopic('/house/garden/automower/control', self.commandMode)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('Automower').setLevel(logging.DEBUG)

    module = Module()
    module.setup()

    Automower(module).setup()

    print("Automower is running!")

    while (True):
        module.loop()
        time.sleep(0.25)


if __name__ == '__main__':
    main()
