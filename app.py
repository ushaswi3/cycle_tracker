from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import sqlite3
from collections import Counter
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# --- Database setup ---
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            start_date TEXT,
            cycle_length INTEGER,
            period_duration INTEGER,
            mood TEXT,
            symptoms TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

# --- Routes ---
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username already exists. Please go back and choose another."
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials. Please try again."
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        start_date = request.form['start_date']
        cycle_length = int(request.form['cycle_length'])
        period_duration = int(request.form['period_duration'])
        mood = request.form.get('mood', '')
        symptoms = request.form.get('symptoms', '')

        user_id = session['user_id']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO cycles (user_id, start_date, cycle_length, period_duration, mood, symptoms) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, start_date, cycle_length, period_duration, mood, symptoms))
        conn.commit()
        conn.close()

        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        next_period_start = start_date_obj + timedelta(days=cycle_length)
        ovulation_day = start_date_obj + timedelta(days=cycle_length - 14)

        events = []

        for i in range(period_duration):
            events.append({
                'title': 'Actual Period',
                'start': (start_date_obj + timedelta(days=i)).strftime('%Y-%m-%d'),
                'color': '#ff0000'
            })

        for i in range(period_duration):
            events.append({
                'title': 'Predicted Period',
                'start': (next_period_start + timedelta(days=i)).strftime('%Y-%m-%d'),
                'color': '#ffd6e0'
            })

        events.append({
            'title': 'Ovulation',
            'start': ovulation_day.strftime('%Y-%m-%d'),
            'color': '#a8dadc'
        })

        symptom_remedies = {
            'cramps': 'Apply a heating pad, drink herbal tea, or try gentle yoga.',
            'headache': 'Rest, hydrate well, and try a cold compress.',
            'fatigue': 'Get extra sleep and eat iron-rich foods like spinach.',
            'bloating': 'Avoid salty foods, drink water, and try light walking.',
            'mood swings': 'Practice mindfulness, listen to calming music, and talk to a friend.',
            'backpain': 'Use a warm compress, maintain good posture, and try gentle stretches.',
            'legpain': 'Massage the legs, stay hydrated, elevate your legs, and rest.',
            'hot flashes': 'Stay cool, wear breathable clothing, avoid caffeine and spicy foods.',
            'cravings': 'Opt for healthy alternatives like dark chocolate, fruits, and nuts. Stay hydrated to reduce cravings.'
        }

        remedies = []
        if symptoms:
            for sym in symptoms.split(','):
                s = sym.strip().lower()
                if s in symptom_remedies:
                    remedies.append((s.capitalize(), symptom_remedies[s]))

        return render_template('result.html',
                               next_period=next_period_start.date(),
                               ovulation=ovulation_day.date(),
                               events=events,
                               remedies=remedies)

    return render_template('dashboard.html')

@app.route('/calendar')
def calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT start_date, cycle_length, period_duration, symptoms FROM cycles WHERE user_id=? ORDER BY start_date", (session['user_id'],))
    data = cursor.fetchall()
    conn.close()

    events = []

    # Remedies dictionary
    symptom_remedies = {
        'cramps': 'Apply a heating pad, drink herbal tea, or try gentle yoga.',
        'headache': 'Rest, hydrate well, and try a cold compress.',
        'fatigue': 'Get extra sleep and eat iron-rich foods like spinach.',
        'bloating': 'Avoid salty foods, drink water, and try light walking.',
        'mood swings': 'Practice mindfulness, listen to calming music, and talk to a friend.',
        'backpain': 'Use a warm compress, maintain good posture, and try gentle stretches.',
        'legpain': 'Massage the legs, stay hydrated, elevate your legs, and rest.',
        'hot flashes': 'Stay cool, wear breathable clothing, avoid caffeine and spicy foods.',
        'cravings': 'Opt for healthy alternatives like dark chocolate, fruits, and nuts. Stay hydrated to reduce cravings.'
    }

    for entry in data:
        start_date = datetime.strptime(entry[0], "%Y-%m-%d")
        cycle_length = entry[1]
        period_duration = entry[2]
        symptoms = entry[3]

        # Actual period dates - red color
        for i in range(period_duration):
            events.append({
                'title': 'Actual Period',
                'start': (start_date + timedelta(days=i)).strftime('%Y-%m-%d'),
                'color': '#ff4d4d'  # Red for actual period
            })

        # Predicted next period - soft pink
        predicted_start = start_date + timedelta(days=cycle_length)
        for i in range(period_duration):
            events.append({
                'title': 'Predicted',
                'start': (predicted_start + timedelta(days=i)).strftime('%Y-%m-%d'),
                'color': '#ffd6e0'
            })

        # Ovulation date - soft teal
        ovulation_date = start_date + timedelta(days=(cycle_length - 14))
        events.append({
            'title': 'Ovulation',
            'start': ovulation_date.strftime('%Y-%m-%d'),
            'color': '#a8dadc'
        })

        # Symptom events with remedies
        if symptoms:
            for sym in symptoms.split(','):
                sym = sym.strip().lower()
                if sym in symptom_remedies:
                    events.append({
                        'title': sym.capitalize(),
                        'start': start_date.strftime('%Y-%m-%d'),
                        'color': '#ffe0ac',
                        'extendedProps': {
                            'remedy': symptom_remedies[sym]
                        }
                    })

    return render_template('calendar.html', events=events)

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT start_date, cycle_length, mood, symptoms FROM cycles WHERE user_id=?", (session['user_id'],))
    data = cursor.fetchall()
    conn.close()

    dates = [row[0] for row in data]
    lengths = [row[1] for row in data]
    moods = [row[2] for row in data]
    symptoms = [row[3] for row in data]

    symptom_list = []
    for s in symptoms:
        if s:
            symptom_list.extend([sym.strip().lower() for sym in s.split(',')])
    symptom_counts = dict(Counter(symptom_list))
    mood_counts = dict(Counter([m.lower() for m in moods if m]))

    return render_template('analytics.html',
                           dates=dates,
                           lengths=lengths,
                           symptom_counts=symptom_counts,
                           mood_counts=mood_counts)

@app.route('/mark_period', methods=['GET', 'POST'])
def mark_period():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        actual_start_date = request.form['actual_start_date']
        cycle_length = int(request.form['cycle_length'])
        period_duration = int(request.form['period_duration'])
        mood = request.form.get('mood', '')
        symptoms = request.form.get('symptoms', '')

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO cycles (user_id, start_date, cycle_length, period_duration, mood, symptoms) VALUES (?, ?, ?, ?, ?, ?)",
                       (session['user_id'], actual_start_date, cycle_length, period_duration, mood, symptoms))
        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    return render_template('mark_period.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists('users.db'):
        init_db()
    app.run(debug=True)
