from flask import Flask, request, jsonify
import os
import pandas as pd

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
        allergies = ','.join(data.get('allergies', []))  # store as comma-separated list
        activity_level = float(data.get('activity_level', 1.5))  # default moderate
        
        bmi = round(weight / ((height / 100) ** 2), 2)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """INSERT INTO user_metrics 
                   (user_id, height, weight, bmi, dietary_preference, fitness_goal, allergies, activity_level)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (current_user_id, height, weight, bmi, dietary_preference, fitness_goal, allergies, activity_level))
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

        if rec_type != "meal":
            return jsonify({'message': 'Exercise recommendations not implemented yet'}), 200

        # ==============================
        # LOAD DATASETS
        # ==============================
        base_dir = os.path.dirname(os.path.abspath(__file__))
        diet_path = os.path.join(base_dir, "Dataset.csv")
        food_path = os.path.join(base_dir, "Food and Calories - Sheet1.csv")

        print(f"📂 Loading datasets from:\n  {diet_path}\n  {food_path}")
        if not os.path.exists(diet_path) or not os.path.exists(food_path):
            print("❌ One or both dataset files are missing!")
            return jsonify({
                'message': 'Dataset files not found. Please verify Dataset.csv and Food and Calories - Sheet1.csv exist in backend folder.'
            }), 500

        diet_df = pd.read_csv(diet_path)
        food_df = pd.read_csv(food_path)
        print("✅ Datasets loaded successfully!")

        # ==============================
        # CLEAN & NORMALIZE DIET DATA
        # ==============================
        diet_df.columns = [c.strip().lower() for c in diet_df.columns]
        diet_df = diet_df.rename(columns={
            "weight(kg)": "weight_kg",
            "height(m)": "height_m",
            "bmi_tags": "bmi_tag",
            "calories_to_maintain_weight": "maintain_calories"
        }, errors="ignore")

        # enforce types used in matching
        if "bmi_tag" in diet_df.columns:
            diet_df["bmi_tag"] = pd.to_numeric(diet_df["bmi_tag"], errors="coerce")
        if "gender" in diet_df.columns:
            diet_df["gender"] = diet_df["gender"].astype(str)

        # ==============================
        # FETCH USER DETAILS
        # ==============================
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (current_user_id,))
        user = cursor.fetchone()

        cursor.execute("""
            SELECT * FROM user_metrics 
            WHERE user_id = %s 
            ORDER BY created_at DESC LIMIT 1
        """, (current_user_id,))
        metrics = cursor.fetchone()
        cursor.close()
        conn.close()

        if not metrics:
            return jsonify({'message': 'No user metrics found. Please update your height, weight, and preferences first.'}), 400

        # ==============================
        # EXTRACT VALUES
        # ==============================
        gender = str(user['gender'])[0].upper()
        height_m = float(metrics['height']) / 100.0  # cm -> m
        weight_kg = float(metrics['weight'])
        diet_pref = str(metrics['dietary_preference']).lower()
        goal = (str(metrics['fitness_goal']).title() if metrics['fitness_goal'] else "Maintenance")
        activity_level = float(metrics.get('activity_level', 1.5))  # default moderate
        user_allergies = [a.strip().lower() for a in str(metrics.get('allergies', '')).split(',') if a.strip()]

        # ==============================
        # CALCULATE BMI & MAP TO NUMERIC TAG
        # ==============================
        bmi = weight_kg / (height_m ** 2)

        # Map: 7=Underweight, 8=Normal, 9=Overweight, 10=Obese
        if bmi < 18.5:
            bmi_tag_text, bmi_tag_num = "Underweight", 7
        elif 18.5 <= bmi < 25:
            bmi_tag_text, bmi_tag_num = "Normal", 8
        elif 25 <= bmi < 30:
            bmi_tag_text, bmi_tag_num = "Overweight", 9
        else:
            bmi_tag_text, bmi_tag_num = "Obese", 10

        # ==============================
        # CALCULATE CALORIE TARGET
        # ==============================
        match = diet_df[
            (diet_df.get("bmi_tag") == bmi_tag_num) &
            (diet_df.get("gender").str.upper() == gender.upper())
        ]

        if not match.empty and "maintain_calories" in match.columns:
            avg_maintain = match["maintain_calories"].mean()
        elif "calories_to_maintain_weight" in diet_df.columns:
            # fallback if file wasn't renamed as expected
            avg_maintain = diet_df.loc[
                (diet_df.get("bmi_tag") == bmi_tag_num) &
                (diet_df.get("gender").str.upper() == gender.upper()),
                "calories_to_maintain_weight"
            ].mean()
        else:
            avg_maintain = 2000.0  # safe fallback

        target_calories = avg_maintain * (activity_level / 1.5)
        if goal == "Weight Loss":
            target_calories *= 0.85
        elif goal == "Weight Gain" or "Muscle" in goal:
            target_calories *= 1.15

        # ==============================
        # CLEAN & FILTER FOOD DATA
        # ==============================
        food_df.columns = [c.strip().lower() for c in food_df.columns]
        # normalize to Title/Capital keys used later
        food_df = food_df.rename(columns={"food": "Food", "calories": "Calories"}, errors="ignore")
        food_df["Calories"] = food_df["Calories"].astype(str).str.extract(r"(\d+\.?\d*)").astype(float)
        food_df = food_df.dropna(subset=["Calories"])
        food_df = food_df[(food_df["Calories"] > 0) & (food_df["Calories"] < 1000)]

        # Diet preference filters
        non_veg_keywords = ["chicken", "fish", "egg", "beef", "pork", "mutton", "shrimp", "bacon", "ham", "sausage", "tuna"]
        dairy_keywords = ["milk", "paneer", "cheese", "butter", "ghee", "curd", "yogurt"]

        def is_non_veg(name): return any(k in str(name).lower() for k in non_veg_keywords)
        def has_dairy(name): return any(k in str(name).lower() for k in dairy_keywords)

        if diet_pref == "vegetarian":
            food_df = food_df[~food_df["Food"].apply(is_non_veg)]
        elif diet_pref == "vegan":
            food_df = food_df[~food_df["Food"].apply(is_non_veg)]
            food_df = food_df[~food_df["Food"].apply(has_dairy)]

        # Allergy filters (enhanced)
        allergy_aliases = {
            'nuts': ['nut', 'almond', 'cashew', 'peanut', 'walnut', 'hazelnut'],
            'dairy': ['milk', 'cheese', 'butter', 'cream', 'paneer', 'yogurt', 'curd'],
            'eggs': ['egg', 'omelet'],
            'gluten': ['wheat', 'bread', 'flour', 'pasta'],
            'soy': ['soy', 'tofu', 'soya'],
            'seafood': ['fish', 'shrimp', 'prawn', 'crab', 'lobster', 'tuna', 'salmon']
        }

        def contains_allergen(food_name, allergies):
            name = str(food_name).lower()
            return any(
                any(alias in name for alias in allergy_aliases.get(a, []))
                for a in allergies
            )

        if user_allergies:
            before = len(food_df)
            food_df = food_df[~food_df["Food"].apply(lambda x: contains_allergen(x, user_allergies))]
            print(f"⚠️ Filtered {before - len(food_df)} foods due to allergies: {user_allergies}")

        # ==============================
        # SELECT TOP FOODS BY GOAL
        # ==============================
        if goal == "Weight Loss":
            top_foods = food_df.sort_values(by="Calories", ascending=True).head(10)
        elif goal == "Weight Gain" or "Muscle" in goal:
            top_foods = food_df.sort_values(by="Calories", ascending=False).head(10)
        else:
            top_foods = food_df.sample(min(10, len(food_df)), random_state=42)

        # ==============================
        # PREPARE RESPONSE
        # ==============================
        meals = []
        for _, row in top_foods.iterrows():
            meals.append({
                "name": str(row.get("Food", "")).title(),
                "calories": float(round(row.get("Calories", 0.0), 1)),
                "serving": row.get("serving", "per serving")
            })

        # helpful debug
        print(f"✅ BMI={bmi:.2f} ({bmi_tag_text}/{bmi_tag_num}), activity={activity_level}, goal={goal}, diet={diet_pref}, allergies={user_allergies}")
        print(f"✅ Target calories: {round(target_calories)} kcal")

        return jsonify({
            "bmi": round(bmi, 2),
            "bmi_tag": bmi_tag_text,
            "goal": goal,
            "target_calories": round(target_calories, 0),
            "meals": meals
        }), 200

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