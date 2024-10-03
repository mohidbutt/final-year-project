import cv2
import face_recognition
import pickle
import os
import numpy as np
import time
import datetime
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from EncordingGenerator import generate_encodings

# Initialize Firebase only if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': "https://visioattend-bc454-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

def check_new_enrollment(section):
    ref = db.reference(f'courses/{section}/newEnroll')
    try:
        data = ref.get()
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def reset_new_enrollment(section):
    ref = db.reference(f'courses/{section}/newEnroll')
    ref.set(False)






def save_attendance_to_firebase(course_id, students_in_class, class_duration_minutes, class_end_time, studentIds):
    course_ref = db.reference(f'courses/{course_id}/enrollStudents')
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # Fetch the existing attendance data to determine the current lecture index
    existing_attendance = {}
    for student_id in studentIds:
        attendance_ref = course_ref.child(student_id).child('attendance')
        attendance_data = attendance_ref.get()
        if attendance_data is None:
            attendance_data = []
        existing_attendance[student_id] = attendance_data

    # Determine the current lecture index (assumes all students have the same number of records)
    current_lecture_index = 0
    for data in existing_attendance.values():
        if len(data) > current_lecture_index:
            current_lecture_index = len(data)

    for student_id in studentIds:
        if student_id not in students_in_class:
            students_in_class[student_id] = {'in_times': [0], 'exit_times': [0]}

    for student_id, record in students_in_class.items():
        if len(record['in_times']) > len(record['exit_times']):
            record['exit_times'].append(class_end_time)

        total_time_spent_seconds = sum(exit_time - in_time for in_time, exit_time in zip(record['in_times'], record['exit_times']))

        # Format time spent in H:MM:SS
        hours, remainder = divmod(total_time_spent_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        formatted_time_spent = f"{int(hours)}:{int(minutes):02}:{int(seconds):02}"

        # Save formatted time spent
        time_spent_ref = course_ref.child(student_id).child('timeSpent')
        time_spent_list = time_spent_ref.get()
        if time_spent_list is None:
            time_spent_list = ["-"] * current_lecture_index
        time_spent_list.append(formatted_time_spent)
        time_spent_ref.set(time_spent_list)

        # Round attendance percentage and save
        attendance_percentage = round((total_time_spent_seconds / (class_duration_minutes * 60)) * 100)

        attendance_ref = course_ref.child(student_id).child('attendance')
        attendance_list = attendance_ref.get()
        if attendance_list is None:
            attendance_list = ["-"] * current_lecture_index
        attendance_list.append(attendance_percentage)
        attendance_ref.set(attendance_list)

        # Save in times
        in_time_ref = course_ref.child(student_id).child('in_Time')
        in_time_list = in_time_ref.get()
        if in_time_list is None:
            in_time_list = ["-"] * current_lecture_index

        in_times_for_session = [time.strftime('%H:%M:%S', time.localtime(time_in)) if time_in != 0 else '00:00:00' for time_in in record['in_times']]
        in_time_list.append(in_times_for_session)
        in_time_ref.set(in_time_list)

        # Save out times
        out_time_ref = course_ref.child(student_id).child('out_Time')
        out_time_list = out_time_ref.get()
        if out_time_list is None:
            out_time_list = ["-"] * current_lecture_index

        out_times_for_session = [time.strftime('%H:%M:%S', time.localtime(time_out)) if time_out != 0 else '00:00:00' for time_out in record['exit_times']]
        out_time_list.append(out_times_for_session)
        out_time_ref.set(out_time_list)

    # Save current date in dates list
    date_ref = db.reference(f'courses/{course_id}/dates')
    dates_list = date_ref.get()
    if dates_list is None:
        dates_list = []
    if current_date not in dates_list:
        dates_list.append(current_date)
        date_ref.set(dates_list)



def calculate_precision_recall(ground_truth, detected_students):
    true_positives = len(ground_truth.intersection(detected_students))
    false_positives = len(detected_students - ground_truth)
    false_negatives = len(ground_truth - detected_students)
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    
    return precision, recall

def calculate_accuracy(ground_truth, detected_students):
    true_positives = len(ground_truth.intersection(detected_students))
    total = len(ground_truth)
    
    accuracy = true_positives / total if total > 0 else 0
    return accuracy

def get_current_time():
    return time.time()

def get_active_slot():
    ref = db.reference('ReserveRoom/SDT-318/timeSlots')
    try:
        slots = ref.get()
        print(f"Retrieved slots data: {slots}")

        if slots is None:
            print("No slots data found or path is incorrect.")
            return None

        current_time = datetime.datetime.now()
        current_time_str = current_time.strftime("%H:%M")
        print(f"Current time: {current_time_str}")

        for slot_name, slot_info in slots.items():
            start_time = slot_info.get('start_time', '').strip()
            end_time = slot_info.get('end_time', '').strip()
            course_id = slot_info.get('courseId', '')

            print(f"Checking slot: {slot_name}")
            print(f"Start time: {start_time}, End time: {end_time}")

            if start_time and end_time:
                if start_time <= current_time_str < end_time:
                    print(f"Active slot found: {slot_name}")
                    return slot_info

    except Exception as e:
        print(f"Error fetching time slots: {e}")

    print("No active slot found within the given time range.")
    return None


def main():
    while True:
        active_slot = get_active_slot()
        
        if not active_slot:
            print("No active slot found. Checking again in 10 seconds...")
            time.sleep(10)
            continue

        section = active_slot['courseId']
        print(f"Active slot found for section: {section}")

        if check_new_enrollment(section):
            print(f"New enrollment detected in {section}. Updating encodings...")
            generate_encodings(section)
            reset_new_enrollment(section)

        encoding_file = f"EncodeFile_{section}.p"
        if not os.path.exists(encoding_file):
            print(f"Encoding file for section {section} not found. Please generate encodings first.")
            time.sleep(10)
            continue

        print(f"Loading aggregated encodings for section: {section}....")
        with open(encoding_file, 'rb') as file:
            encode_dict = pickle.load(file)

        studentIds = list(encode_dict.keys())
        print("Encodings loaded")

        class_duration_minutes = 1
        total_unique_students = len(studentIds)
        ground_truth = set(studentIds)
        detected_students = set()

        class_start_time = time.time()
        students_in_class = {}

        face_detection_timeout = 10
        unknown_face_detection_interval = 10  # Interval to ignore repeated unknown face detections (in seconds)
        unknown_face_last_detected = {}  # Tracks the last time unknown faces were detected

        cap_incoming = cv2.VideoCapture(0)
        cap_incoming.set(3, 640)  # Set resolution width
        cap_incoming.set(4, 480)  # Set resolution height

        cap_outgoing = cv2.VideoCapture(1)  # Change camera index if necessary
        cap_outgoing.set(3, 640)  # Set resolution width
        cap_outgoing.set(4, 480)  # Set resolution height

        while True:
            current_time = get_current_time()

            success_incoming, img_incoming = cap_incoming.read()
            success_outgoing, img_outgoing = cap_outgoing.read()

            if not success_incoming or not success_outgoing:
                print("Failed to read from one of the cameras")
                break

            imgs_incoming = cv2.resize(img_incoming, (0, 0), None, 0.25, 0.25)
            imgs_incoming = cv2.cvtColor(imgs_incoming, cv2.COLOR_BGR2RGB)

            imgs_outgoing = cv2.resize(img_outgoing, (0, 0), None, 0.25, 0.25)
            imgs_outgoing = cv2.cvtColor(imgs_outgoing, cv2.COLOR_BGR2RGB)

            faceCurFrame_incoming = face_recognition.face_locations(imgs_incoming)
            encodeCurFrame_incoming = face_recognition.face_encodings(imgs_incoming, faceCurFrame_incoming)

            for encodeFace, facLoc in zip(encodeCurFrame_incoming, faceCurFrame_incoming):
                face_id = tuple(encodeFace)
                matches = face_recognition.compare_faces(list(encode_dict.values()), encodeFace, tolerance=0.6)
                face_distances = face_recognition.face_distance(list(encode_dict.values()), encodeFace)

                if True in matches:
                    best_match_index = np.argmin(face_distances)
                    student_id = studentIds[best_match_index]
                    detected_students.add(student_id)

                    if student_id not in students_in_class:
                        students_in_class[student_id] = {'present': True, 'in_times': [current_time], 'exit_times': []}
                        print(f"Student {student_id} entered at {time.strftime('%H:%M:%S', time.localtime(current_time))}")
                    else:
                        if not students_in_class[student_id]['present']:
                            students_in_class[student_id]['present'] = True
                            students_in_class[student_id]['in_times'].append(current_time)
                            print(f"Student {student_id} entered at {time.strftime('%H:%M:%S', time.localtime(current_time))}")

                    top, right, bottom, left = facLoc
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    cv2.rectangle(img_incoming, (left, top), (right, bottom), (0, 255, 0), 2)  # Green rectangle for known face

                else:
                    if face_id not in unknown_face_last_detected or current_time - unknown_face_last_detected[face_id] >= unknown_face_detection_interval:
                        unknown_face_last_detected[face_id] = current_time
                        top, right, bottom, left = facLoc
                        top *= 4
                        right *= 4
                        bottom *= 4
                        left *= 4
                        cv2.rectangle(img_incoming, (left, top), (right, bottom), (0, 0, 255), 2)  # Red rectangle for unknown face
                        print("Unknown face detected")

            faceCurFrame_outgoing = face_recognition.face_locations(imgs_outgoing)
            encodeCurFrame_outgoing = face_recognition.face_encodings(imgs_outgoing, faceCurFrame_outgoing)

            for encodeFace, facLoc in zip(encodeCurFrame_outgoing, faceCurFrame_outgoing):
                face_id = tuple(encodeFace)
                matches = face_recognition.compare_faces(list(encode_dict.values()), encodeFace, tolerance=0.6)
                face_distances = face_recognition.face_distance(list(encode_dict.values()), encodeFace)

                if True in matches:
                    best_match_index = np.argmin(face_distances)
                    student_id = studentIds[best_match_index]
                    detected_students.add(student_id)

                    if student_id in students_in_class and students_in_class[student_id]['present']:
                        students_in_class[student_id]['present'] = False
                        students_in_class[student_id]['exit_times'].append(current_time)
                        print(f"Student {student_id} exited at {time.strftime('%H:%M:%S', time.localtime(current_time))}")

                    top, right, bottom, left = facLoc
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    cv2.rectangle(img_outgoing, (left, top), (right, bottom), (0, 255, 0), 2)  # Green rectangle for known face

                else:
                    if face_id not in unknown_face_last_detected or current_time - unknown_face_last_detected[face_id] >= unknown_face_detection_interval:
                        unknown_face_last_detected[face_id] = current_time
                        top, right, bottom, left = facLoc
                        top *= 4
                        right *= 4
                        bottom *= 4
                        left *= 4
                        cv2.rectangle(img_outgoing, (left, top), (right, bottom), (0, 0, 255), 2)  # Red rectangle for unknown face
                        print("Unknown face detected")

            elapsed_time = current_time - class_start_time
            if elapsed_time >= class_duration_minutes * 60:
                print("Class duration reached, saving attendance...")
                class_end_time = get_current_time()
                save_attendance_to_firebase(section, students_in_class, class_duration_minutes, class_end_time, studentIds)

                precision, recall = calculate_precision_recall(ground_truth, detected_students)
                accuracy = calculate_accuracy(ground_truth, detected_students)

                print(f"Accuracy: {accuracy * 100:.2f}%, Precision: {precision * 100:.2f}%, Recall: {recall * 100:.2f}%")

                for student_id, record in students_in_class.items():
                    if len(record['in_times']) > len(record['exit_times']):
                        record['exit_times'].append(class_end_time)

                    total_time_spent = sum(exit_time - in_time for in_time, exit_time in zip(record['in_times'], record['exit_times']))
                    print(f"Student {student_id} total time spent: {total_time_spent} seconds")

                break

            cv2.imshow("Incoming Camera", img_incoming)
            cv2.imshow("Outgoing Camera", img_outgoing)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap_incoming.release()
        cap_outgoing.release()
        cv2.destroyAllWindows()
        time.sleep(10)

if __name__ == "__main__":
    main()
