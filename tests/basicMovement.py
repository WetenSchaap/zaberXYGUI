from zaber_motion import Units
from zaber_motion.ascii import Connection
import time


with Connection.open_serial_port("/dev/ttyUSB0") as connection:
    connection.enable_alerts()

    device_list = connection.detect_devices()
    print("Found {} devices".format(len(device_list)))

    devicex = device_list[0]
    axisx = devicex.get_axis(1)
    devicey = device_list[1]
    axisy = devicey.get_axis(1)
    if not axisx.is_homed():
        axisx.home()
    if not axisy.is_homed():
        axisy.home()
    print("start at 0")
    axisx.move_absolute(0, Units.LENGTH_MILLIMETRES)
    axisy.move_absolute(0, Units.LENGTH_MILLIMETRES)
    print("zero-ing complete")
    # Move a small distance, blocking comands
    print ("move xy blocking commands")
    axisx.move_absolute(10, Units.LENGTH_MILLIMETRES)
    axisy.move_absolute(7, Units.LENGTH_MILLIMETRES)
    print ("move complete")

    # sleep for a few sec
    time.sleep(3)
    # Move another small distance, now simultaniously
    print ("move xy non-blocking commands")
    axisx.move_absolute(30, Units.LENGTH_MILLIMETRES, wait_until_idle=False)
    axisy.move_absolute(33, Units.LENGTH_MILLIMETRES, wait_until_idle=False)
    print("I can do stuff while the thing is moving now.")
    # Wait until move complete
    axisx.wait_until_idle()
    axisy.wait_until_idle()
    print ("move complete")
    #%% Now read out positions:
    x = axisx.get_position(Units.LENGTH_MICROMETRES)
    y = axisy.get_position(Units.LENGTH_MICROMETRES)
    print("Axis Positions:")
    print(f"x = {x} µm")
    print(f"y = {y} µm")