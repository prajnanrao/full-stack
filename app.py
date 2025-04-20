from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from flask_login import LoginManager, login_user, login_required, UserMixin, logout_user, current_user
from flask import jsonify
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

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

@app.route('/getRestaurant', methods=['GET'])
def get_restaurant():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Restaurants")
        rows = cur.fetchall()
        cur.close()

        # Convert to list of dictionaries
        restaurants = []
        for row in rows:
            restaurant = {
                'restaurant_id': row[0],
                'name': row[1],
                'description': row[2],
                'cuisine_type': row[3],
                'address': row[4],
                'city': row[5],
                'state': row[6],
                'Pin_code': row[7],
                'phone': row[8],
                'rating': float(row[9]),
                'is_active': bool(row[10])
            }
            restaurants.append(restaurant)

        return jsonify(restaurants)

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/addRestaurant', methods=['POST'])
def add_restaurant():
    try:
        data = request.json  # Get JSON data from the request
        name = data.get('name')
        address = data.get('address')
        phone = data.get('phone')
        cuisine_type = data.get('cuisine_type')
        rating = data.get('rating')
        city = data.get('city')
        state = data.get('state')
        pin_code = data.get('pin_code')
        description = data.get('description')

        # Generate a unique restaurant_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT MAX(restaurant_id) FROM Restaurants")
        max_id = cur.fetchone()[0]
        restaurant_id = (max_id + 1) if max_id else 1

        # Insert restaurant details into the database
        cur.execute("""
            INSERT INTO Restaurants (restaurant_id, name, description, cuisine_type, address, city, state, Pin_code, phone, rating, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (restaurant_id, name, description, cuisine_type, address, city, state, pin_code, phone, rating, True))
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Restaurant added successfully!'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/updateRestaurant', methods=['PUT'])
def update_restaurant():
    try:
        data = request.json
        restaurant_id = data.get('restaurant_id')
        name = data.get('name')
        address = data.get('address')
        phone = data.get('phone')
        cuisine_type = data.get('cuisine_type')
        rating = data.get('rating')
        city = data.get('city')
        state = data.get('state')
        pin_code = data.get('pin_code')
        description = data.get('description')

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE Restaurants
            SET name = %s, description = %s, cuisine_type = %s, address = %s, city = %s, state = %s, Pin_code = %s, phone = %s, rating = %s
            WHERE restaurant_id = %s
        """, (name, description, cuisine_type, address, city, state, pin_code, phone, rating, restaurant_id))
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Restaurant updated successfully!'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/deleteRestaurant', methods=['DELETE'])
def delete_restaurant():
    try:
        data = request.json
        restaurant_id = data.get('restaurant_id')

        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM Restaurants WHERE restaurant_id = %s", (restaurant_id,))
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Restaurant deleted successfully!'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

