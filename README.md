# HiLighting LEDs

It's yet another cheapo LED strip from AliExpress!  Every strip I buy seems to get cheaper and cheaper.  I find it strange that every manufacturer seems to implement their own controller and so each set of lights has a different protocol.  But here we are.
This time I paid £2.52 including tax and delivery for a 5M strip with an IR remote control.  The remote didn't include a battery.  The app is called `HiLighting`.  It forces you to enable precise location on Android before it will even detect your lights and allow you to control them!  There is some interesting looking functionality which allows you to choose your own colour scheme for the effects.  I don't think I will spent too much time with that since it's not supported in Home Assistant, but we'll see.

Something to be aware of is that the picture on the AliExpress page for the product doesn't necessarily represent the app or the controller that the lights will use.

AliExpress link:  https://www.aliexpress.com/item/1005005485885067.html

![image](https://github.com/8none1/hilighting_homeassistant/assets/6552931/317cab8a-c576-4db9-8aa8-8744dd775748)

My lights report their name as: `L7161` and have a MAC address of `23:01:02:aa:10:84`.

As with the [ELK-BLEDOB](https://github.com/8none1/elk-bledob) project I will be using an nRF52840 BLE Sniffer rather than trying to get snoop logs off Android.
So let's breakout Wireshark and go fishing...

## Current State

Working:

- On / Off
- Set RGB colour

Next:

- Brightness
- Effects
- Status updates?

## Sniffing

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

If we scale this to 8 bits as used in Home Assistant, then one interval is about 0x96 (150).  Soooo if we take the brightness as passed to us by HA and multiply it by 150 and add 27650 then we should get the correct brightness.  I mean, what?

Best guess here is that the second byte is a actually a word between 0x0 and 0xf which gives us 15 increments. Why on earth do we need 16bit brightness?

## Other projects that might be of interest

- [iDotMatrix](https://github.com/8none1/idotmatrix)
- [Zengge LEDnet WF](https://github.com/8none1/zengge_lednetwf)
- [iDealLED](https://github.com/8none1/idealLED)
- [BJ_LED](https://github.com/8none1/bj_led)
- [ELK BLEDOB](https://github.com/8none1/elk-bledob)
