# HiLighting LEDs

It's yet another cheapo LED strip from AliExpress!  Every strip I buy seems to get cheaper and cheaper.  I find it strange that every manufacturer seems to implement their own controller and so each set of lights has a different protocol.  But here we are.
This time I paid £2.52 including tax and delivery for a 5M strip with an IR remote control.  The remote didn't include a battery.  The app is called `HiLighting`.  It forces you to enable precise location on Android before it will even detect your lights and allow you to control them!  There is some interesting looking functionality which allows you to choose your own colour scheme for the effects.  I don't think I will spent too much time with that since it's not supported in Home Assistant, but we'll see.

Something to be aware of is that the picture on the AliExpress page for the product doesn't necessarily represent the app or the controller that the lights will use.

AliExpress link:  https://www.aliexpress.com/item/1005005485885067.html

![image](https://github.com/8none1/hilighting_homeassistant/assets/6552931/317cab8a-c576-4db9-8aa8-8744dd775748)

![image](https://github.com/8none1/hilighting_homeassistant/assets/6552931/5bb03ae0-b6ba-47ea-b27e-1a9519bb7eb1)

My lights report their name as: `L7161` and have a MAC address of `23:01:02:aa:10:84`.


## Current State

Planned implementation complete.

Working:

- On / Off
- Set RGB colour
- Brightness
- Limited effects with a fixed speed

## Installation in Home Assistant

## Installation

### Requirements

You need to have the bluetooth component configured and working in Home Assistant in order to use this integration.

### HACS

Add this repo to HACS as a custom repo.  Click through:

- HACS -> Integrations -> Top right menu -> Custom Repositories
- Paste the Github URL to this repo in to the Repository box
- Choose category `Integration`
- Click Add
- Restart Home Assistant
- HiLighting LED devices should start to appear in your Integrations page

## Sniffing

As with the [ELK-BLEDOB](https://github.com/8none1/elk-bledob) project I will be using an nRF52840 BLE Sniffer rather than trying to get snoop logs off Android.
So let's breakout Wireshark and go fishing...

Tips if you're using Wireshark and a nRF52840 with the Nordic toolkit:

- Filter `btle.length != 0` will hide empty PDU packets
- Filter `btatt.handle == 0x0014` will show writes to the serial port

## What the....

It looks like this set of lights offers a serial port over Bluetooth LE and then you send commands to it that way.
Had a chat on the Home Assistant Discord and the feeling is that if it's GATT then it should just work, so I'm going to try and implement a simple on/off integration before digging in to all the complex stuff.
... and ...  it does indeed just work.

## Power on & off

If you have a BLE UART connection you just write these bytes to the serial port.  Using an app like [LightBlue](https://punchthrough.com/lightblue/) you can connect to the controller, connect to `6e400002-b5a3-f393-e0a9-e50e24dcca9e` and write these hex bytes.

- `55 01 02 00` Off
- `55 01 02 01` On

## RGB

```
|------|------------------------ header
|      | ||--------------------- red
|      | || ||------------------ green
|      | || || ||--------------- blue
55 07 01 ff 00 00
55 07 01 00 ff 00
55 07 01 00 00 ff
```
## Brightness

Brightness is odd.

```
|------|------------------------ header
|      | |---|------------------ brightness
55 03 01 09 03
55 03 01 6c 02
55 03 01 6f 05
```

Minimum brightness is 0x6c 0x02 (27650)
Maximum brightness is 0xff 0x0f (65295)

It seems that the two brightness bytes do not represent a single value.  Byte 4, the last byte, is a scale which stops at 0x0F.  Byte 3 is the smaller increments which seems to be an 8 bit number.  I don't think it's really necessary to have that level of granularity on these type of LEDs, so I've only implemented the 15 levels of brightness from byte 4.  This seems fine.

## Effects

The standard effects numbered from 0 to 9.  You don't seem to be able to specify a brightness for them.

```
|---|--------------------------- header
|   | ||------------------------ select effect
|   | || ||--------------------- effect number
55 04 01 00
55 04 01 01
55 04 01 06
55 04 01 07
```

### Effect Speed

```
|---|--------------------------- header
|   | ||------------------------ select effect speed (0-255)
|   | || ||--------------------- speed
55 04 04 31
55 04 04 59
55 04 04 96
55 04 04 bf
55 04 04 ff
```

#### Custom Effects

We could build a set of custom effects and hard code them as part of the integration.  But I'm not planning on doing that any time soon.  The format seems easy enough to understand.


```

|------| --------------------------------------------------------------------- custom effects header
|      | ||------------------------------------------------------------------- speed probably 0-255
|      | || ||---------------------------------------------------------------- effect type (merge, flash etc) probably 1 -> 5
|      | || || ||------------------------------------------------------------- brightness probably 0-255
|      | || || || |---------------| ------------------------------------------ likely all colour data. 2 bytes per colour? 565?
55 05 01 00 03 00 fa f8 55 f9 b1 ff       -  RGB   merge,  slow,   dim
55 05 01 00 03 ff fa f8 55 f9 b1 ff       -  RGB   merge,  slow,   bright
55 05 01 7f 03 00 fa f8 55 f9 b1 ff       -  rgb   merge,  fast,   dim
55 05 01 7f 03 ff fa f8 55 f9 b1 ff       -  rgb   merge,  fast,   bright
55 05 01 7f 04 ff fa f8 55 f9 b1 ff       -  rgb   flash,  fast,   bright
55 05 01 7f 05 ff fa f8 55 f9 b1 ff       -  rgb,  jump,   fast,   bright
55 05 01 7f 05 ff fa f8 41 f9 fc fd 4d e4 -  rgrg, jump,   fast,   bright

```

## Other projects that might be of interest

- [iDotMatrix](https://github.com/8none1/idotmatrix)
- [Zengge LEDnet WF](https://github.com/8none1/zengge_lednetwf)
- [iDealLED](https://github.com/8none1/idealLED)
- [BJ_LED](https://github.com/8none1/bj_led)
- [ELK BLEDOB](https://github.com/8none1/elk-bledob)
- [HiLighting LED](https://github.com/8none1/hilighting_homeassistant)
- [BLELED LED Lamp](https://github.com/8none1/ledble-ledlamp)
