<h2>Making of a MQTT interface for a De Dietrich boiler fitted with a Diematic 3 regulator</h2>

The goal is to be able to control boiler's general setting with a smartphone using a MQTT client or through a domotic software.

Reminder : Diematic 3 regulator has a built-in control board like :

![Diematic 3 Regulation Control Panel](ReadMeImages/DiematicRegul.png)

And a remote control board like :

![Diematic 3 Remote Control](ReadMeImages/DiematicCdA.png)

I remind that if you use information and software available in this repository, It's mean that you feel enough qualified to manage what you are doing and its impacts.

<h2>General Design</h2>
<h3>ModBus Interface Description</h3>

Diematic 3 regulator is fitted with a ModBus interface which allows to read and modify measures and parameters.

There's very few doucmentation on the specification of the De Dietrich ModBus implementation. Used documents can be found on the web by using key words "diematic modbus register"

ModBus rely on data exchange on a serial bus. The Diematic 3 implementation is done with following details :

    RTU (binary) mode, on a RS485 bus
    9600 bauds, 8 bits, no parity, 1 stop bit
    boiler address is 0x0A (hexadecimal)

One specifity of the De Dietrich implementation is the dual-master :
    The boiler transmit ModBus command during 5s as a ModBus master and then remain silent during 5 next seconds  waiting for possible ModBus commandas slave (address: 0x0A).

This particularty will have some impact on the behviour of our system : reponse time will be between 5 and 10 s (5s waiting for boiler slave mode followed by the data transmission).

My main requirements to design the solution were:
- to not spend too much time
- to not spend too much money
as at the beginning I was not sure to achieved something usable.

It's why I chose to use following elements :
- an interface card USR-TCP-232-24, replaced later by an USR-TCP-232-306 which is delivered in an enclosure and has bigger range for power supply voltage. USR-TCP-232-306 specifications can be found on USR-IOT website and bought averywhere. The interface RS485 port is connected on the ModBus port of the Boiler on on side and to the LAN on the other side. If you need it, you can use some WIFI version.
- a Raspberry with raspian installed and Python 3.6 or more. Python script have been tested with python 3.8. A diffculty with Raspberry is to no corrupt the SD card on power loss. I've solved this issue using a backup battery. If you've a NAS already robust agains that kind of problem, you also be able to use it.
- a MQTT broker, which can be installed on the same raspberry or elsewhere
- some python scripts to send commands received as MQTT messages to the boiler, and provide boiler status always through MQTT messages.

Internet box settings to allow external access to the NAS while complying with good security practice wont be described here. Several solutions can be used according your paranoid level.

![Web Interface Design](ReadMeImages/DiematicMQTTInterfaceDesign.png)

<h2>Making of</h2>
<h3>Wiring</h3>

You can start with wiring the USR-TCP-232-306 to the boiler using a 2 wire cable and a mini DIN connector with four pins. The cable schematic is below:

![ModBus wiring](ReadMeImages/ModBusMiniDinConnection.png)

<h3>Module settings</h3>
You can now go on with setting the USR-TCP-232-306  module with a standard web brother :

![Module setup](ReadMeImages/USR-TCP232-306-config.png)

Remark : I let you read the doc to configure IP parameters of the USR-TCP-232-306. The TCP server address of the above page is not used

<h3>Python script </h3>
Instructions are available in the 
[Wiki](https://github.com/Benoit3/Diematic_to_MQTT/wiki)

<h3>Home Assistant Integration</h3>

The Home Assistant discovery mode is enable by default. Check parameters in the Diematic32MQTT.conf file.

You will just have to connect your hassio to your MQTT broker and define your cards.

![Hassio_Control](ReadMeImages/HassioControlCard.png) ![Hassio_Control](ReadMeImages/HassioMonitoringCard.png)
![Hassio_Control](ReadMeImages/HassioSettingCard.png)

<h3>To use client Dash MQTT for android</h3>

With this [client](https://play.google.com/store/apps/details?id=net.routix.mqttdash&hl=fr&gl=US) you can get easily custom dashboard like this one:

![Dash MQTT](ReadMeImages/MQTTDash.png)

<h3>Limitations</h3>

With this release 313 (boiler bought end of 2006), some limitations has been solved with sometimes the help of workaround. Temporary anti freezing, is no more available as it was not correctly settable through the Diematic 3 Modbus interface, but permanent antifreezing mode has replaced it. Notice that, in this case the remote control shows below display, which is normal (you can get it with the mode button selecting antifreeze during 5s) :
![AntiFreeze](ReadMeImages/AntiFreeze.png)

Main found limitations of the Diematic 3 interfaces are :
- update of remote display heating mode not updatable without "heavy" workaround
- no possibility to switch between programs (P1..P4)
- Pump ECS (water heater) info not robust
- no possibility to use without issue temporary freezing mode
- pump power stays at 100% when all pumps are off

<h3>Experience return</h3>

[Here](https://community.home-assistant.io/t/de-dietrich-diematic-modbus-to-mqtt-interface/363086/27?u=benoits) is an interesting application to monitor gaz consumption and level inside a gaz tank

For further info you can go to [Fibaro forum](https://www.domotique-fibaro.fr/topic/5677-de-dietrich-diematic-isystem/) or to the [Home Assistant Community](https://community.home-assistant.io/t/de-dietrich-diematic-modbus-to-mqtt-interface/363086)
