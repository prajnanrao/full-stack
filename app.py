from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from flask_login import LoginManager, login_user, login_required, UserMixin, logout_user, current_user

app = Flask(__name__)

# Database configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # Replace with your password
app.config['MYSQL_DB'] = 'Foodhub'
mysql = MySQL(app)

# Secret key for session management
app.secret_key = 'your_secret_key'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)

# Dummy User class
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Example: Check for admin credentials
        if username == 'admin' and password == 'adminpassword':
            user = User(1)  # Create a user object
            login_user(user)
            return redirect(url_for('index'))
        else:
            return "Invalid credentials", 403
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/place-order')
def placeOrder():
    return render_template('place-order.html')

@app.route('/track-order')
def trackOrder():
    return render_template('track-order.html')

@app.route('/review')
def review():
    return render_template('review.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/manage-restaurants', methods=['GET', 'POST'])
@login_required  # Ensure only logged-in users can access this route
def manage_restaurants():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO restaurants(name, address) VALUES(%s, %s)", (name, address))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('manage_restaurants'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM restaurants")
    restaurants = cur.fetchall()
    cur.close()
    return render_template('manage_restaurants.html', restaurants=restaurants)

@app.route('/manage-orders', methods=['GET'])
@login_required  # Ensure only logged-in users can access this route
def manage_orders():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM orders")
    orders = cur.fetchall()
    cur.close()
    return render_template('manage_orders.html', orders=orders)

@app.route('/track-order/<int:order_id>', methods=['GET'])
@login_required  # Ensure only logged-in users can access this route
def track_order_details(order_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cur.fetchone()
    cur.close()
    
    if order:
        return render_template('track_order.html', order=order)
    else:
        return "Order not found", 404

@app.route('/update-order-status', methods=['POST'])
@login_required  # Ensure only logged-in users can access this route
def update_order_status():
    order_id = request.form['order_id']
    status = request.form['status']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE order_id = %s", (status, order_id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('manage_orders'))

@app.route('/submit-review', methods=['POST'])
@login_required  # Ensure only logged-in users can access this route
def submit_review():
    restaurant = request.form['restaurant']
    rating = request.form['rating']
    review = request.form['review']
    
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO reviews(restaurant, rating, review) VALUES(%s, %s, %s)", (restaurant, rating, review))
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
