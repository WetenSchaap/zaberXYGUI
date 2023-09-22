import zaber_motion
from zaber_motion import Units
from zaber_motion.ascii import Connection
import PySimpleGUI as sg
import time
import serial.tools.list_ports

zaberSerialPort = ""
allPorts = serial.tools.list_ports.comports()
for device in allPorts:
    if device.vid == 1027 and device.pid == 24577:
        zaberSerialPort = device.device
if zaberSerialPort == "":
    zaberSerialPort = input("Zaber ZY stage not autodetected. Input serial port manually to continue, or press enter to quit.")
    if zaberSerialPort == "":
        import sys
        sys.exit()

# Initalize ZABER

with Connection.open_serial_port(zaberSerialPort) as connection:
    connection.enable_alerts()

    device_list = connection.detect_devices()

    devicex = device_list[0]
    axisx = devicex.get_axis(1)
    devicey = device_list[1]
    axisy = devicey.get_axis(1)
    if not axisx.is_homed():
        axisx.home()
    if not axisy.is_homed():
        axisy.home()

    x = axisx.get_position(Units.LENGTH_MICROMETRES)
    y = axisy.get_position(Units.LENGTH_MICROMETRES)

    # Initialize GUI
    sg.theme('DarkBrown4')  # Set your favourite theme

    layoutLeft = [
        [sg.Text(f'X = {x:06.1f} µm',key="-X-"), sg.Text(f"Y = {y:06.1f} µm",key="-Y-"),sg.Push(),sg.Button("Update",key="-UPDATE-")],
        [sg.Canvas(key="-CANVAS-")],
        [sg.Text("Set absolute location:")],
        [sg.Text("X (µm) ="), sg.InputText(default_text=0,key="-XMOVE-")],
        [sg.Text("Y (µm) ="), sg.InputText(default_text=0,key="-YMOVE-")],
        [sg.Push(), sg.Button("Move to location",key="-MOVE-"), sg.Push()],
    ]

    layoutRighy = [
        [sg.Button("STOP", key='-STOP-')],
        [sg.Push(),sg.Button("⬆️",key='-UP-'),sg.Push()],
        [sg.Push(),sg.Button("⬅️",key='-LEFT-'),sg.Button("➡️",key='-RIGHT-'),sg.Push()],
        [sg.Push(),sg.Button("⬇️",key='-DOWN-'),sg.Push()],
        [sg.Text("Stepsize (mm):"), sg.InputText(default_text=1,key="-STEP-")],
        [sg.Text("Status:"), sg.Text("All good", key ="-STATUS-")],
    ]

    layout = [
        [
            sg.Column(layoutLeft),
            sg.VSeperator(pad=(0,0)),
            sg.Column(layoutRighy),
        ]
    ]

    window = sg.Window(
        'ZABER XY-stage controller', 
        layout, 
        return_keyboard_events=True,
        )

    while True:  # Event Loop
        event, values = window.read(timeout=50)
        if event == sg.WIN_CLOSED:
            break
        elif event in ("STOP","Escape:9"):
            axisx.stop(wait_until_idle = False)
            axisy.stop(wait_until_idle = False)
            window["-STATUS-"].update("EMERGENCY STOP")
        elif event in ("-UP-","Up:111"):
            try:
                stepsize = float( values["-STEP-"] )
            except ValueError:
                window["-STATUS-"].update("Stepsize not a number!")
                continue
            try:
                axisy.move_relative(stepsize,Units.LENGTH_MILLIMETRES,wait_until_idle = False)
            except zaber_motion.CommandFailedException:
                window["-STATUS-"].update("Command rejected, possibly out of range?")
                continue
            print("moving!")
            window["-STATUS-"].update("All good")
        elif event in ("-DOWN-","Down:116"):
            try:
                stepsize = float( values["-STEP-"] )
            except ValueError:
                window["-STATUS-"].update("Stepsize not a number!")
                continue
            try:
                axisy.move_relative(-stepsize,Units.LENGTH_MILLIMETRES,wait_until_idle = False)
            except zaber_motion.CommandFailedException:
                window["-STATUS-"].update("Command rejected, possibly out of range?")
                continue
            print("moving!")
            window["-STATUS-"].update("All good")
        elif event in ("-RIGHT-","Right:114"):
            try:
                stepsize = float( values["-STEP-"] )
            except ValueError:
                window["-STATUS-"].update("Stepsize not a number!")
                continue
            try:
                axisx.move_relative(stepsize,Units.LENGTH_MILLIMETRES,wait_until_idle = False)
            except zaber_motion.CommandFailedException:
                window["-STATUS-"].update("Command rejected, possibly out of range?")
                continue
            print("moving!")
            window["-STATUS-"].update("All good")
        elif event in ("-LEFT-","Left:113"):
            try:
                stepsize = float( values["-STEP-"] )
            except ValueError:
                window["-STATUS-"].update("Stepsize not a number!")
                continue
            try:
                axisx.move_relative(-stepsize,Units.LENGTH_MILLIMETRES,wait_until_idle = False)
            except zaber_motion.CommandFailedException:
                window["-STATUS-"].update("Command rejected, possibly out of range?")
                continue
            print("moving!")
            window["-STATUS-"].update("All good")
        elif event == "-MOVE-":
            try:
                Xloc = float( values["-XMOVE-"] )
                Yloc = float( values["-YMOVE-"] )
            except ValueError:
                window["-STATUS-"].update("Set x or y not a number!")
                continue
            try:
                axisx.move_absolute(Xloc,Units.LENGTH_MICROMETRES,wait_until_idle = False)
                axisy.move_absolute(Yloc,Units.LENGTH_MICROMETRES,wait_until_idle = False)
            except zaber_motion.CommandFailedException:
                window["-STATUS-"].update("Command rejected, possibly out of range?")
            print("moving!")
            window["-STATUS-"].update("All good")
        elif event in ("__TIMEOUT__", "-UPDATE-"):
            pass # do nothing, just update x/y
        else:
            # unknown command?
            print(event, values)
        # Finally, update x,y values with reported.
        x = axisx.get_position(Units.LENGTH_MICROMETRES)
        y = axisy.get_position(Units.LENGTH_MICROMETRES)
        window["-X-"].update(f"X = {x:06.1f} µm")
        window["-Y-"].update(f"Y = {y:06.1f} µm")
    window.close()
