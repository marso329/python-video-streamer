from client import Receiver
import time
import sys
if sys.version_info[0]>2:
    import tkinter as Tkinter
else:
    import Tkinter 

test = Receiver("127.0.0.1", "pygame", (320, 240))
root = Tkinter.Tk()
lmain = Tkinter.Label(root)
lmain.pack()
while True:
    temp = test.get_frame()
    lmain.imgtk = temp
    lmain.configure(image=temp)
    root.update()
    time.sleep(0.01)
