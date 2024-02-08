import numpy as np
import time
import zaber_motion
import zaber

class Universalstage:
    def __init__(self,type="dummy"):
        self.type = type
        if self.type not in ("dummy","zaber"):
            raise ValueError(f"Unrecognized stage type: {self.type}")
        elif self.type == "dummy":
            self.connection = DummyConnection()
        elif self.type == "zaber":
            zaberPort = zaber.getZaberPort()
            self.connection = zaber_motion.ascii.Connection.open_serial_port(zaberPort)
    def stageInit(self):
        if self.type == "zaber":
            self.axisx,self.axisy = zaber.stageInit(self.connection)
            return self.axisx,self.axisy
        elif self.type == "dummy":
            self.axisx,self.axisy = (DummyAxis(), DummyAxis())
            return self.axisx,self.axisy 
    def close(self):
        self.connection.close()

    def __enter__(self):
        '''for with... constructions'''
        return self
    
    def __exit__(self, exception_type, exception_value, exception_traceback):
        #Exception handling here, if an error occurs in the with block
        self.close()


#####################################
# The stuff that follows below are the minimal classes needed to mimick behaviour of the zaberstage
# for a dummyclass, or to serve as an example to implement a new stage with the same universal API.
# Not complete at all. If you get an error, just add more bits to this to fill up what is missing.
#####################################

class DummyConnection:
    def __init__(self):
        self.connected = True
    def close(self):
        self.connected = False

class DummyAxis:
    def __init__(self):
        self.position = 0
        self.settings = DummyAxisSettings()
        self.homed = "True"
    
    def is_homed(self):
        return self.homed
    
    def home(self):
        time.sleep(1) # sleep to make it convincing
        return True

    def get_position(self,unit):
        # ignore unit. Not interesting
        return self.position
    
    def move_absolute(self, position, unit, wait_until_idle=True):
        self.position = position

    def stop(self):
        pass

    def move_relative(self, move, unit, wait_until_idle=True):
        self.position += move


class DummyAxisSettings:
    def __init__(self):
        self.properties = {
            "limit.max" : 50000,
            "limit.min" : 0,
        }
    def get(self,property,unit):
        """Note that we completely ignore the unit, not interesting for dummy class"""
        return self.properties[property]
