# HiLighting LEDs

It's yet another cheapo LED strip from AliExpress!  Every strip I buy seems to get cheaper and cheaper.  I find it strange that every manufacturer seems to implement their own controller and so each set of lights has a different protocol.  But here we are.
This time I paid £2.52 including tax and delivery for a 5M strip with an IR remote control.  The remote didn't include a battery.  The app is called `HiLighting`.  It forces you to enable precise location on Android before it will even detect your lights and allow you to control them!  There is some interesting looking functionality which allows you to choose your own colour scheme for the effects.  I don't think I will spent too much time with that since it's not supported in Home Assistant, but we'll see.

Something to be aware of is that the picture on the AliExpress page for the product doesn't necessisarily represent the app or the controller that the lights will use.

AliExpress link:  https://www.aliexpress.com/item/1005005485885067.html

![image](https://github.com/8none1/hilighting_homeassistant/assets/6552931/317cab8a-c576-4db9-8aa8-8744dd775748)

As with the (ELK-BLEDOB)[https://github.com/8none1/elk-bledob] project I will be using an nRF52840 BLE Sniffer rather than trying to get snoop logs off Android.

So let's breakout Wireshark and go fishing...

