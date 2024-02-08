'''
Module for convenience functions controlling a ZABER stage 
'''
import serial.tools.list_ports
import zaber_motion

def stageInit(zaberStage):
    """
    Initialize zaber stage - makes connection, homes if required, checks if I can finx x and y position.

    Parameters
    ----------
    zaberStage : zaber_motion.ascii.Connection
        Opened connection to the Zaber stage.

    Returns
    -------
    axisx
        Object controlling x-axis
    axisy
        Object controlling y-axis
    """
    zaberStage.enable_alerts()
    device_list = zaberStage.detect_devices()
    devicex = device_list[0]
    axisx = devicex.get_axis(1)
    devicey = device_list[1]
    axisy = devicey.get_axis(1)
    # just test whether the connection is working properly. Homing is the resposibility of other programms.
    _ =  axisx.is_homed()
    _ = axisy.is_homed()
    return axisx,axisy

def moveXY(xy, axisx, axisy, wait_until_idle=True):
    """
    Move stage to [x,y] location.

    Parameters
    ----------
    xy : list-like
        zy-coordinates, xy[0] = x, xy[1] = y. Coordinates in µm
    axisx :
        Object controlling x-axis
    axisy :
        Object controlling y-axis
    wait_until_idle : bool, optional
        If True will block until both axis are in position, by default True
    """
    axisx.move_absolute( xy[0],zaber_motion.Units.LENGTH_MICROMETRES,wait_until_idle = False) 
    axisy.move_absolute( xy[1],zaber_motion.Units.LENGTH_MICROMETRES,wait_until_idle = False)
    if wait_until_idle:
        axisx.wait_until_idle()
        axisy.wait_until_idle()

def getZaberPort():
    """
    Automatically detect zaber stage USB-connection port.
    """
    zaberSerialPort = ""
    allPorts = serial.tools.list_ports.comports()
    for device in allPorts:
        if device.vid == 1027 and device.pid == 24577: # Change this to the actual device you have to get autoconnect to work. The vid & pid can be found using the pyserial module.
            zaberSerialPort = device.device
            return zaberSerialPort
    if zaberSerialPort == "":
        raise ValueError("Zaber XY stage not autodetected. Is it connected? If yes, check vid and pid set in zaber module")