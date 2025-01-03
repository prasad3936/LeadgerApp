from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import signal
import threading
import webview
app = Flask(__name__)

# Configuration for SQLite Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///customer_db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'credit' or 'debit'
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    products = db.Column(db.String(255), nullable=False)
    transactions = db.relationship('Transaction', cascade="all, delete-orphan", backref='customer')

@app.route('/')
def index():
    customers = Customer.query.all()
    total_amount = db.session.query(db.func.sum(Customer.amount)).scalar() or 0
    return render_template('index.html', customers=customers, total_amount=total_amount)

@app.route('/add', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        amount = request.form['amount']
        products = request.form['products']

        new_customer = Customer(name=name, mobile=mobile, amount=amount, products=products)
        db.session.add(new_customer)
        db.session.commit()

        return redirect(url_for('index'))
    return render_template('add_customer.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.mobile = request.form['mobile']
        customer.amount = request.form['amount']
        customer.products = request.form['products']

        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_customer.html', customer=customer)

@app.route('/delete/<int:id>')
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/transaction/<int:id>/<string:action>', methods=['POST'])
def transaction(id, action):
    customer = Customer.query.get_or_404(id)
    amount = float(request.form['amount'])
    
    if action == 'credit':
        customer.amount += amount
        transaction = Transaction(customer_id=id, type='credit', amount=amount)
    elif action == 'debit':
        if customer.amount >= amount:
            customer.amount -= amount
            transaction = Transaction(customer_id=id, type='debit', amount=amount)
        else:
            # Render an error page for insufficient balance
            error_message = "Insufficient balance. Please check your account and try again."
            return render_template('error.html', error_message=error_message), 400
    
    # Add and commit the transaction
    db.session.add(transaction)
    db.session.commit()
    
    # Redirect to the index page after successful operation
    return redirect(url_for('index'))


@app.route('/print_invoice/<int:id>')
def print_invoice(id):
    customer = Customer.query.get_or_404(id)
    transactions = Transaction.query.filter_by(customer_id=id).order_by(Transaction.date.desc()).all()
    current_datetime = datetime.utcnow()
    return render_template('invoice.html', customer=customer, transactions=transactions, current_datetime=current_datetime)

import webview

@app.route('/shutdown', methods=['POST'])
def shutdown():
    try:
        webview.destroy_window()  # Use destroy_window instead of close
        return "Shutting down", 200
    except Exception as e:
        app.logger.error(f"Error shutting down: {e}")
        return "Error shutting down", 500

# Function to run Flask in a separate thread
def run_flask():
    app.run(debug=False, use_reloader=False)


if __name__ == '__main__':
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Launch PyWebView
    webview.create_window('Ledger - A Customer Management App', 'http://127.0.0.1:5000', width=800, height=600)
    webview.start()
