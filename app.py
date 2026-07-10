# ============================================
# Project 5: Smart Expense Tracker
# ============================================

from flask import Flask, render_template, request, jsonify
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'Khizar@Dev2024'

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root1234',
    'database': 'khizar_portfolio'
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        print("Database initialized.")

@app.route('/')
def index():
    return render_template('index.html', categories=CATEGORIES)

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    conn = get_db()
    if not conn:
        return jsonify([])
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM expenses ORDER BY date DESC LIMIT 50")
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
        INSERT INTO expenses (title, amount, category, type, date, note)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (data['title'], data['amount'], data['category'], 
          data['type'], data['date'], data.get('note', '')))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/transactions/<int:id>', methods=['DELETE'])
def delete_transaction(id):
    conn = get_db()
    if not conn:
        return jsonify({'error': 'DB connection failed'})
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/summary', methods=['GET'])
def get_summary():
    conn = get_db()
    if not conn:
        return jsonify({})
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT SUM(amount) as total FROM expenses WHERE type='income'")
    income = cursor.fetchone()['total'] or 0
    cursor.execute("SELECT SUM(amount) as total FROM expenses WHERE type='expense'")
    expense = cursor.fetchone()['total'] or 0
    cursor.execute("""
        SELECT category, SUM(amount) as total 
        FROM expenses WHERE type='expense' 
        GROUP BY category ORDER BY total DESC
    """)
    by_category = cursor.fetchall()
    cursor.execute("""
        SELECT DATE_FORMAT(date, '%Y-%m') as month, 
               SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as income,
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expense
        FROM expenses GROUP BY month ORDER BY month
    """)
    monthly = cursor.fetchall()
    conn.close()
    return jsonify({
        'total_income': income,
        'total_expense': expense,
        'balance': income - expense,
        'by_category': by_category,
        'monthly': monthly
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True)