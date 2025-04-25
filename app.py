from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask_login import LoginManager, login_user, login_required, UserMixin, logout_user, current_user
from flask import jsonify
import logging
# For password hashing
from werkzeug.security import generate_password_hash, check_password_hash
import functools  # For admin_required decorator
from MySQLdb.cursors import DictCursor  # Import DictCursor

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# Database configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Prajna@9623'  # Replace with your password
app.config['MYSQL_DB'] = 'Foodhub'
mysql = MySQL(app)

# Secret key for session management
app.secret_key = 'your_secret_key'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to /login if @login_required fails
login_manager.login_message_category = 'info'  # Flash message category

# --- Enhanced User Class ---


class User(UserMixin):
    def __init__(self, id, email, name, is_admin, address=None, phone=None):
        self.id = id
        self.email = email  # Using email as username essentially
        self.name = name
        self.is_admin = is_admin
        self.address = address
        self.phone = phone

    # Add other properties you might need from the Customers table

# --- Updated User Loader ---


@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT customer_id, email, Full_name, is_admin, phone, address FROM Customers WHERE customer_id = %s", (int(user_id),))
    user_data = cur.fetchone()
    cur.close()
    if user_data:
        # User data is tuple: (id, email, name, is_admin_flag, phone, address)
        is_admin_bool = bool(user_data[3])  # Convert DB value (0/1) to boolean
        return User(id=user_data[0], email=user_data[1], name=user_data[2],
                    is_admin=is_admin_bool, phone=user_data[4], address=user_data[5])
    return None

# --- Admin Required Decorator ---


