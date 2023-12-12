import cv2
import os
import face_recognition_models
import face_recognition
import pickle
import numpy as np
import cvzone

cap = cv2.VideoCapture(0)

# Set the desired resolution
cap.set(3, 690)  # Width
cap.set(4, 480)  # Height

# Importing the modes folder in a loop list
folderModePath = '/Users/user/Desktop/FYP PRACTICE/resources/modes'
modePathList = os.listdir(folderModePath)
imgModelist = []
for path in modePathList:
    imgModelist.append(cv2.imread(os.path.join(folderModePath, path)))

# loading encoding files
print("loading encoded file....")
file = open("EncodeFile.p", 'rb')
encodeListtKnownWithIds = pickle.load(file)
file.close()
encodeListtKnown, studentIds = encodeListtKnownWithIds
#for checking print(studentIds)
print("file loaded")

imgbackground = cv2.imread('/Users/user/Desktop/FYP PRACTICE/resources/background.jpg')

while True:
    success, img = cap.read()
    # start recognition
    imgs = cv2.resize(img, (0, 0), None, 0.25, 0.24)
    imgs = cv2.cvtColor(imgs, cv2.COLOR_BGR2RGB)

    faceCurFrame = face_recognition.face_locations(imgs)
    encodecurFrame = face_recognition.face_encodings(imgs, faceCurFrame)

    for encodeFace, facLoc in zip(encodecurFrame, faceCurFrame):
        matches = face_recognition.compare_faces(encodeListtKnown, encodeFace)
        Facedistance = face_recognition.face_distance(encodeListtKnown, encodeFace)
        print("matches", matches)
        print("facedistance", Facedistance)
        matchIndex = np.argmin(Facedistance)
        print("Match Index", matchIndex)
        print(studentIds[matchIndex])

        # Draw a rectangle around the face
        top, right, bottom, left = facLoc
        top = int(top * 4)  # Since we resized the image by 0.25
        right = int(right * 4)
        bottom = int(bottom * 4)
        left = int(left * 4)
        cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 4)

    # Display the webcam feed on the left side
    imgbackground[190:190 + img.shape[0], 60:60 + img.shape[1]] = img

    # Display the image from the list on the top-right corner
    imgbackground[150:150 + imgModelist[0].shape[0],
    imgbackground.shape[1] - 120 - imgModelist[0].shape[1]:imgbackground.shape[1] - 120] = imgModelist[0]

    cv2.imshow("face attendance", imgbackground)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the video capture and close all windows
cap.release()
cv2.destroyAllWindows()
