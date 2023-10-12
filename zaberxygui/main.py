import zaber_motion
from zaber_motion import Units
from zaber_motion.ascii import Connection
import PySimpleGUI as sg
import time
import serial.tools.list_ports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backend_bases import MouseButton

def draw_figure(canvas, figure):
    '''Helper function for plotting current location'''
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg

def formatplot(ax,xmax,ymax,xSign=1,ySign=1):
    """Correctly format plot"""
    ax.grid(True)
    ax.set_aspect('equal', adjustable='box')
    if xSign == 1:
        ax.set_xlim([0,xmax])
    elif xSign == -1:
        ax.set_xlim(xmax,0)
    if ySign == 1:
        ax.set_ylim([0,ymax])
    elif ySign == -1:
        ax.set_ylim(ymax,0)

def on_click(event):
    """
    Get xydata when we click on matplotlib plot, and move there, if this behaviour is enabled.
    """
    if event.button is MouseButton.LEFT and event.inaxes and values["-AllowMapMove-"]:
        print(f'data coords {event.xdata} {event.ydata},')
        axis['x'].move_absolute(event.xdata,Units.LENGTH_MICROMETRES,wait_until_idle = False)
        axis['y'].move_absolute(event.ydata,Units.LENGTH_MICROMETRES,wait_until_idle = False)

zaberSerialPort = ""
allPorts = serial.tools.list_ports.comports()
for device in allPorts:
    if device.vid == 1027 and device.pid == 24577: # Change this to the actual device you have to get autoconnect to work. The vid & pid can be found using the pyserial module.
        zaberSerialPort = device.device
