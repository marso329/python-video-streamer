import os
import socket,select,logging
import sys
global pygame,cv2,pyaudio,math,audioop
class Streamer():
    def __init__(self):
        self.__mode=None
        self.__modes={"pygame":self.set_pygame_mode,"cv":self.set_cv_mode}
        self.__set_size={"pygame":self.set_pygame_size,"cv":self.set_cv_size}
        self.__reset={"pygame":self.reset_pygame,"cv":self.reset_cv}
        self.__get={"pygame":self.get_pygame,"cv":self.get_cv}
        self.__path="//dev/video0"
        #everything for the interal logger
        self._logger = logging.getLogger('Brick_logger')
        self._logger.setLevel(logging.WARNING)
        self._console_handler = logging.StreamHandler()
        self._console_handler.setLevel(logging.NOTSET)
        self._formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self._console_handler.setFormatter(self._formatter)
        self._logger.addHandler(self._console_handler)
        
        #everything for the brick
        self._s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._s.bind(('', 5000))
        self._conn=None
        self._addr=None
        self.__camera=None
        self.__sound_enabled=False
        self._logger.info("setup complete")
        self.mainloop()

    #Judging by the name, this should be the mainloop
    def mainloop(self):
        self._logger.info("entered mainloop function")
        self.wait_for_connection()
        while True:
            commands=self.split_command(self.receive_data())
            for element in commands:
                self.commandhandler(element)
                
    def is_number(self,value):
        try:
            int(value)
            return True
        except ValueError:
            return False

    def is_float(self,value):
        try:
            float(value)
            return True
        except ValueError:
            return False
        
    def checkSubelement(self,subelement):
        if self.is_number(subelement):
            return int(subelement)
        if self.is_float(subelement):
            return float(subelement)
        else:
            if subelement=="True":
                return True
            elif subelement=="False":
                return False
            else:
                return subelement
    
    #a simple function that sends data to the user
    def send_data(self,data):
        self._logger.info("sending data: ")
        self._conn.sendall(data.encode())
        self._logger.info("send complete")
        
    #takes in a received string and converts it into a list of commands that can easily be used
    def split_command(self,data):
        self._logger.info("translating string to list: "+data )
        commandlist=[]
        data=data.split(";")
        del data[-1]
        for element in data:
            if "=" not in element:
                commandlist.append([element])
            else:
                tempList=[]
                element=element.split("=")
                tempList.append(element[0])
                temp=[]
                element[1]=element[1].split(",")
                for element in element[1]:
                    temp.append(element)
                tempList.append(temp)
                commandlist.append(tempList)
        self._logger.info("translate complete: "+str(commandlist))
        return commandlist
            
    def receive_data(self):
        self._logger.info("entered receive_data")
        self._logger.info("waiting for data to receive")
        complete_data_set=""
        while not complete_data_set:
            readable, writable, exceptional = select.select([self._conn], [self._conn], [self._conn])
            while self._conn not in readable:
                #self._logger.info("waiting for data to receive")
                readable, writable, exceptional = select.select([self._conn], [self._conn], [self._conn])
            while self._conn in readable:
                self._logger.info("receiving data")
                try:
                    data=self._conn.recv(64).decode()
                except (socket.herror,socket.error,socket.gaierror,socket.timeout):
                    self._logger.warning("broken connection")
                    self.reset_connection()
                if not data:
                    self._logger.warning("broken connection")
                    self.reset_connection()
                complete_data_set=complete_data_set+data
                readable, writable, exceptional = select.select([self._conn], [self._conn], [self._conn])
        self._logger.info("datatransfer complete")
        return complete_data_set
    
    #All the commands from the PC ends up here
    def commandhandler(self,data):
        self._logger.info("commandhandler is handling:"+str(data))
        if len(data)>1:
            for i in range(len(data[1])):
                data[1][i]=self.checkSubelement(data[1][i])
        self._logger.info("command after checksubelement: "+str(data))
        if data[0]=="get_frame":
            self.__get[self.__mode]()
        elif data[0]=="set_mode":
            self.set_mode(data[1])
        elif data[0]=="set_size":
            self.__set_size[self.__mode](data[1])
        elif data[0]=="get_sound_intensity":
            self.get_sound_intensity()
        else:
            self._logger.info("ignored command because not defined")
    def get_sound_intensity(self):
        global pyaudio,math,audioop
        if not self.__sound_enabled:
            import pyaudio
            import math
            import audioop
            self.__p=pyaudio.PyAudio()
            self.__audio_stream= self.__p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1024)
            self.__sound_enabled=True
            self.__audio_stream.stop_stream()
        self.__audio_stream.start_stream()
        values = [math.sqrt(abs(audioop.avg(self.__audio_stream.read(1024), 4))) for x in range(5)]
        self.__audio_stream.stop_stream()
        r = sum(values)
        self.send_data("respons=True,"+str(r))
        
            
    def set_cv_size(self,data):
        self._logger.info("setting cv size to: "+str(data))
        self.__camera.set(3,float(data[0]))
        self.__camera.set(4,float(data[1]))
        self.send_data("respons=True,"+str(self.__camera.get(3))+","+str(self.__camera.get(4)))
        
    def set_pygame_size(self,data):
        self._logger.info("setting pygame size to: "+str(data))
        self.__camera.stop()
        self.__camera=pygame.camera.Camera(self.__path,(data[0],data[1]))
        self.__camera.start()
        temp=self.__camera.get_size()
        self.send_data("respons=True,"+str(temp[0])+","+str(temp[1]))
        
    def set_cv_mode(self):
        global cv2
        pos=0
        if self.__path=="//dev/video1":
            pos=1
        if self.__mode==None:
            import cv2
            self.__camera=cv2.VideoCapture(pos)
        elif self.__mode!="cv":
            import cv2
            self.__reset[self.__mode]()
            self.__camera=cv2.VideoCapture(pos)
        else:
            pass
        self.__mode="cv"
        
    def set_pygame_mode(self):
        global pygame
        self._logger.info("setting pygame mode")
        if self.__mode==None:
            import pygame
            import pygame.camera
            import pygame.image
            pygame.init()
            pygame.camera.init()
            self.__camera=pygame.camera.Camera(self.__path)
            self.__camera.start()
        elif self.__mode!="pygame":
            self.__reset[self.__mode]()
            import pygame
            import pygame.camera
            import pygame.image
            pygame.init()
            pygame.camera.init()
            self.__camera=pygame.camera.Camera(self.__path)
            self.__camera.start()
        self.__mode="pygame"
        
    def set_mode(self,data):
        self._logger.info("setting mode: "+str(data[0]))
        if data[0] not in self.__modes:
            self.send_data("False=NoSuchMode")
        if not os.path.exists("//dev/video0"):
            if not os.path.exists("//dev/video1"):
                self.send_data("respons=False=NoCameraConnected")
            else:
                self.__path="//dev/video1"
                self.__modes[data[0]]()
                self.send_data("respons=True")
        else:
            self.__modes[data[0]]()
            self.send_data("respons=True")
        
    def get_pygame(self):
        self._logger.info("getting pygame frame")
        image=self.__camera.get_image()
        pil_string_image = pygame.image.tostring(image, "RGBA",False)
        try:
            self._conn.sendall(pil_string_image)
        except socket.error:
            self.reset_connection()
            
    def get_cv(self):
        self._logger.info("getting cv frame")
        for i in range(4):  
            _,frame=self.__camera.read()
        frame = cv2.imencode('.jpg', frame)[1].tostring()
        try:
            self._conn.sendall(frame)
        except socket.error:
            self.reset_connection()

    #waits for a user to connect
    def wait_for_connection(self):
        self._logger.info("waiting for connection")
        self._s.listen(1)
        self._conn, self._addr = self._s.accept()
        self._s.setblocking(0)
        self._logger.info("connection accepted")
        
    def reset_pygame(self):
        self._logger.info("stoping pygame camera")
        self.__camera.stop()
        
    def reset_cv(self):
        self._logger.info("stoping cv camera")
        self.__camera.release()
        
    #closes the sockets and waits for a user to connect
    def reset_connection(self):
        self._logger.info("reseting connection")
        self._s.close()
        self._s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._s.bind(('', 5000))
        self._conn=None
        self._addr=None
        self.__path="//dev/video0"
        self.mainloop()
temp=Streamer()
