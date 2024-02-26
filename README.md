# HiLighting LEDs

It's yet another cheapo LED strip from AliExpress!  Every strip I buy seems to get cheaper and cheaper.  I find it strange that every manufacturer seems to implement their own controller and so each set of lights has a different protocol.  But here we are.
This time I paid £2.52 including tax and delivery for a 5M strip with an IR remote control.  The remote didn't include a battery.  The app is called `HiLighting`.  It forces you to enable precise location on Android before it will even detect your lights and allow you to control them!  There is some interesting looking functionality which allows you to choose your own colour scheme for the effects.  I don't think I will spent too much time with that since it's not supported in Home Assistant, but we'll see.

Something to be aware of is that the picture on the AliExpress page for the product doesn't necessarily represent the app or the controller that the lights will use.

AliExpress link:  https://www.aliexpress.com/item/1005005485885067.html

![image](https://github.com/8none1/hilighting_homeassistant/assets/6552931/317cab8a-c576-4db9-8aa8-8744dd775748)

My lights report their name as: `L7161` and have a MAC address of `23:01:02:aa:10:84`.

As with the (ELK-BLEDOB)[https://github.com/8none1/elk-bledob] project I will be using an nRF52840 BLE Sniffer rather than trying to get snoop logs off Android.
So let's breakout Wireshark and go fishing...

## Sniffing

Tips if you're using Wireshark and a nRF52840 with the Nordic toolkit:

- Filter `btle.length != 0` will hide empty PDU packets
- Filter `btatt.handle == 0x0014` will show writes to the serial port

## What the....

It looks like this set of lights offers a serial port over Bluetooth LE and then you send commands to it that way. 

## Power on & off

If you have a BLE UART connection you just write these bytes to the serial port:

`55 01 02 00` Off
`55 01 02 01` On

## Other projects that might be of interest

- [iDotMatrix](https://github.com/8none1/idotmatrix)
- [Zengge LEDnet WF](https://github.com/8none1/zengge_lednetwf)
- [iDealLED](https://github.com/8none1/idealLED)
- [BJ_LED](https://github.com/8none1/bj_led)
- [ELK BLEDOB](https://github.com/8none1/elk-bledob)