if zaberSerialPort == "":
    zaberSerialPort = input("Zaber XY stage not autodetected. Input serial port manually to continue, or press enter to quit.")
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
    xmax = axisx.settings.get("limit.max",unit = Units.LENGTH_MICROMETRES)
    ymax = axisy.settings.get("limit.max",unit = Units.LENGTH_MICROMETRES)
    xSign = 1
    ySign = 1
    xySwitch = False

    boolToSign = {
        True : -1,
        False : 1,
    }
    axis = { # This seems superfluous, but makes switching definition of what is x and what is y a whole lot easier
        'x' : axisx,
        'y' : axisy,
    }

    # Initialize GUI
    sg.theme('DarkBrown4')  # Set your favourite theme

    layoutLeft = [
        [sg.Text(f'X = {x:06.1f} µm',key="-X-"), sg.Text(f"Y = {y:06.1f} µm",key="-Y-"),sg.Push(),sg.Button("Update",key="-UPDATE-")],
        [sg.Text("Allow navigation by clicking on plot below"), sg.Checkbox("",default=True, key="-AllowMapMove-")],
        [sg.Canvas(key="-CANVAS-")],
        [sg.Text("Set absolute location:")],
        [sg.Text("X (µm) ="), sg.InputText(default_text=0,key="-XMOVE-")],
        [sg.Text("Y (µm) ="), sg.InputText(default_text=0,key="-YMOVE-")],
        [sg.Push(), sg.Button("Move to location",key="-MOVE-"), sg.Push()],
    ]

    layoutRighy = [
        [sg.Push(),sg.Button("STOP", key='-STOP-'),sg.Push()],
        [sg.Push(),sg.Text("Move stage using arrow keys or buttons below"),sg.Push()],
        [sg.Push(),sg.Button("⬆️",key='-UP-'),sg.Push()],
        [sg.Push(),sg.Button("⬅️",key='-LEFT-'),sg.Button("➡️",key='-RIGHT-'),sg.Push()],
        [sg.Push(),sg.Button("⬇️",key='-DOWN-'),sg.Push()],
        [sg.Text("Stepsize (mm):"), sg.InputText(default_text=1,key="-STEP-")],
        [sg.VPush()],
        [sg.Text("Mirror X-axis"), sg.Checkbox("",default=False, enable_events=True, key="-MirrorX-")],
        [sg.Text("Mirror Y-axis"), sg.Checkbox("",default=False, enable_events=True, key="-MirrorY-")],
        [sg.Text("Switch X & Y axis"), sg.Checkbox("",default=False,  enable_events=True, key="-SwitchXY-")],
        [sg.VPush()],
        [sg.Text("Status:"), sg.Text("All good", key ="-STATUS-",size=40)],

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
        finalize=True
    )

    # Initialize location plot
    canvas_elem = window['-CANVAS-']
    canvas = canvas_elem.TKCanvas
    # draw the intitial scatter plot
    fig, ax = plt.subplots(1,1)
    formatplot(ax,xmax,ymax)
    ax.scatter(x,y,s=100)
    plt.connect('button_press_event', on_click) # This makes clicking somewhere on the plot do something
    fig_agg = draw_figure(canvas, fig)

    while True:  # Event Loop
        event, values = window.read(timeout=50)
        if event == sg.WIN_CLOSED:
            break
        elif event in ("-STOP-","Escape:9"):
            axis['x'].stop(wait_until_idle = False)
            axis['y'].stop(wait_until_idle = False)
            window["-STATUS-"].update("EMERGENCY STOP")
        elif event in ("-UP-","Up:111"):
            try:
                stepsize = float( values["-STEP-"] )
            except ValueError:
                window["-STATUS-"].update("Stepsize not a number!")
                continue
            try:
                axis['y'].move_relative( ySign * stepsize,Units.LENGTH_MILLIMETRES,wait_until_idle = False)
            except zaber_motion.CommandFailedException:
                window["-STATUS-"].update("Command rejected, possibly out of range?")
                continue
            window["-STATUS-"].update("All good")
        elif event in ("-DOWN-","Down:116"):
            try:
                stepsize = float( values["-STEP-"] )
            except ValueError:
                window["-STATUS-"].update("Stepsize not a number!")
                continue
            try:
                axis['y'].move_relative(-1 * ySign * stepsize,Units.LENGTH_MILLIMETRES,wait_until_idle = False)
            except zaber_motion.CommandFailedException:
                window["-STATUS-"].update("Command rejected, possibly out of range?")
                continue
            window["-STATUS-"].update("All good")
        elif event in ("-RIGHT-","Right:114"):
            try:
                stepsize = float( values["-STEP-"] )
            except ValueError:
                window["-STATUS-"].update("Stepsize not a number!")
                continue
            try:
                axis['x'].move_relative(xSign * stepsize,Units.LENGTH_MILLIMETRES,wait_until_idle = False)
            except zaber_motion.CommandFailedException:
                window["-STATUS-"].update("Command rejected, possibly out of range?")
                continue
            window["-STATUS-"].update("All good")
        elif event in ("-LEFT-","Left:113"):
            try:
                stepsize = float( values["-STEP-"] )
            except ValueError:
                window["-STATUS-"].update("Stepsize not a number!")
                continue
            try:
                axis['x'].move_relative(-1 * xSign * stepsize,Units.LENGTH_MILLIMETRES,wait_until_idle = False)
            except zaber_motion.CommandFailedException:
                window["-STATUS-"].update("Command rejected, possibly out of range?")
                continue
            window["-STATUS-"].update("All good")
        elif event == "-MOVE-":
            try:
                Xloc = float( values["-XMOVE-"] )
                Yloc = float( values["-YMOVE-"] )
            except ValueError:
                window["-STATUS-"].update("Set x or y to not a number!")
                continue
            try:
                # You are putting numbers here so do not use the sign flag like with relative movement
                axis['x'].move_absolute( Xloc,Units.LENGTH_MICROMETRES,wait_until_idle = False) 
                axis['y'].move_absolute( Yloc,Units.LENGTH_MICROMETRES,wait_until_idle = False)
            except zaber_motion.CommandFailedException:
                window["-STATUS-"].update("Command rejected, possibly out of range?")
            window["-STATUS-"].update("All good")
        elif event in ('-MirrorX-'):
            xSign = boolToSign[values['-MirrorX-']]
        elif event in ('-MirrorY-'):
            ySign = boolToSign[values['-MirrorY-']]
        elif event in ('-SwitchXY-'):
            xySwitch = values['-SwitchXY-']
            if xySwitch:
                axis = {
                    'x' : axisy,
                    'y' : axisx,
                }
            else:
                axis = {
                    'x' : axisx,
                    'y' : axisy,
                }
        elif event in ('-UPDATE-'): # Usefull for printing debug
            pass
        elif event in ("__TIMEOUT__"):
            pass # do nothing for now, just update x/y
        else:
            # Can be useful to see what new keypresses etc are coming in
            pass
            # print(event, values)
        # Finally, update x,y values with reported.
        x = axis['x'].get_position(Units.LENGTH_MICROMETRES)
        y = axis['y'].get_position(Units.LENGTH_MICROMETRES)
        window["-X-"].update(f"X = {x:06.1f} µm")
        window["-Y-"].update(f"Y = {y:06.1f} µm")
        ax.cla()
        formatplot(ax,xmax,ymax,xSign,ySign)
        ax.scatter(x,y,s=100)
        fig_agg.draw()
    window.close()
