#Tracker EXPENSE TRACKER

from flask import Flask, render_template, request, jsonify, session, redirect
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
import urllib.parse
import uuid

app = Flask(__name__)
app.secret_key = 'Khizar@Dev2024'

# ---- Set your admin password here ----
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Khizar@Admin2024')

mysql_url = os.environ.get('MYSQL_URL') or os.environ.get('MYSQL_PUBLIC_URL')

if mysql_url:
    parsed = urllib.parse.urlparse(mysql_url)
    DB_CONFIG = {
        'host': parsed.hostname,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path[1:],
        'port': parsed.port or 3306
    }
else:
    DB_CONFIG = {
        'host': os.environ.get('MYSQLHOST', 'localhost'),
        'user': os.environ.get('MYSQLUSER', 'root'),
        'password': os.environ.get('MYSQLPASSWORD', 'root1234'),
        'database': os.environ.get('MYSQLDATABASE', 'khizar_portfolio'),
        'port': int(os.environ.get('MYSQLPORT', 3306))
    }

CATEGORIES = ['Food', 'Transport', 'Shopping', 'Entertainment', 'Health', 'Education', 'Bills', 'Other']

def get_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"DB Error: {e}")
        return None

def init_db():
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255),
                amount FLOAT,
                category VARCHAR(100),
                type ENUM('income', 'expense'),
                date DATE,
                note TEXT,
                session_id VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        print("Database initialized.")

@app.before_request
def assign_session():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

@app.route('/')
def index():
    return render_template('index.html', categories=CATEGORIES)

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    conn = get_db()
    if not conn:
        return jsonify([])
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM expenses WHERE session_id = %s ORDER BY date DESC", (session.get('user_id'),))
    transactions = cursor.fetchall()
    conn.close()
    for t in transactions:
        t['date'] = str(t['date'])
        t['created_at'] = str(t['created_at'])
    return jsonify(transactions)

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    data = request.json
    conn = get_db()
    if not conn:
        return jsonify({'error': 'DB connection failed'})
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expenses (title, amount, category, type, date, note, session_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        data.get('title'),
        data.get('amount'),
        data.get('category'),
        data.get('type'),
        data.get('date'),
        data.get('note', ''),
        session['user_id']
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/transactions/<int:id>', methods=['DELETE'])
def delete_transaction(id):
    conn = get_db()
    if not conn:
        return jsonify({'error': 'DB connection failed'})
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = %s AND session_id = %s", (id, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ============== ADMIN ROUTES ==============

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect('/admin')
        else:
            return render_template('admin_login.html', error='Wrong password')

    if not session.get('is_admin'):
        return render_template('admin_login.html', error=None)

    return render_template('admin.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect('/')

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    if not conn:
        return jsonify({'error': 'DB connection failed'})

    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total_transactions FROM expenses")
    total_transactions = cursor.fetchone()['total_transactions']

    cursor.execute("SELECT COUNT(DISTINCT session_id) as total_users FROM expenses")
    total_users = cursor.fetchone()['total_users']

    cursor.execute("SELECT SUM(amount) as total_income FROM expenses WHERE type = 'income'")
    result_inc = cursor.fetchone()
    total_income = result_inc['total_income'] or 0

    cursor.execute("SELECT SUM(amount) as total_expense FROM expenses WHERE type = 'expense'")
    result_exp = cursor.fetchone()
    total_expense = result_exp['total_expense'] or 0

    conn.close()

    return jsonify({
        'total_transactions': total_transactions,
        'total_users': total_users,
        'total_income': float(total_income),
        'total_expense': float(total_expense)
    })

@app.route('/api/admin/transactions', methods=['GET'])
def admin_get_all_transactions():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    if not conn:
        return jsonify([])

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM expenses ORDER BY created_at DESC")
    transactions = cursor.fetchall()
    conn.close()

    for t in transactions:
        t['date'] = str(t['date'])
        t['created_at'] = str(t['created_at'])
    return jsonify(transactions)

@app.route('/api/admin/transactions/<int:id>', methods=['DELETE'])
def admin_delete_transaction(id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    if not conn:
        return jsonify({'error': 'DB connection failed'})
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
