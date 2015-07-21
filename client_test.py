from client import Receiver
import time
import sys
if sys.version_info[0]>2:
    import tkinter as Tkinter
else:
    import Tkinter 

test = Receiver("10.42.0.3", "pygame", (320, 240))
root = Tkinter.Tk()
lmain = Tkinter.Label(root)
lmain.pack()
while True:
    #temp = test.get_frame()
    #lmain.imgtk = temp
    #lmain.configure(image=temp)
    #root.update()
    print(test.get_sound_intensity())
    time.sleep(0.01)