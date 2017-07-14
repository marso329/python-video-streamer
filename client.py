import socket,select,logging,time
import numpy as np
import time
from PIL import Image
from PIL import ImageTk
import sys
global cv2
if sys.version_info[0]>2:
    import tkinter as Tkinter
else:
    import Tkinter 

class Ev3Exception(Exception):
    pass
class Receiver():
    def __init__(self,ip_adress,mode,size):
        if mode not in ["pygame","cv"]:
            raise Ev3Exception("mode not available")
        if type(size)!=tuple or len(size)!=2 or size[0]<0 or size[1]<1:
            raise Ev3Exception("frame size is invalid")
        
        #everything for the camera
        self.__mode=mode
        self.__size=size
        self.__convert={"pygame":self.convert_pygame,"cv":self.convert_cv}
        
        #everything for the interal logger
        self._logger = logging.getLogger('Brick_logger')
        self._logger.setLevel(logging.WARNING)
        self._console_handler = logging.StreamHandler()
        self._console_handler.setLevel(logging.NOTSET)
        self._formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self._console_handler.setFormatter(self._formatter)
        self._logger.addHandler(self._console_handler)
        
        #everything for the ev3 connection
        self._logger.info("starting setup")
        self._s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._port=5000
        socket.inet_aton(ip_adress)
        self._ip_adress=ip_adress
        self._timeout=30
        self._s.settimeout(1)
        self._s.connect((self._ip_adress , self._port))
        self._s.setblocking(0)
        
        self.set_mode(self.__mode)
        self.set_size(self.__size)
        self._timeout=5
        self._logger.info("setup complete")
    
    #converts the string received from the host to a usable list of lists
    def convert_sensorlist(self,data):
        self._logger.info("entered convert_sensorlist")
        self._logger.info("converting: "+data)
        sensorlist=[]
        data=data.split(";")
        for element in data:
            if not element: continue
            tempList=[]
            temp=element.split("=")
            tempList.append(temp[0])
            temp=temp[1].split(",")
            tempList.append([])
            for subElement in temp:
                tempList[1].append(self.check_subelement(subElement))
            sensorlist.append(tempList)
        self._logger.info("convert complete: "+str(sensorlist))
        return sensorlist
    
    def handle_respons(self):
        self._logger.info("entered handle_respons")
        respons=self.convert_sensorlist(self.receive_data().decode())
        self._logger.info("received: "+str(respons))
        if len(respons)!=1:
            raise Ev3Exception("responslist had more the one elements, that should not happen: "+str(respons))
        respons=respons[0]
        if respons[0]!="respons":
            raise Ev3Exception("incorrect responsform: "+str(respons))
        respons=respons[1]
        if type(respons[0])!=bool:
            raise Ev3Exception("respons does not contain a bool telling if the operation was succesful or not")
        if not respons[0] and not type(respons[1])==str:
            raise Ev3Exception("respons was unsuccessful and does not contain a string telling why")
        if len(respons)==1:
            respons.append("")
        if len(respons)>2:
            self._logger.info("respons longer than normal")
            temp=[]
            for i in range(1,len(respons)):
                temp.append(respons[i])
            return respons[0],temp
        return respons
    
    def is_digit(self,element):
        try:
            int(element)
            return True
        except ValueError:
            return False
    
    def is_float(self,element):
        try:
            float(element)
            return True
        except ValueError:
            return False
            
    def check_subelement(self,subelement):
        if self.is_digit(subelement):
            return int(subelement)
        elif self.is_float(subelement):
            return float(subelement)
        else:
            if subelement=="True":
                return True
            elif subelement=="False":
                return False
            else:
                return subelement
    
    def set_mode(self,mode):
        global cv2
        self.send_command("set_mode="+mode)
        success,value=self.handle_respons()
        if not success:
            raise Ev3Exception(value)
        if mode=="cv":
            import cv2
        self._logger.info("mode successfully set")
        
    def set_size(self,size):
        self.send_command("set_size="+str(size[0])+","+str(size[1]))
        success,value=self.handle_respons()
        if not success:
            raise Ev3Exception(value)
        else:
            self.__size=(value[0],value[1])
        self._logger.info("size successfully set")
        
    def receive_data(self):
        self._logger.info("entered receive_data")
        readable, writable, exceptional = select.select([self._s], [self._s], [self._s])
        complete_data_set=bytearray()
        temp=[]
        while not complete_data_set:
            self._logger.info("waiting for data to receive")
            start_time=time.time()
            while self._s not in readable:
                readable, writable, exceptional = select.select([self._s], [self._s], [self._s])
                if time.time()>start_time+self._timeout:
                    raise Ev3Exception("the ev3 did not respond within the current timeout. Solution: try again with logging set to INFO")
            if self._s in readable:
                self._logger.info("receiving data")
                while self._s in readable:
                    data=self._s.recv(2048)
                    if not data:
                        self._logger.warning("broken connection")
                        raise socket.error
                    temp.append(data)
                    readable, writable, exceptional = select.select([self._s], [], [],0.15)
            for element in temp:
                for subelement in element:
                    complete_data_set.append(subelement)
        self._logger.info("transfer complete,received:")
        return complete_data_set
        
    def send_data(self,data):
        self._logger.info("entered send_data,sending: "+data)
        readable, writable, exceptional = select.select([self._s], [self._s], [])
        while self._s not in writable:
            readable, writable, exceptional = select.select([self._s], [self._s], [])
        self._s.sendall(data.encode()) 
        self._logger.info("send complete")

    #all commands go by this method if we wan to buffer the later on and send them all together
    def send_command(self,data):
        self._logger.info("entered send_command,sending: "+data)
        self.send_data(data + ";")
        self._logger.info("send complete")
        
    def convert_cv(self,data):
        temp_image=cv2.imdecode( np.asarray(bytearray(data), dtype=np.uint8), 1 )
        b,g,r = cv2.split(temp_image)
        img = cv2.merge((r,g,b))
        im = Image.fromarray(img)
        return ImageTk.PhotoImage(image=im)
    
    def convert_pygame(self,data):
        return ImageTk.PhotoImage(Image.frombytes("RGBA",self.__size,bytes(data)))
    
    #returns a photoimage object compliant with tkinter
    def get_frame(self):
        self.send_command("get_frame=")
        value=self.receive_data()
        return self.__convert[self.__mode](value)
    
    def get_sound_intensity(self):
        self.send_command("get_sound_intensity=")
        success,value=self.handle_respons()
        if not success:
            raise Ev3Exception(value)
        return value
    
    def get_size(self):
        return self.__size

