import os
import sys
sys.path.append("..")
import ocr.utils
from paho.mqtt import client as mqtt_client
import paho.mqtt.client as mqtt
import pyvirtualcam
import time
import cv2
import random
import json
from threading import Thread


class VirtualCamera():
    def __init__(self):
        self.cam = None
        self.running = True
      
    def terminate(self):
        self.running = False
          
    def run(self, frame):
        width = frame.shape[1]
        height = frame.shape[0]
        cam = pyvirtualcam.Camera(width=width, height=height, fps=20)
        while self.running==True:
            cam.send(frame)
            cam.sleep_until_next_frame()

class AnylineOCRReader():
    def __init__(self):
        self.broker = 'broker.emqx.io'
        self.port = 8083
        self.topic = "DataCapture"
        self.results = []
        self.client = None
        self.mqtt_thread = Thread(target=self.connect_mqtt, args=())
        self.mqtt_thread.start()
        self.previous_result = ""
        
    def stop_MQTT(self):
        self.client.loop_stop()
        
    def connect_mqtt(self):
        # The callback for when the client receives a CONNACK response from the server.
        def on_connect(client, userdata, flags, rc):
            print("Connected with result code "+str(rc))

            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.
            client.subscribe(self.topic)
            self.client = client

        # The callback for when a PUBLISH message is received from the server.
        def on_message(client, userdata, msg):
            #print(msg.topic+" "+str(msg.payload))
            obj = json.loads(msg.payload)
            if "mrz" in obj:
                if self.previous_result != obj["mrz"]:
                    self.previous_result = obj["mrz"]
                    self.results.append(obj)


        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect("broker.emqx.io", 1883, 60)
        
        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        # Other loop*() functions are available that give a threaded interface and a
        # manual interface.
        client.loop_forever()

    def ocr(self, file_path):
        self.results.clear()
        result_dict = {}
        boxes = []
        img = cv2.imread(file_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = self.add_padding(img)
        img = self.resize(img)
        seconds_elapsed = 0
        while self.client==None:
            time.sleep(0.5)
            print("mqtt not connected yet")
            seconds_elapsed = seconds_elapsed + 0.5
            if seconds_elapsed>10:
                print("mqtt not connected")
                break
            
        c = VirtualCamera()
        t = Thread(target = c.run, args =(img, ))
        t.start()

        seconds_elapsed = 0
        while len(self.results)==0:
            print("waiting for results.")
            time.sleep(0.5)
            seconds_elapsed = seconds_elapsed + 0.5
            if seconds_elapsed>10:
                print("timeout")
                break                
        print("results")
        
        if len(self.results)>0:
            result = self.results[0]
            boxes = [{"text":result["mrz"].replace("\\n","\n")}]
            result_dict["elapsedTime"]=result["scanTime"]
        c.terminate()
        time.sleep(1)
        result_dict["boxes"] = boxes
        return result_dict
        
    def resize(self,img):
        width = img.shape[1]
        height = img.shape[0]
        if width>=height:
            img = cv2.resize(img, (1920, 1080))
        else:
            img = cv2.resize(img, (1080, 1920))
        return img
            
    def get_img_radio(self, img):
        width = img.shape[1]
        height = img.shape[0]
        if width>height:
            return width/height
        else:
            return height/width

    def add_padding(self, img):
        width = img.shape[1]
        height = img.shape[0]
        
        ratio = 16/9
        
        desired_height = height
        desired_width = width
        
        top = 0
        bottom = 0
        left = 0
        right = 0
        
        
        
        
        if self.get_img_radio(img) > ratio: #17/9 > 16/9 add padding to short side
            if width>height:
                desired_width = width
                desired_height = width / ratio
                top = int((desired_height - height)/2)
                bottom = top
            else:
                desired_width = height / ratio
                desired_height = height
                left = int((desired_width - width)/2)
                right = left
        else: # 4/3 < 16/9 add padding to long side
            #if width>=height:
            desired_width = height * ratio
            desired_height = height
            left = int((desired_width - width)/2)
            right = left
            #else:
            #    desired_width = width
            #    desired_height = width * ratio
            #    top = int((desired_height - height)/2)
            #    bottom = top

        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT,value=[255,255,255])
        return img 
        
if __name__ == "__main__":
    reader = AnylineOCRReader()
    result_dict = reader.ocr("test.jpg")
    print(result_dict)
    result_dict = reader.ocr("Bulgaria-passport-mini.jpg")
    print(result_dict)
    reader.stop_MQTT()
    exit()