import os
import face_recognition
import pickle
import firebase_admin
from firebase_admin import credentials, storage

# Initialize Firebase Admin SDK with your credentials, Storage bucket name, and Database URL
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': "visioattend-bc454.appspot.com",  # Replace with your Firebase Storage bucket name
    'databaseURL': "https://visioattend-bc454-default-rtdb.asia-southeast1.firebasedatabase.app/" # Replace with your Firebase Realtime Database URL
})

# Initialize Firebase storage
bucket = storage.bucket()

def download_images_from_bucket(section_folder):
    local_images_dir = 'images'  # Save to the current directory
    os.makedirs(local_images_dir, exist_ok=True)
    blobs = bucket.list_blobs(prefix=section_folder)
    found_images = False
    for blob in blobs:
        if blob.content_type and 'image' in blob.content_type:
            found_images = True
            filename = os.path.basename(blob.name)
            if not any(filename.lower().endswith(ext) for ext in ['jpg', 'jpeg', 'png']):
                filename += '.jpg'  # Default to .jpg, adjust if necessary
            local_filename = os.path.join(local_images_dir, filename)
            try:
                blob.download_to_filename(local_filename)
                print(f"Downloaded image: {filename}")
            except Exception as e:
                print(f"Error downloading {filename}: {e}")

    if not found_images:
        print(f"No images found in the folder '{section_folder}'.")

def load_and_encode_images(image_folder):
    encode_dict = {}
    for filename in os.listdir(image_folder):
        if filename.startswith('.'):  # Skip hidden files
            continue
        img_path = os.path.join(image_folder, filename)
        try:
            face_image = face_recognition.load_image_file(img_path)
            face_encodings = face_recognition.face_encodings(face_image)
            if face_encodings:
                student_id = os.path.splitext(filename)[0]
                encode_dict[student_id] = face_encodings[0]
                print(f"Encoded image: {filename}")
            else:
                print(f"No faces found in image: {filename}")
        except Exception as e:
            print(f"Error processing image {img_path}: {e}")

    return encode_dict

def generate_encodings(section):
    section_folder = f'{section}/'  # Adjust to the section folder in Firebase Storage

    print(f"Downloading images from Firebase storage for section: {section}...")
    download_images_from_bucket(section_folder)

    downloaded_images = os.listdir('images')
    if not downloaded_images:
        print(f"No images were downloaded for section: {section}.")
        return
    else:
        print(f"Downloaded images for section {section}: {downloaded_images}")

    print(f"Encoding downloaded images for section: {section}...")
    encode_dict = load_and_encode_images('images')

    if not encode_dict:
        print(f"No encodings were created for section: {section}.")
        return

    encoding_file = f"EncodeFile_{section}.p"
    with open(encoding_file, 'wb') as file:
        pickle.dump(encode_dict, file)

    print(f"Encodings saved to '{encoding_file}' for section: {section}")

    # Clear the images directory
    for file in os.listdir('images'):
        file_path = os.path.join('images', file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

if __name__ == "__main__":
    section = input("Enter the section name (e.g., OOP, DSA): ").strip()
    generate_encodings(section)