def admin_required(func):
    @functools.wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not current_user.is_admin:
            flash('Admin access required.', 'warning')
            # Or wherever non-admins should go
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return decorated_view


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
@login_required
@admin_required
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
@login_required
@admin_required
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
@login_required
@admin_required
def delete_restaurant():
    try:
        data = request.json
        restaurant_id = data.get('restaurant_id')

        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID is required.'}), 400

        cur = mysql.connection.cursor()
        # Soft delete: Update is_active to FALSE instead of deleting
        cur.execute(
            "UPDATE Restaurants SET is_active = FALSE WHERE restaurant_id = %s", (restaurant_id,))
        # Note: This doesn't automatically deactivate associated menu items.
        # You might want to add logic here or elsewhere to also set is_available=FALSE
        # for menu items belonging to this restaurant if that's the desired behavior.
        mysql.connection.commit()
        affected_rows = cur.rowcount
        cur.close()

        if affected_rows > 0:
            flash(f'Restaurant {restaurant_id} marked as inactive.', 'success')
            logging.info(
                f"Admin {current_user.id} deactivated restaurant {restaurant_id}")
            return jsonify({'message': 'Restaurant marked as inactive successfully!'}), 200
        else:
            return jsonify({'error': 'Restaurant not found or already inactive.'}), 404

    except Exception as e:
        # Log the specific foreign key error if possible
        if "1451" in str(e):
            logging.error(
                f"Foreign key constraint error trying to deactivate restaurant {restaurant_id}: {e}")
            # Even with soft delete, constraints on related tables could potentially cause issues
            # if not handled (though less likely than with hard delete).
            # Conflict
            return jsonify({'error': 'Cannot deactivate restaurant due to related data. Please check associated menus or orders.'}), 409
        else:
            logging.error(
                f"Error deactivating restaurant {restaurant_id}: {e}")
            mysql.connection.rollback()  # Rollback on general error
            return jsonify({'error': str(e)}), 500
    finally:
        # Ensure cursor is closed in case of exception before close() was reached
        try:
            if cur and not cur.closed:
                cur.close()
        except:
            pass


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))  # Already logged in

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = True if request.form.get('remember') else False

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT customer_id, email, Full_name, password_hash, is_admin FROM Customers WHERE email = %s", (email,))
        user_data = cur.fetchone()
        cur.close()

        if user_data:
            stored_hash = user_data[3]
            if check_password_hash(stored_hash, password):
                is_admin_bool = bool(user_data[4])
                user_obj = User(
                    id=user_data[0], email=user_data[1], name=user_data[2], is_admin=is_admin_bool)
                login_user(user_obj, remember=remember)

                # Redirect admin to admin page, others to index
                # For redirecting after required login
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                if user_obj.is_admin:
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('Login failed. Check email and password.', 'danger')
        else:
            flash('Login failed. User does not exist.', 'danger')

    return render_template('login.html')  # Render login form for GET requests


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
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
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)  # Use DictCursor
        # Fetch reviews joined with customer names and restaurant names
        cur.execute("""
            SELECT r.review_id, r.rating, r.comment, c.Full_name as customer_name, rest.name as restaurant_name
            FROM Reviews r
            JOIN Customers c ON r.customer_id = c.customer_id
            JOIN Restaurants rest ON r.restaurant_id = rest.restaurant_id
            ORDER BY r.review_id DESC -- Or some other ordering
        """)
        reviews = cur.fetchall()
        cur.close()
    except Exception as e:
        logging.error(f"Error fetching reviews: {e}")
        flash('Could not load reviews.', 'warning')
        reviews = []  # Ensure reviews is an empty list on error

    return render_template('review.html', reviews=reviews)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))  # Already logged in

    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']  # Assuming 'name' corresponds to Full_name
        password = request.form['password']
        # Add other fields as needed (phone, address etc. from your form)
        # Get phone number, use .get for safety
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        pin_code = request.form.get('pin_code')

        # Basic validation (add more robust validation)
        if not email or not name or not password or not phone or not address or not city or not state or not pin_code:  # Added address fields validation
            flash('All fields are required!', 'danger')
            return redirect(url_for('register'))

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT customer_id FROM Customers WHERE email = %s", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            flash('Email address already registered.', 'warning')
            cur.close()
            return redirect(url_for('register'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Insert new user (as non-admin by default)
        # Adjust INSERT statement based on the fields you collect
        try:
            # --- START: Manually generate next customer_id ---
            cur.execute("SELECT MAX(customer_id) FROM Customers")
            max_id_result = cur.fetchone()
            # Handle empty table or NULL result
            max_id = max_id_result[0] if max_id_result and max_id_result[0] is not None else 0
            next_customer_id = max_id + 1
            logging.info(
                f"Manually generating next customer_id: {next_customer_id}")
            # --- END: Manually generate next customer_id ---

            # Updated INSERT to include the generated customer_id and all required fields
            cur.execute("INSERT INTO Customers (customer_id, Full_name, email, password_hash, phone, address, city, state, Pin_code) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (next_customer_id, name, email, hashed_password, phone, address, city, state, pin_code))
            mysql.connection.commit()
            flash('Registration successful! Please log in.', 'success')
            cur.close()
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()  # Rollback in case of error
            flash(f'An error occurred: {e}', 'danger')
            logging.error(f"Registration error: {e}")
            cur.close()
            return redirect(url_for('register'))

    # Render registration form for GET requests
    return render_template('register.html')


@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin():
    orders = []
    order_to_track = None
    reviews = []  # Initialize reviews list
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        # Fetch orders
        cur.execute("""
            SELECT 
                o.order_id, o.customer_id, o.restaurant_id, o.supplier_id, 
                o.order_status, o.order_placed_time, o.preparation_complete_time, 
                o.dispatch_time, o.delivery_time, o.total_price, o.delivery_address,
                c.Full_name as customer_name, 
                r.name as restaurant_name
            FROM Orders o
            LEFT JOIN Customers c ON o.customer_id = c.customer_id
            LEFT JOIN Restaurants r ON o.restaurant_id = r.restaurant_id
            ORDER BY o.order_placed_time DESC
        """)
        orders = cur.fetchall()

        # Fetch Reviews for Admin
        cur.execute("""
            SELECT 
                rev.review_id, rev.rating, rev.comment, 
                c.Full_name as customer_name, 
                r.name as restaurant_name
            FROM Reviews rev
            LEFT JOIN Customers c ON rev.customer_id = c.customer_id
            LEFT JOIN Restaurants r ON rev.restaurant_id = r.restaurant_id
            ORDER BY rev.review_id DESC
        """)
        reviews = cur.fetchall()

        cur.close()  # Close cursor after fetching all data

        # --- Fetch specific order details (existing code) ---
        if request.method == 'POST' and 'order_id' in request.form:
            track_order_id = request.form['order_id']
            # Log attempt
            logging.info(
                f"Admin attempting to track order ID: {track_order_id}")
            cur_track = None  # Initialize cursor variable
            try:
                track_order_id_int = int(track_order_id)
                cur_track = mysql.connection.cursor(cursorclass=DictCursor)
                # Log the query being executed
                query = """ 
                    SELECT o.*, c.Full_name as customer_name, r.name as restaurant_name
                    FROM Orders o 
                    LEFT JOIN Customers c ON o.customer_id = c.customer_id
                    LEFT JOIN Restaurants r ON o.restaurant_id = r.restaurant_id
                    WHERE o.order_id = %s
                    """
                logging.debug(
                    f"Executing track query: {query} with ID: {track_order_id_int}")
                cur_track.execute(query, (track_order_id_int,))
                order_to_track = cur_track.fetchone()
                if order_to_track:
                    logging.info(
                        f"Found details for order ID: {track_order_id_int}")
                else:
                    logging.warning(
                        f"No order found in database for ID: {track_order_id_int}")
                    # Set a flash message specifically for not found case
                    flash(
                        f'Order ID {track_order_id_int} not found in the database.', 'warning')

            except ValueError:
                logging.warning(
                    f"Invalid Order ID format entered: {track_order_id}")
                flash('Invalid Order ID format. Please enter a number.', 'warning')
            except Exception as e:
                flash(f'Error tracking order: {e}', 'danger')
                logging.error(
                    f"Admin order track error for ID {track_order_id}: {e}")
            finally:
                # Ensure cursor is closed if it was opened
                if cur_track:
                    cur_track.close()

        # Pass fetched data to the template
        return render_template('admin.html', orders=orders, reviews=reviews, tracked_order=order_to_track)

    except Exception as e:
        # Close cursor if it was opened
        try:
            cur.close()
        except:
            pass
        logging.error(f"Error loading admin dashboard: {e}")
        flash(f'Could not load admin dashboard data: {e}', 'danger')
        # Render template with empty orders list on error
        return render_template('admin.html', orders=[], reviews=[], tracked_order=None)


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
@login_required
@admin_required
def update_order_status():
    order_id = request.form['order_id']
    status = request.form['status']
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE Orders SET order_status = %s WHERE order_id = %s", (status, order_id))
    mysql.connection.commit()
    cur.close()
    flash(f'Order {order_id} status updated to {status}.', 'success')
    return redirect(url_for('admin'))


@app.route('/submit-review', methods=['POST'])
@login_required  # Ensure only logged-in users can submit reviews
def submit_review():
    if not current_user.is_authenticated:
        flash('You must be logged in to submit a review.', 'warning')
        return redirect(url_for('login'))

    try:
        # Get data from form
        # Get restaurant_id from dropdown
        restaurant_id = request.form.get('restaurant_id')
        rating = request.form.get('rating')
        comment = request.form.get('review')
        # Optional: if passed from context
        order_id = request.form.get('order_id')
        customer_id = current_user.id

        # Basic Validation
        if not restaurant_id or not rating or not comment:
            flash('Restaurant, rating, and review comment are required.', 'danger')
            # Redirect back to review page, potentially passing old data
            return redirect(url_for('review'))

        try:
            rating = int(rating)
            if not 1 <= rating <= 5:  # Assuming 1-5 star rating based on review.html
                raise ValueError("Rating out of range")
        except (ValueError, TypeError):
            flash('Invalid rating selected.', 'danger')
            return redirect(url_for('review'))

        cur = mysql.connection.cursor()

        # Generate review_id (Manual ID generation)
        cur.execute("SELECT MAX(review_id) FROM Reviews")
        max_id_result = cur.fetchone()
        max_id = max_id_result[0] if max_id_result and max_id_result[0] is not None else 0
        next_review_id = max_id + 1
        logging.info(f"Generating review_id: {next_review_id}")

        # Convert order_id to INT or None
        db_order_id = int(order_id) if order_id else None

        # Insert into Reviews table
        cur.execute("""
            INSERT INTO Reviews (review_id, customer_id, restaurant_id, order_id, rating, comment)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (next_review_id, customer_id, restaurant_id, db_order_id, rating, comment))

        mysql.connection.commit()
        cur.close()

        flash('Thank you for your review!', 'success')
        # Changed redirect to review page
        return redirect(url_for('review'))

    except Exception as e:
        mysql.connection.rollback()
        logging.error(f"Review submission error: {e}")
        flash(f'An error occurred while submitting your review: {e}', 'danger')
        # Avoid closing cursor here if it wasn't opened or failed before opening
        try:
            if cur:
                cur.close()
        except:
            pass
        # Redirect back to review page on error
        return redirect(url_for('review'))

# Add menu item


@app.route('/admin/restaurant/<int:restaurant_id>/menu/add', methods=['POST'])
@login_required
@admin_required
def add_menu_item(restaurant_id):
    try:
        data = request.get_json()  # Use get_json() to parse JSON data from the request
        item_name = data.get('item_name')
        description = data.get('description')
        price = data.get('price')
        category = data.get('category')
        # Default to True if not provided
        is_available = data.get('is_available', True)
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
@login_required
@admin_required
def view_menu_items(restaurant_id):
    cursor = mysql.connection.cursor(cursorclass=DictCursor)
    cursor.execute(
        "SELECT * FROM Menu WHERE restaurant_id = %s", (restaurant_id,))
    menu_items = cursor.fetchall()
    return render_template('view_menu.html', menu_items=menu_items, restaurant_id=restaurant_id)

# Edit menu item


@app.route('/admin/menu/<int:menu_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_menu_item(menu_id):
    cursor = mysql.connection.cursor(cursorclass=DictCursor)
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
@login_required
@admin_required
def delete_menu_item(menu_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM Menu WHERE menu_id = %s", (menu_id,))
    mysql.connection.commit()
    # Redirect needs to be smarter, perhaps back to the specific restaurant's menu or admin dashboard
    # For now, redirecting to admin page which lists restaurants might be okay
    return redirect(url_for('admin'))  # Redirect to admin dashboard


@app.route('/getRestaurantsWithMenus', methods=['GET'])
def get_restaurants_with_menus():
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)

        # Fetch all restaurants
        cur.execute(
            "SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE")
        restaurants = cur.fetchall()
        print(restaurants, "here")
        result = []

        for restaurant in restaurants:
            print("here")
            restaurant_id = restaurant['restaurant_id']

            # Fetch menus for the restaurant
            # Select menu_id, category, item_name, price
            cur.execute(
                "SELECT menu_id, category, item_name, price FROM Menu WHERE restaurant_id = %s AND is_available = TRUE", (restaurant_id,))
            menu_items = cur.fetchall()

            # Group menu items by category
            menu_dict = {}
            for item in menu_items:
                category = item['category']
                if category not in menu_dict:
                    menu_dict[category] = []
                # Append dictionary with menu_id, item_name, price
                menu_dict[category].append({
                    'menu_id': item['menu_id'],
                    'item_name': item['item_name'],
                    'price': float(item['price'])
                })

            # Convert menu_dict to a list of categories with items
            menus = [{'category': category, 'items': items}
                     for category, items in menu_dict.items()]

            result.append({
                'restaurant_id': restaurant_id,  # Include restaurant_id
                'name': restaurant['name'],
                'menus': menus
            })

        cur.close()
        return jsonify(result)

    except Exception as e:
        logging.error(f"Error fetching restaurants with menus: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/getMenuDetails', methods=['GET'])
def get_menu_details():
    try:
        cur = mysql.connection.cursor()

        # Fetch all menu items
        cur.execute("SELECT * FROM Menu")
        menu_items = cur.fetchall()
        print(menu_items)
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
@login_required
@admin_required
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
@login_required
@admin_required
def delete_menu():
    cur = None  # Declare in outer scope
    try:
        data = request.json
        menu_id = data.get('menu_id')

        if not menu_id:
            return jsonify({'error': 'Menu ID is required.'}), 400

        cur = mysql.connection.cursor()
        # Soft delete
        cur.execute(
            "UPDATE Menu SET is_available = FALSE WHERE menu_id = %s", (menu_id,))
        mysql.connection.commit()
        affected_rows = cur.rowcount

        if affected_rows > 0:
            flash(f'Menu item {menu_id} marked as unavailable.', 'success')
            logging.info(
                f"Admin {current_user.id} marked menu item {menu_id} as unavailable")
            return jsonify({'message': 'Menu item marked as unavailable successfully!'}), 200
        else:
            return jsonify({'error': 'Menu item not found or already unavailable.'}), 404

    except Exception as e:
        if "1451" in str(e):
            logging.error(
                f"Foreign key constraint error trying to deactivate menu {menu_id}: {e}")
            return jsonify({'error': 'Cannot deactivate menu item due to related order data.'}), 409
        else:
            logging.error(f"Error deactivating menu item {menu_id}: {e}")
            mysql.connection.rollback()
            return jsonify({'error': str(e)}), 500

    finally:
        if cur:
            try:
                cur.close()
            except:
                pass

# --- User Order Placement ---


@app.route('/api/placeOrder', methods=['POST'])
@login_required
def place_order_api():
    try:
        data = request.json
        customer_info = data.get('customerInfo')
        order_items_data = data.get('items')
        restaurant_id = data.get('restaurantId')  # Frontend needs to send this

        if not customer_info or not order_items_data or not restaurant_id:
            return jsonify({'error': 'Missing order data: customerInfo, items, or restaurantId'}), 400

        if not current_user.is_authenticated:
            return jsonify({'error': 'User not logged in'}), 401

        customer_id = current_user.id
        # Assuming address is passed in customerInfo
        delivery_address = customer_info.get('address')
        # Potentially prefill name/phone from current_user if not provided, or validate provided ones

        if not delivery_address:
            return jsonify({'error': 'Delivery address is required'}), 400

        cur = mysql.connection.cursor()

        # 1. Calculate Total Price and Validate Items
        total_price = 0
        item_ids_and_quantities = []
        for item_data in order_items_data:
            # Frontend needs to send menu_id
            menu_id = item_data.get('menu_id')
            quantity = item_data.get('quantity')
            if not menu_id or not quantity or quantity <= 0:
                return jsonify({'error': 'Invalid item data found in order'}), 400

            # Fetch item price from DB to ensure accuracy and availability
            cur.execute(
                "SELECT price, is_available FROM Menu WHERE menu_id = %s", (menu_id,))
            menu_item = cur.fetchone()
            # Check if item exists and is available
            if not menu_item or not menu_item[1]:
                cur.close()
                return jsonify({'error': f'Menu item with ID {menu_id} not found or unavailable.'}), 400

            item_price = menu_item[0]
            total_price += item_price * quantity
            item_ids_and_quantities.append(
                {'menu_id': menu_id, 'quantity': quantity, 'price': item_price})

        # 2. Generate Order ID
        cur.execute("SELECT MAX(order_id) FROM Orders")
        max_id_result = cur.fetchone()
        max_id = max_id_result[0] if max_id_result and max_id_result[0] is not None else 0
        next_order_id = max_id + 1
        logging.info(f"Generating order_id: {next_order_id}")

        # 3. Insert into Orders table
        cur.execute("""
            INSERT INTO Orders (order_id, customer_id, restaurant_id, total_price, delivery_address, order_status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (next_order_id, customer_id, restaurant_id, total_price, delivery_address, 'placed'))

        # 4. Insert into OrderItems table
        for item in item_ids_and_quantities:
            # Generate Order Item ID (Assuming AUTO_INCREMENT is NOT set, otherwise remove this)
            cur.execute("SELECT MAX(order_item_id) FROM OrderItems")
            max_oi_id_result = cur.fetchone()
            max_oi_id = max_oi_id_result[0] if max_oi_id_result and max_oi_id_result[0] is not None else 0
            next_order_item_id = max_oi_id + 1

            cur.execute("""
                INSERT INTO OrderItems (order_item_id, order_id, item_id, quantity, item_price_at_order)
                VALUES (%s, %s, %s, %s, %s)
            """, (next_order_item_id, next_order_id, item['menu_id'], item['quantity'], item['price']))

        # 5. Commit transaction
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Order placed successfully!', 'orderId': next_order_id}), 201

    except Exception as e:
        mysql.connection.rollback()
        logging.error(f"Order placement error: {e}")
        return jsonify({'error': str(e)}), 500

# --- User Order Tracking ---


@app.route('/api/trackOrder/<int:order_id>', methods=['GET'])
@login_required
def track_order_api(order_id):
    try:
        if not current_user.is_authenticated:
            return jsonify({'error': 'User not logged in'}), 401

        customer_id = current_user.id

        # Use dictionary cursor for easier access
        cur = mysql.connection.cursor(cursorclass=DictCursor)

        # Fetch order details, ensuring it belongs to the current user
        cur.execute("""
            SELECT o.order_id, o.restaurant_id, o.order_status, o.order_placed_time, 
                   o.total_price, o.delivery_address, r.name as restaurant_name
            FROM Orders o
            JOIN Restaurants r ON o.restaurant_id = r.restaurant_id
            WHERE o.order_id = %s AND o.customer_id = %s
        """, (order_id, customer_id))
        order = cur.fetchone()

        if not order:
            # If the initial query (checking order_id AND customer_id) fails,
            # return 404 immediately without checking if the order ID exists for someone else.
            cur.close()
            return jsonify({'error': 'Order not found.'}), 404

        # Fetch order items for this order
        cur.execute("""
            SELECT oi.quantity, oi.item_price_at_order, m.item_name
            FROM OrderItems oi
            JOIN Menu m ON oi.item_id = m.menu_id
            WHERE oi.order_id = %s
        """, (order_id,))
        order_items = cur.fetchall()

        cur.close()

        # Combine results
        order_details = {
            'orderId': order['order_id'],
            'restaurantName': order['restaurant_name'],
            'status': order['order_status'],
            'placedTime': order['order_placed_time'].isoformat() if order['order_placed_time'] else None,
            'totalPrice': float(order['total_price']),
            'deliveryAddress': order['delivery_address'],
            'items': [
                {
                    'itemName': item['item_name'],
                    'quantity': item['quantity'],
                    'price': float(item['item_price_at_order'])
                }
                for item in order_items
            ]
        }

        return jsonify(order_details), 200

    except Exception as e:
        logging.error(f"Order tracking error for order {order_id}: {e}")
        # Avoid closing cursor here if it wasn't opened or failed before opening
        try:
            if cur:
                cur.close()
        except:
            pass  # Ignore errors during cleanup
        return jsonify({'error': str(e)}), 500

# --- Admin Order Cancellation ---


@app.route('/api/admin/order/<int:order_id>', methods=['DELETE'])
@login_required
@admin_required
def cancel_order_admin(order_id):
    try:
        cur = mysql.connection.cursor()

        # Check if order exists before attempting update
        cur.execute(
            "SELECT order_id FROM Orders WHERE order_id = %s", (order_id,))
        order = cur.fetchone()
        if not order:
            cur.close()
            return jsonify({'error': 'Order not found'}), 404

        # Update the order status to 'cancelled'
        cur.execute(
            "UPDATE Orders SET order_status = %s WHERE order_id = %s", ('cancelled', order_id))
        mysql.connection.commit()

        # Check if update was successful (optional, commit() doesn't guarantee change if status was already cancelled)
        # You could re-fetch the status or rely on affected_rows if the DB driver supports it reliably.

        cur.close()
        logging.info(
            f"Admin user {current_user.id} cancelled order {order_id}")
        return jsonify({'message': f'Order {order_id} cancelled successfully.'}), 200

    except Exception as e:
        mysql.connection.rollback()
        logging.error(
            f"Error cancelling order {order_id} by admin {current_user.id}: {e}")
        try:
            if cur:
                cur.close()
        except:
            pass
        return jsonify({'error': str(e)}), 500

# --- Admin Review Management APIs ---


@app.route('/api/admin/review/<int:review_id>', methods=['PUT'])
@login_required
@admin_required
def update_review_admin(review_id):
    try:
        data = request.json
        new_comment = data.get('comment')

        if new_comment is None:  # Check if comment key exists
            return jsonify({'error': 'Missing comment data'}), 400

        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE Reviews SET comment = %s WHERE review_id = %s", (new_comment, review_id))
        mysql.connection.commit()
        affected_rows = cur.rowcount  # Check if update actually happened
        cur.close()

        if affected_rows > 0:
            flash(f'Review {review_id} updated successfully.', 'success')
            return jsonify({'message': f'Review {review_id} updated successfully.'}), 200
        else:
            return jsonify({'error': 'Review not found or no changes made'}), 404

    except Exception as e:
        mysql.connection.rollback()
        logging.error(
            f"Error updating review {review_id} by admin {current_user.id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/review/<int:review_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_review_admin(review_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM Reviews WHERE review_id = %s", (review_id,))
        mysql.connection.commit()
        affected_rows = cur.rowcount  # Check if delete actually happened
        cur.close()

        if affected_rows > 0:
            flash(f'Review {review_id} deleted successfully.', 'success')
            logging.info(
                f"Admin user {current_user.id} deleted review {review_id}")
            return jsonify({'message': f'Review {review_id} deleted successfully.'}), 200
        else:
            return jsonify({'error': 'Review not found'}), 404

    except Exception as e:
        mysql.connection.rollback()
        logging.error(
            f"Error deleting review {review_id} by admin {current_user.id}: {e}")
        return jsonify({'error': str(e)}), 500

# --- End Admin Review Management APIs ---

# --- Profile Management ---


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        # Potentially add city, state, pin code if those fields exist in the form/model

        # Basic Validation
        if not name or not email or not phone or not address:
            flash('All fields are required.', 'danger')
            return redirect(url_for('profile'))

        # Email Uniqueness Check (if email has changed)
        if email != current_user.email:
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT customer_id FROM Customers WHERE email = %s", (email,))
            existing_user = cur.fetchone()
            cur.close()  # Close cursor after check
            if existing_user:
                flash(
                    'That email address is already registered by another user.', 'warning')
                return redirect(url_for('profile'))  # Stay on profile page

        # Update user details in the database
        try:
            cur = mysql.connection.cursor()
            # Add city, state, pin_code to query if they are being updated
            cur.execute("""
                UPDATE Customers 
                SET Full_name = %s, email = %s, phone = %s, address = %s
                WHERE customer_id = %s
            """, (name, email, phone, address, current_user.id))
            mysql.connection.commit()
            cur.close()
            flash('Profile updated successfully!', 'success')
            # Reload user object to reflect changes immediately in the header/session
            load_user(current_user.id)
        except Exception as e:
            mysql.connection.rollback()
            flash(f'An error occurred while updating profile: {e}', 'danger')
            logging.error(
                f"Profile update error for user {current_user.id}: {e}")
            try:
                cur.close()
            except:
                pass

        # Redirect back to profile page after POST
        return redirect(url_for('profile'))

    # GET Request: Render the profile page with current user data
    # current_user is implicitly available
    return render_template('profile.html')

# --- End Profile Management ---


if __name__ == '__main__':
    app.run(debug=True)
