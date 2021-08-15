import numpy as np
import cv2
import time
import datetime
from collections import deque
from twilio.rest import Client

def is_person_present(frame, thresh=1100):
    
    
    global foog
    kernel= None
    #Subtract background
    fgmask = foog.apply(frame)

    # removing shadows
    ret, fgmask = cv2.threshold(fgmask, 250, 255, cv2.THRESH_BINARY)

    # dialation to increase area of person
    fgmask = cv2.dilate(fgmask,kernel,iterations = 4)

    # contour detection
    contours, hierarchy = cv2.findContours(fgmask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
     
    # Cheking if contour area is greater than thresh
    if contours and cv2.contourArea(max(contours, key = cv2.contourArea)) > thresh:
            
           
            cnt = max(contours, key = cv2.contourArea)

            # Drawing rect
            x,y,w,h = cv2.boundingRect(cnt)
            cv2.rectangle(frame,(x ,y),(x+w,y+h),(0,0,255),2)
            cv2.putText(frame,'Person Detected',(x,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0,255,0), 1, cv2.LINE_AA)
            
            return True, frame
        
        
    # Otherwise report there was no one present
    else:
        return False, frame
    

#twilio api sending message
def send_message(body):

    # Your Account SID from twilio.com/console
    account_sid = info_dict['account_sid']


    # Your Auth Token from twilio.com/console
    auth_token  = info_dict['auth_token']


    client = Client(account_sid, auth_token)

    message = client.messages.create( to = info_dict['your_num'], from_ = info_dict['trial_num'], body= body)



cv2.namedWindow('frame', cv2.WINDOW_NORMAL)


#  test local video
#cap = cv2.VideoCapture('sample_video.mp4')

# Read the video stream from the camera
cap = cv2.VideoCapture('https://192.168.2.6:8080/video')


# Get width and height of the frame
width = int(cap.get(3))
height = int(cap.get(4))



# Initialize background Subtractor
foog = cv2.createBackgroundSubtractorMOG2( detectShadows = True, varThreshold = 100, history = 1600)



status = False


patience = 7


detection_thresh = 15

#initializing time for patience
initial_time = None

#Deque object creation
de = deque([False] * detection_thresh, maxlen=detection_thresh)


fps = 0 
frame_counter = 0
start_time = time.time()


# Read and store the credentials information in a dict
with open('credentials.txt', 'r') as myfile:
     data = myfile.read()

info_dict = eval(data)


while(True):
    
    ret, frame = cap.read()
    if not ret:
        break 
            
    # returns bool and frame
    detected, annotated_image = is_person_present(frame)  
    
    # append deque with above bool
    de.appendleft(detected)
     
    # if not of times the person is present in freame greater than threshold then proceed  
    #  initialize the videowriter once person is detected
    if sum(de) == detection_thresh and not status:                       
            status = True
            entry_time = datetime.datetime.now().strftime("%A, %I-%M-%S %p %d %B %Y")
            #print("before out")
            out = cv2.VideoWriter('D://outputs/{}.mp4'.format(entry_time), cv2.VideoWriter_fourcc(*'MJPG'), 15.0, (width, height))

    # If status is True but the person is not in the current frame
    if status and not detected:
        
        # start the patience timer only if the person has not been detected for a few frames
        if sum(de) > (detection_thresh/2): 
            
            if initial_time is None:
                initial_time = time.time()
            
        elif initial_time is not None:        
            
            # If patience runs out and the person is still not detected then set the status to False
            #  send a text message.
            if  time.time() - initial_time >= patience:
                status = False
                exit_time = datetime.datetime.now().strftime("%A, %I:%M:%S %p %d %B %Y")
                out.release()
                initial_time = None
            
                body = "Alert: \n A Person Entered the Room at {} \n Left the room at {}".format(entry_time, exit_time)
                send_message(body)
    
    # If significant amount of detections  has occured then reset Initial Time.
    elif status and sum(de) > (detection_thresh/2):
        initial_time = None
    

    current_time = datetime.datetime.now().strftime("%A, %I:%M:%S %p %d %B %Y")


    cv2.putText(annotated_image, 'FPS: {:.2f}'.format(fps), (510, 450), cv2.FONT_HERSHEY_COMPLEX, 0.6, (0, 0, 255),2)
    
  
    cv2.putText(annotated_image, current_time, (310, 20), cv2.FONT_HERSHEY_COMPLEX, 0.5, (0, 0, 255),1)    
    
    
    cv2.putText(annotated_image, 'Room Occupied: {}'.format(str(status)), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                (0, 255, 0),2)

  
    if initial_time is None:
        text = 'Patience: {}'.format(patience)
    else: 
        text = 'Patience: {:.2f}'.format(max(0, patience - (time.time() - initial_time)))
        
    cv2.putText(annotated_image, text, (10, 45), cv2.FONT_HERSHEY_COMPLEX, 0.6, (0, 255, 0) , 2)   

    
    if status:
        out.write(annotated_image)
 
    
    cv2.imshow('frame',frame)
    
    #Average FPS
    frame_counter += 1
    fps = (frame_counter / (time.time() - start_time))
    
    
    if cv2.waitKey(30) == ord('q'):
        break


cap.release()
cv2.destroyAllWindows()
out.release()