# Add menu item
@app.route('/admin/restaurant/<int:restaurant_id>/menu/add', methods=['POST'])
def add_menu_item(restaurant_id):
    try:
        data = request.get_json()  # Use get_json() to parse JSON data from the request
        item_name = data.get('item_name')
        description = data.get('description')
        price = data.get('price')
        category = data.get('category')
        is_available = data.get('is_available', True)  # Default to True if not provided
        preparation_time = data.get('preparation_time')

        if not item_name or not price or not category:
            return jsonify({'error': 'Missing required fields: item_name, price, or category'}), 400

        cur = mysql.connection.cursor()
        cur.execute("SELECT MAX(menu_id) FROM Menu")
        max_id = cur.fetchone()[0]
        menu_id = (max_id + 1) if max_id else 1
        logging.info(f"Generated menu_id: {description}")
        cur.execute("""
            INSERT INTO Menu (menu_id, restaurant_id, item_name, description, price, category, is_available, preparation_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (menu_id, restaurant_id, item_name, description, price, category, is_available, preparation_time))
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Menu item added successfully!'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# View menu items
@app.route('/admin/restaurant/<int:restaurant_id>/menu')
def view_menu_items(restaurant_id):
    cursor = mysql.connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Menu WHERE restaurant_id = %s", (restaurant_id,))
    menu_items = cursor.fetchall()
    return render_template('view_menu.html', menu_items=menu_items, restaurant_id=restaurant_id)

# Edit menu item
@app.route('/admin/menu/<int:menu_id>/edit', methods=['GET', 'POST'])
def edit_menu_item(menu_id):
    cursor = mysql.connection.cursor(dictionary=True)
    if request.method == 'POST':
        item_name = request.form['item_name']
        description = request.form['description']
        price = request.form['price']
        category = request.form['category']
        is_available = 'is_available' in request.form
        prep_time = request.form['preparation_time']

        cursor.execute("""
            UPDATE Menu SET item_name=%s, description=%s, price=%s, category=%s,
            is_available=%s, preparation_time=%s WHERE menu_id=%s
        """, (item_name, description, price, category, is_available, prep_time, menu_id))
        mysql.connection.commit()
        return redirect('/admin/restaurants')  # Or back to menu list

    cursor.execute("SELECT * FROM Menu WHERE menu_id = %s", (menu_id,))
    menu_item = cursor.fetchone()
    return render_template('edit_menu_item.html', menu_item=menu_item)

# Delete menu item
@app.route('/admin/menu/<int:menu_id>/delete')
def delete_menu_item(menu_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM Menu WHERE menu_id = %s", (menu_id,))
    mysql.connection.commit()
    return redirect('/admin/restaurants')

@app.route('/getRestaurantsWithMenus', methods=['GET'])
def get_restaurants_with_menus():
    try:
        cur = mysql.connection.cursor()

        # Fetch all restaurants
        cur.execute("SELECT * FROM Restaurants")
        restaurants = cur.fetchall()

        result = []

        for restaurant in restaurants:
            restaurant_id = restaurant[0]
            name = restaurant[1]

            # Fetch menus for the restaurant
            cur.execute("SELECT category, item_name, price FROM Menu WHERE restaurant_id = %s", (restaurant_id,))
            menu_items = cur.fetchall()

            # Group menu items by category
            menu_dict = {}
            for item in menu_items:
                category = item[0]
                if category not in menu_dict:
                    menu_dict[category] = []
                menu_dict[category].append({
                    'item_name': item[1],
                    'price': float(item[2])
                })

            # Convert menu_dict to a list of categories with items
            menus = [{'category': category, 'items': items} for category, items in menu_dict.items()]

            result.append({
                'name': name,
                'menus': menus
            })

        cur.close()
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/getMenuDetails', methods=['GET'])
def get_menu_details():
    try:
        cur = mysql.connection.cursor()

        # Fetch all menu items
        cur.execute("SELECT * FROM Menu")
        menu_items = cur.fetchall()

        result = []

        for item in menu_items:
            menu_item = {
                'menu_id': item[0],
                'restaurant_id': item[1],
                'item_name': item[2],
                'description': item[3],
                'price': float(item[4]),
                'category': item[5],
                'is_available': bool(item[6]),
                'preparation_time': item[7]
            }
            result.append(menu_item)

        cur.close()
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/updateMenu', methods=['PUT'])
def update_menu():
    try:
        data = request.json
        menu_id = data.get('menu_id')
        item_name = data.get('item_name')
        description = data.get('description')
        price = data.get('price')
        category = data.get('category')
        is_available = data.get('is_available', True)
        preparation_time = data.get('preparation_time')

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE Menu
            SET item_name = %s, description = %s, price = %s, category = %s, is_available = %s, preparation_time = %s
            WHERE menu_id = %s
        """, (item_name, description, price, category, is_available, preparation_time, menu_id))
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Menu item updated successfully!'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/deleteMenu', methods=['DELETE'])
def delete_menu():
    try:
        data = request.json
        menu_id = data.get('menu_id')

        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM Menu WHERE menu_id = %s", (menu_id,))
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Menu item deleted successfully!'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
