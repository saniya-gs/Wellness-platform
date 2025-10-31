from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import jwt
import datetime
from functools import wraps
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'wellness-secret-key-2024'
CORS(app)

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Saniya@123',  # CHANGE THIS if you used different password
    'database': 'wellness_db'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"❌ Database Error: {e}")
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token missing'}), 401
        try:
            token = token.split(' ')[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except:
            return jsonify({'message': 'Token invalid'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        age = data.get('age')
        gender = data.get('gender')
        
        if not all([name, email, password, age, gender]):
            return jsonify({'message': 'All fields required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'message': 'Email already registered'}), 400
        
        hashed_password = hash_password(password)
        query = "INSERT INTO users (name, email, password, age, gender) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (name, email, hashed_password, age, gender))
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ User registered: {email}")
        return jsonify({'message': 'Registration successful'}), 201
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return jsonify({'message': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'message': 'Email and password required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        hashed_password = hash_password(password)
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, hashed_password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            return jsonify({'message': 'Invalid credentials'}), 401
        
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        print(f"✅ User logged in: {email}")
        return jsonify({
            'token': token,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'age': user['age'],
                'gender': user['gender']
            }
        }), 200
    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({'message': str(e)}), 500

@app.route('/dashboard', methods=['GET'])
@token_required
def dashboard(current_user_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (current_user_id,))
        user = cursor.fetchone()
        
        cursor.execute("SELECT * FROM user_metrics WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (current_user_id,))
        metrics = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({'user': user, 'metrics': metrics}), 200
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return jsonify({'message': str(e)}), 500

@app.route('/submit_metrics', methods=['POST'])
@token_required
def submit_metrics(current_user_id):
    try:
        data = request.get_json()
        height = float(data.get('height'))
        weight = float(data.get('weight'))
        dietary_preference = data.get('dietary_preference')
        fitness_goal = data.get('fitness_goal')
        allergies = data.get('allergies', '')
        
        bmi = round(weight / ((height / 100) ** 2), 2)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """INSERT INTO user_metrics 
                   (user_id, height, weight, bmi, dietary_preference, fitness_goal, allergies)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (current_user_id, height, weight, bmi, dietary_preference, fitness_goal, allergies))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Metrics updated', 'bmi': bmi}), 200
    except Exception as e:
        print(f"❌ Metrics error: {e}")
        return jsonify({'message': str(e)}), 500

@app.route('/recommend_physical', methods=['POST'])
@token_required
def recommend_physical(current_user_id):
    try:
        data = request.get_json()
        rec_type = data.get('type', 'meal')
        
        meals = {
            'Breakfast': [
                {'name': 'Oatmeal Bowl', 'calories': 320, 'protein': 12, 'carbs': 54},
                {'name': 'Greek Yogurt Parfait', 'calories': 280, 'protein': 18, 'carbs': 35},
                {'name': 'Smoothie Bowl', 'calories': 290, 'protein': 15, 'carbs': 45},
                {'name': 'Avocado Toast', 'calories': 310, 'protein': 10, 'carbs': 38}
            ],
            'Lunch': [
                {'name': 'Quinoa Buddha Bowl', 'calories': 450, 'protein': 18, 'carbs': 62},
                {'name': 'Grilled Chicken Salad', 'calories': 420, 'protein': 35, 'carbs': 28},
                {'name': 'Lentil Soup', 'calories': 390, 'protein': 20, 'carbs': 58},
                {'name': 'Veggie Wrap', 'calories': 380, 'protein': 15, 'carbs': 52}
            ],
            'Dinner': [
                {'name': 'Salmon with Veggies', 'calories': 480, 'protein': 38, 'carbs': 32},
                {'name': 'Tofu Stir Fry', 'calories': 440, 'protein': 22, 'carbs': 52},
                {'name': 'Chicken with Rice', 'calories': 520, 'protein': 42, 'carbs': 45},
                {'name': 'Pasta Primavera', 'calories': 460, 'protein': 18, 'carbs': 68}
            ],
            'Snacks': [
                {'name': 'Mixed Nuts', 'calories': 180, 'protein': 6, 'carbs': 8},
                {'name': 'Protein Bar', 'calories': 200, 'protein': 12, 'carbs': 24},
                {'name': 'Hummus with Veggies', 'calories': 150, 'protein': 5, 'carbs': 18},
                {'name': 'Greek Yogurt', 'calories': 160, 'protein': 15, 'carbs': 12}
            ]
        }
        
        exercises = [
            {'name': 'Push-ups', 'sets': 4, 'reps': 15, 'duration': 10, 'calories': 70, 'instructions': 'Keep body straight'},
            {'name': 'Squats', 'sets': 4, 'reps': 20, 'duration': 12, 'calories': 80, 'instructions': 'Squat low, push through heels'},
            {'name': 'Lunges', 'sets': 3, 'reps': 15, 'duration': 12, 'calories': 75, 'instructions': 'Step forward, drop back knee'},
            {'name': 'Plank', 'sets': 3, 'reps': 1, 'duration': 8, 'calories': 50, 'instructions': 'Hold 60 seconds'},
            {'name': 'Burpees', 'sets': 3, 'reps': 12, 'duration': 10, 'calories': 100, 'instructions': 'Full body movement'}
        ]
        
        if rec_type == 'meal':
            return jsonify({'meals': meals}), 200
        else:
            return jsonify({'exercises': exercises}), 200
    except Exception as e:
        print(f"❌ Physical recommendation error: {e}")
        return jsonify({'message': str(e)}), 500

@app.route('/submit_mental', methods=['POST'])
@token_required
def submit_mental(current_user_id):
    try:
        data = request.get_json()
        anxiety = int(data.get('anxiety', 0))
        depression = int(data.get('depression', 0))
        stress = int(data.get('stress', 0))
        sleep = int(data.get('sleep', 3))
        social = int(data.get('social', 3))
        
        scores = {
            'anxiety': 100 - (anxiety * 20),
            'depression': 100 - (depression * 20),
            'stress': 100 - (stress * 20),
            'sleep': sleep * 20,
            'social': social * 20
        }
        scores['overall'] = sum(scores.values()) / 5
        
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """INSERT INTO mental_health_scores 
                   (user_id, anxiety_score, depression_score, stress_score, sleep_score, social_score, overall_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (current_user_id, scores['anxiety'], scores['depression'],
                              scores['stress'], scores['sleep'], scores['social'], scores['overall']))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'scores': scores}), 200
    except Exception as e:
        print(f"❌ Mental health error: {e}")
        return jsonify({'message': str(e)}), 500

@app.route('/recommend_yoga', methods=['POST'])
@token_required
def recommend_yoga(current_user_id):
    try:
        yoga = [
            {'name': 'Child\'s Pose', 'difficulty': 'Beginner', 'duration': 5, 'benefits': 'Stress relief', 'youtube': 'https://youtube.com/watch?v=2MTmAT2d4vI'},
            {'name': 'Downward Dog', 'difficulty': 'Beginner', 'duration': 3, 'benefits': 'Full body stretch', 'youtube': 'https://youtube.com/watch?v=pvz0RY9MJG8'},
            {'name': 'Warrior II', 'difficulty': 'Intermediate', 'duration': 4, 'benefits': 'Strength, focus', 'youtube': 'https://youtube.com/watch?v=69-rVpIH6Vw'},
            {'name': 'Tree Pose', 'difficulty': 'Intermediate', 'duration': 3, 'benefits': 'Balance', 'youtube': 'https://youtube.com/watch?v=VqnJJBFhKRo'},
            {'name': 'Corpse Pose', 'difficulty': 'Beginner', 'duration': 10, 'benefits': 'Deep relaxation', 'youtube': 'https://youtube.com/watch?v=1VYlOKUdylM'}
        ]
        return jsonify({'yoga': yoga}), 200
    except Exception as e:
        print(f"❌ Yoga error: {e}")
        return jsonify({'message': str(e)}), 500

@app.route('/update_activity', methods=['POST'])
@token_required
def update_activity(current_user_id):
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO user_activity (user_id, activity_type, activity_value) VALUES (%s, %s, %s)"
        cursor.execute(query, (current_user_id, data.get('type'), data.get('value')))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Activity tracked'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    print("🚀 Starting Wellness Platform Backend...")
    print("📍 Server running at: http://localhost:5000")
    print("✅ Ready to accept connections!")
    app.run(debug=True, host='0.0.0.0', port=5000)