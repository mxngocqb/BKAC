import sqlite3
import base64

class UserScheduleDB:
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                identify_number TEXT,
                start_time TEXT,
                end_time TEXT,
                fingerprint_image BLOB,
                face_image BLOB
            )
        ''')
        conn.commit()
        conn.close()

    def insert_user_schedule(self, user_data):
        # Decode base64 image data
        fingerprint_b64 = user_data.get("fingerPrintImage", "").split(",")[-1]
        face_b64 = user_data.get("faceImage", "").split(",")[-1]
        fingerprint_image = base64.b64decode(fingerprint_b64)
        face_image = base64.b64decode(face_b64)
        print(user_data)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_schedule (
                user_id, username, identify_number, start_time, end_time,
                fingerprint_image, face_image
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_data.get("userId"),
            user_data.get("username"),
            user_data.get("identifyNumber"),
            user_data.get("startTime"),
            user_data.get("endTime"),
            fingerprint_image,
            face_image
        ))
        conn.commit()
        conn.close()

    def get_user_schedule_by_id(self, identify_number):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user_schedule WHERE identify_number = ?', (identify_number,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "username": row[2],
                "identify_number": row[3],
                "start_time": row[4],
                "end_time": row[5],
                "fingerprint_image": base64.b64encode(row[6]).decode('utf-8') if row[6] else None,
                "face_image": base64.b64encode(row[7]).decode('utf-8') if row[7] else None
            }
        else:
            return None

    def get_all_user_schedules(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM user_schedule')
                rows = cursor.fetchall()

                user_schedules = []
                for row in rows:
                    user_schedules.append({
                        "id": row[0],
                        "user_id": row[1],
                        "username": row[2],
                        "identify_number": row[3],
                        "start_time": row[4],
                        "end_time": row[5],
                        "fingerprint_image": base64.b64encode(row[6]).decode('utf-8') if row[6] else None,
                        "face_image": base64.b64encode(row[7]).decode('utf-8') if row[7] else None
                    })
                return user_schedules
        except sqlite3.Error as e:
            print(f"Error retrieving all user schedules: {e}")
            return []

