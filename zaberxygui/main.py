import zaber_motion
from zaber_motion import Units
import zaber_motion.ascii


import PySimpleGUI as sg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backend_bases import MouseButton

# import time
# import os
# import sys
import io
import argparse
import numpy as np
import pyperclip

import universalstage

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

def array_to_data(array, resize=False, format="png"):
    """
    Converts raw numpy data outputted by camera to a datastream for displaying. Optionally makes image smaller to get it to fit on the screen. I use a shitty filter for that for max speed, so keep in mind this could be the reason for artefacts! The format determines the size and speed of this, obviously.

    Parameters
    ----------
    array : np.array
        As returned by camera
    resize : int, defaults to False
        Size of the 'y' edge of the image in pixels
    format : str, defaults to png
        Datatype/compression to covert the raw input data to.

    Returns
    -------
    bytes datastream
        Image as streamable data
    """
    im = PIL.Image.fromarray(array)
    if resize:
        xresize = round( (resize / im.size[0]) * im.size[1] )
        im.thumbnail((resize,xresize), PIL.Image.Resampling.NEAREST)
    with io.BytesIO() as output:
        im.save(output, format="PNG")
        data = output.getvalue()
    return data

def get_step(stepsize,xsign,ysign,direction):
    movSign = {
        "-UP-":1 * ysign,
        "-DOWN-":-1 * ysign,
        "-RIGHT-":1 * xsign,
        "-LEFT-":-1 * xsign,
    }
    return stepsize * movSign[direction]


