import cv2
import face_recognition
import os
import pickle

# Importing the images folder in a loop list
folderPath = '/Users/user/Desktop/FYP PRACTICE/images'
PathList = os.listdir(folderPath)
imgList = []
studentIds = []

print(PathList)
for path in PathList:
    # Load the image
    img = cv2.imread(os.path.join(folderPath, path))

    # Check if the image is loaded successfully
    if img is not None:
        imgList.append(img)
        studentIds.append(os.path.splitext(path)[0])
    else:
        print(f"Error loading image: {os.path.join(folderPath, path)}")

# Print the length of imgModelist
print(f"Number of valid images in the list: {len(imgList)}")
print(studentIds)





"""def FindEncordings(imagesList):
    encodeList= []
    for img in imagesList:
        img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)

 
    return encodeList
"""
#create encoedings
def FindEncordings(imagesList):
    encodeList = []
    for img in imagesList:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        face_encodings = face_recognition.face_encodings(img)
        if face_encodings:
            encodeList.append(face_encodings[0])

    return encodeList

print("encoding starts....")
encodeListtKnown = FindEncordings(imgList)
#print(encodeListtKnown)
encodeListtKnownWithIds = [encodeListtKnown,studentIds]
print("encoding ends....")



# creating pikle file to store the encodings
file = open("EncodeFile.p",'wb')
pickle.dump(encodeListtKnownWithIds,file)
file.close()
print("file saved")