def main(stage="dummy",camtype="dummy"):
    
    def on_click(event):
        """
        Get xydata when we click on matplotlib plot, and move there, if this behaviour is enabled.
        Inside main loop for scope reasons.
        """
        if event.button is MouseButton.LEFT and event.inaxes and values["-AllowMapMove-"]:
            # print(f'data coords {event.xdata} {event.ydata},')
            axis['x'].move_absolute(event.xdata,Units.LENGTH_MICROMETRES,wait_until_idle = False)
            axis['y'].move_absolute(event.ydata,Units.LENGTH_MICROMETRES,wait_until_idle = False)
            window["-STATUS-"].update("All good")
    
    savedLocations = []
    with universalstage.Universalstage(type=stage) as stageConnection:
        # First initialize the GUI
        sg.theme('DarkBrown4')  # Set your favourite theme
        x,y = 0,0 # dummy values
        layoutStatus = [[sg.Text("Status:"), sg.Text("All good", key ="-STATUS-",size=40)]],
        layoutTopMiddle = [ # Map of all locations
            [sg.Text(f'X = {x:06.1f} µm',key="-X-"), sg.Text(f"Y = {y:06.1f} µm",key="-Y-"),sg.Push(),sg.Button("Update",key="-UPDATE-")],
            [sg.Text("Allow navigation by clicking on plot below"), sg.Checkbox("",default=False, key="-AllowMapMove-")],
            [sg.Canvas(key="-CANVAS-")],
        ]
        layoutMidLeft = [ # Movement control
            [sg.Push(),sg.Button("STOP", key='-STOP-'),sg.Push()],
            [sg.Push(),sg.Text("Move stage using arrow keys or buttons below"),sg.Push()],
            [sg.Push(),sg.Button("⬆️",key='-UP-'),sg.Push()],
            [sg.Push(),sg.Button("⬅️",key='-LEFT-'),sg.Button("➡️",key='-RIGHT-'),sg.Push()],
            [sg.Push(),sg.Button("⬇️",key='-DOWN-'),sg.Push()],
            [sg.Text("Stepsize (mm):"), sg.InputText(default_text=1,key="-STEP-")],
            [sg.VPush()],
            [sg.Text("Set absolute location:")],
            [sg.Text("X (µm) ="), sg.InputText(default_text=0,key="-XMOVE-")],
            [sg.Text("Y (µm) ="), sg.InputText(default_text=0,key="-YMOVE-")],
            [sg.Push(), sg.Button("Move to location",key="-MOVE-"), sg.Push()],
            [sg.Text("Mirror X-axis"), sg.Checkbox("",default=False, enable_events=True, key="-MirrorX-")],
            [sg.Text("Mirror Y-axis"), sg.Checkbox("",default=False, enable_events=True, key="-MirrorY-")],
            [sg.Text("Switch X & Y axis"), sg.Checkbox("",default=False,  enable_events=True, key="-SwitchXY-")],
            [sg.VPush()],
        ]
        layoutTopRight = [
            [sg.Text("Saved locations:")],
            [sg.Multiline(size=(50,30),  disabled=True, write_only=True, key='-SVLOC-', autoscroll=True)],
            [sg.Button("Log location", key='-LOCLOG-'),sg.Button("Copy locations", key='-COPLOC-')],
        ]


        layout = [
            [ # Position stuff
                sg.Column(layoutTopMiddle),
                sg.VSeperator(pad=(0,0)),
                sg.Column(layoutTopRight),
            ],
            [
                sg.HorizontalSeparator()
            ],
            [ # Imaging stuff
                sg.Column(layoutMidLeft),
            ],
            [
                sg.HorizontalSeparator()
            ],
            [ # statusbar with errors and stuff
                layoutStatus
            ]
        ]

        window = sg.Window(
            'XY-stage-controller', 
            layout, 
            return_keyboard_events=False, # dangerous, was true in previous versions
            resizable=True,
            finalize=True
        )
        window["-STATUS-"].update("Connecting to Zaber stage")
        axisx,axisy = stageConnection.stageInit()
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
        # init moves
        movDirection = {
            "-UP-":axis['y'].move_relative,
            "-DOWN-":axis['y'].move_relative,
            "-LEFT-":axis['x'].move_relative,
            "-RIGHT-":axis['x'].move_relative,
        }
        # Initialize location plot
        canvas_elem = window['-CANVAS-']
        canvas = canvas_elem.TKCanvas
        # draw the intitial scatter plot
        fig, ax = plt.subplots(1,1,figsize=(4.5,4))
        formatplot(ax,xmax,ymax)
        ax.scatter(0,0,s=100)
        plt.connect('button_press_event', on_click) # This makes clicking somewhere on the plot do something
        fig_agg = draw_figure(canvas, fig)


        # Now check if zaber is ready to go or homing needs to happen.
        if not axisx.is_homed():
            window["-STATUS-"].update("Stage is homing",text_color='red')
            axisx.home()
        if not axisy.is_homed():
            window["-STATUS-"].update("Stage is homing",text_color='red')
            axisy.home()
        window["-STATUS-"].update("Zaber ready to start")
        x = axisx.get_position(Units.LENGTH_MICROMETRES)
        y = axisy.get_position(Units.LENGTH_MICROMETRES)

        window["-X-"].update(f"X = {x:06.1f} µm")
        window["-Y-"].update(f"Y = {y:06.1f} µm")
        ax.cla()
        ax.scatter(x,y,s=100)
        fig_agg.draw()
        while True:  # Event Loop
            event, values = window.read(timeout=20) # the timeout (in ms) determines max framerate from te feed. Setting to 0 will saturate one core of the CPU so may not be a great idea for testing, but if all works, probably best to set to remove
            if event == sg.WIN_CLOSED:
                break
            elif event in ("-STOP-"):
                axis['x'].stop(wait_until_idle = False)
                axis['y'].stop(wait_until_idle = False)
                window["-STATUS-"].update("EMERGENCY STOP",text_color='red')
            elif event in ("-UP-","-DOWN-","-LEFT-","-RIGHT-"):
                try:
                    stepsize = float( values["-STEP-"] )
                except ValueError:
                    window["-STATUS-"].update("Stepsize not a number!",text_color='red')
                    continue
                try:
                    movDirection[event]( get_step(stepsize,xSign,ySign,event), Units.LENGTH_MILLIMETRES, wait_until_idle = False )
                    window["-STATUS-"].update("All good")
                except zaber_motion.CommandFailedException:
                    window["-STATUS-"].update("Command rejected, possibly out of range?",text_color='red')
                    continue
            elif event == "-MOVE-":
                try:
                    Xloc = float( values["-XMOVE-"] )
                    Yloc = float( values["-YMOVE-"] )
                except ValueError:
                    window["-STATUS-"].update("Set x or y to not a number!",text_color='red')
                    continue
                try:
                    # You are putting numbers here so do not use the sign flag like with relative movement
                    axis['x'].move_absolute( Xloc,Units.LENGTH_MICROMETRES,wait_until_idle = False) 
                    axis['y'].move_absolute( Yloc,Units.LENGTH_MICROMETRES,wait_until_idle = False)
                except zaber_motion.CommandFailedException:
                    window["-STATUS-"].update("Command rejected, possibly out of range?",text_color='red')
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
            #### Saving image locations:
            elif event in ("-LOCLOG-"):
                realx = axisx.get_position(Units.LENGTH_MICROMETRES) # real as opposed to the "fake" one I show with mirrored axis and stuff
                realy = axisy.get_position(Units.LENGTH_MICROMETRES)
                name = f"location{len(savedLocations):03d}" 
                savedLocations.append((name,realx,realy))
                window["-SVLOC-"].update(
                    f"{name}:\n" + f"  x: {realx}\n" + f"  y: {realy}\n", 
                    append=True
                )
                window["-STATUS-"].update("Logged current location")
            elif event in ("-COPLOC-"):
                print(window["-SVLOC-"].get())
                pyperclip.copy(window["-SVLOC-"].get())
                window["-STATUS-"].update("Copied logged locations to clipboard")
            ### General stuff
            elif event in ('-UPDATE-'): # Usefull for printing debug
                pass
            elif event in ("__TIMEOUT__"):
                pass # do nothing for now, just update x/y
            else:
                # Can be useful to see what new keypresses etc are coming in
                pass
                # print(event, values)
            ##### Finally:
            ## update x,y values with reported.
            x = axis['x'].get_position(Units.LENGTH_MICROMETRES)
            y = axis['y'].get_position(Units.LENGTH_MICROMETRES)
            window["-X-"].update(f"X = {x:06.1f} µm")
            window["-Y-"].update(f"Y = {y:06.1f} µm")
            ax.cla()
            formatplot(ax,xmax,ymax,xSign,ySign)
            ax.scatter(x,y,s=100)
            # write saved locations in plot
            for l in savedLocations:
                ax.scatter(l[1], l[2])
                ax.annotate(l[0], (l[1], l[2]))
            fig_agg.draw()


def parse_arguments():
    parser = argparse.ArgumentParser(
        prog='zaberxygui',
        description="shows the xy stage as well as the camera in one simple GUI."
    )
    parser.add_argument('-s','--stage', default="zaber", help="The type of xy stage you are using. Will of course only work with implemented stages")
    return parser.parse_args()

if __name__ ==  "__main__":
    args = parse_arguments()
    main(stage = args.stage)