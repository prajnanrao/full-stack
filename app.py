from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from flask_login import LoginManager, login_user, login_required, UserMixin, logout_user, current_user
import logging
from werkzeug.security import generate_password_hash, check_password_hash
import functools
from MySQLdb.cursors import DictCursor
from datetime import datetime

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
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- User Class (Reverted to simpler form) --- 
class User(UserMixin):
    def __init__(self, id, email, name, is_admin, address=None, phone=None):
        self.id = id
        self.email = email
        self.name = name
        self.is_admin = is_admin
        self.address = address
        self.phone = phone
    
# --- User Loader (Reverted to simpler form) --- 
@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor(cursorclass=DictCursor) 
    user_obj = None
    cur.execute("SELECT customer_id, email, Full_name, is_admin, phone, address FROM Customers WHERE customer_id = %s", (int(user_id),))
    user_data = cur.fetchone()
    if user_data:
        is_admin_bool = bool(user_data['is_admin'])
        user_obj = User(id=user_data['customer_id'], email=user_data['email'], name=user_data['Full_name'], 
                        is_admin=is_admin_bool, 
                        phone=user_data['phone'], address=user_data['address'])
    cur.close()
    return user_obj

# --- Admin Required Decorator --- 
def admin_required(func):
    @functools.wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not current_user.is_admin:
            flash('Admin access required.', 'warning')
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
        data = request.json
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
        cur.execute("SELECT MAX(restaurant_id) FROM Restaurants")
        max_id = cur.fetchone()[0]
        restaurant_id = (max_id + 1) if max_id else 1
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
    cur = None # Initialize cur
    try:
        data = request.json
        restaurant_id = data.get('restaurant_id')
        if not restaurant_id:
             return jsonify({'error': 'Restaurant ID is required.'}), 400
        cur = mysql.connection.cursor()
        cur.execute("UPDATE Restaurants SET is_active = FALSE WHERE restaurant_id = %s", (restaurant_id,))
        mysql.connection.commit()
        affected_rows = cur.rowcount
        if affected_rows > 0:
             flash(f'Restaurant {restaurant_id} marked as inactive.', 'success')
             logging.info(f"Admin {current_user.id} deactivated restaurant {restaurant_id}")
             return jsonify({'message': 'Restaurant marked as inactive successfully!'}), 200
        else:
             return jsonify({'error': 'Restaurant not found or already inactive.'}), 404
    except Exception as e:
        if "1451" in str(e):
             logging.error(f"Foreign key constraint error trying to deactivate restaurant {restaurant_id}: {e}")
             return jsonify({'error': 'Cannot deactivate restaurant due to related data. Please check associated menus or orders.'}), 409
        else:
             logging.error(f"Error deactivating restaurant {restaurant_id}: {e}")
             if cur: mysql.connection.rollback()
             return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in delete_restaurant: {e_close}")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index')) 

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = True if request.form.get('remember') else False
        user_obj = None

        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("SELECT customer_id, email, Full_name, password_hash, is_admin, phone, address FROM Customers WHERE email = %s", (email,))
        customer_data = cur.fetchone()
        cur.close() 

        if customer_data and check_password_hash(customer_data['password_hash'], password):
            is_admin_bool = bool(customer_data['is_admin'])
            user_obj = User(id=customer_data['customer_id'], email=customer_data['email'], 
                            name=customer_data['Full_name'], is_admin=is_admin_bool,
                            phone=customer_data['phone'], address=customer_data['address'])
        
        if user_obj:
            login_user(user_obj, remember=remember)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user_obj.is_admin:
                return redirect(url_for('admin')) 
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check email and password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = current_user.id
    cur = mysql.connection.cursor(cursorclass=DictCursor)

    if request.method == 'POST':
        new_name = request.form.get('name')
        new_email = request.form.get('email')
        new_phone = request.form.get('phone')
        new_address = request.form.get('address')
        # Optional: Add city, state, pin_code if they are included in the form and User model
        # new_city = request.form.get('city')
        # new_state = request.form.get('state')
        # new_pin_code = request.form.get('pin_code')

        # Check if email is being changed and if it's already taken
        if new_email != current_user.email:
            cur.execute("SELECT customer_id FROM Customers WHERE email = %s AND customer_id != %s", (new_email, user_id))
            if cur.fetchone():
                flash('That email address is already in use by another account.', 'danger')
                cur.close()
                return redirect(url_for('profile'))

        try:
            # Note: The Customers table has city, state, Pin_code. 
            # For simplicity, this update focuses on fields present in the active part of profile.html.
            # If city, state, pin_code are added to the form, update this query.
            cur.execute("""
                UPDATE Customers 
                SET Full_name = %s, email = %s, phone = %s, address = %s
                WHERE customer_id = %s
            """, (new_name, new_email, new_phone, new_address, user_id))
            mysql.connection.commit()
            
            # Update the current_user object in session
            current_user.name = new_name
            current_user.email = new_email
            current_user.phone = new_phone
            current_user.address = new_address
            # If city, state, pin_code are added, update them on current_user too if they exist on the object.

            flash('Your profile has been updated successfully!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            app.logger.error(f"Error updating profile for user {user_id}: {e}")
        finally:
            cur.close()
        return redirect(url_for('profile'))

    # For GET request, simply render the template
    # The template will use current_user for initial values
    return render_template('profile.html')

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
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("""
            SELECT r.review_id, r.rating, r.comment, c.Full_name as customer_name, rest.name as restaurant_name
            FROM Reviews r
            JOIN Customers c ON r.customer_id = c.customer_id
            JOIN Restaurants rest ON r.restaurant_id = rest.restaurant_id
            ORDER BY r.review_id DESC
        """)
        reviews = cur.fetchall()
        cur.close()
    except Exception as e:
        logging.error(f"Error fetching reviews: {e}")
        flash('Could not load reviews.', 'warning')
        reviews = []
    return render_template('review.html', reviews=reviews)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name'] 
        password = request.form['password']
        phone = request.form.get('phone') 
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        pin_code = request.form.get('pin_code')
        if not all([email, name, password, phone, address, city, state, pin_code]):
            flash('All fields are required!', 'danger')
            return redirect(url_for('register'))
        cur = mysql.connection.cursor()
        cur.execute("SELECT customer_id FROM Customers WHERE email = %s", (email,))
        existing_user = cur.fetchone()
        if existing_user:
            flash('Email address already registered.', 'warning')
            cur.close()
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        try:
            cur.execute("SELECT MAX(customer_id) FROM Customers")
            max_id_result = cur.fetchone()
            max_id = max_id_result[0] if max_id_result and max_id_result[0] is not None else 0 
            next_customer_id = max_id + 1
            logging.info(f"Manually generating next customer_id: {next_customer_id}")
            cur.execute("INSERT INTO Customers (customer_id, Full_name, email, password_hash, phone, address, city, state, Pin_code) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (next_customer_id, name, email, hashed_password, phone, address, city, state, pin_code))
            mysql.connection.commit()
            flash('Registration successful! Please log in.', 'success')
            cur.close()
            return redirect(url_for('login'))
        except Exception as e:
            if cur: mysql.connection.rollback()
            flash(f'An error occurred: {e}', 'danger')
            logging.error(f"Registration error: {e}")
            if cur: cur.close()
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/admin', methods=['GET', 'POST'])
@login_required 
@admin_required
def admin():
    orders = []
    order_to_track = None
    reviews = [] 
    cur = None # Initialize cur
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("""
            SELECT o.order_id, o.customer_id, o.restaurant_id, o.supplier_id, o.order_status, o.order_placed_time, 
                   o.preparation_complete_time, o.dispatch_time, o.delivery_time, 
                   o.total_price, o.applied_coupon_id, o.discount_amount, o.final_amount, 
                   o.delivery_address,
                   c.Full_name as customer_name, r.name as restaurant_name
            FROM Orders o
            LEFT JOIN Customers c ON o.customer_id = c.customer_id
            LEFT JOIN Restaurants r ON o.restaurant_id = r.restaurant_id
            ORDER BY o.order_placed_time DESC
        """)
        orders = cur.fetchall()
        cur.execute("""
            SELECT rev.review_id, rev.rating, rev.comment, c.Full_name as customer_name, r.name as restaurant_name
            FROM Reviews rev
            LEFT JOIN Customers c ON rev.customer_id = c.customer_id
            LEFT JOIN Restaurants r ON rev.restaurant_id = r.restaurant_id
            ORDER BY rev.review_id DESC
        """)
        reviews = cur.fetchall()
        if request.method == 'POST' and 'order_id' in request.form:
            track_order_id = request.form['order_id']
            logging.info(f"Admin attempting to track order ID: {track_order_id}") 
            cur_track = None 
            try:
                track_order_id_int = int(track_order_id)
                # Always create a new cursor for tracking to avoid issues with the main cursor's state.
                cur_track = mysql.connection.cursor(cursorclass=DictCursor)
                query = """ 
                    SELECT o.*, c.Full_name as customer_name, r.name as restaurant_name
                    FROM Orders o 
                    LEFT JOIN Customers c ON o.customer_id = c.customer_id
                    LEFT JOIN Restaurants r ON o.restaurant_id = r.restaurant_id
                    WHERE o.order_id = %s
                    """
                logging.debug(f"Executing track query: {query} with ID: {track_order_id_int}")
                cur_track.execute(query, (track_order_id_int,))
                order_to_track = cur_track.fetchone()
                if order_to_track:
                    logging.info(f"Found details for order ID: {track_order_id_int}")
                else:
                    logging.warning(f"No order found in database for ID: {track_order_id_int}")
                    flash(f'Order ID {track_order_id_int} not found in the database.', 'warning') 
            except ValueError:
                 logging.warning(f"Invalid Order ID format entered: {track_order_id}")
                 flash('Invalid Order ID format. Please enter a number.', 'warning')
            except Exception as e:
                 flash(f'Error tracking order: {e}', 'danger')
                 logging.error(f"Admin order track error for ID {track_order_id}: {e}")
            finally:
                 if cur_track: # Always try to close cur_track if it was initialized
                     try: 
                         cur_track.close()
                     except Exception as e_close_track:
                         logging.warning(f"Error closing cur_track in admin: {e_close_track}")
        return render_template('admin.html', orders=orders, reviews=reviews, tracked_order=order_to_track)
    except Exception as e:
        logging.error(f"Error loading admin dashboard: {e}")
        flash(f'Could not load admin dashboard data: {e}', 'danger')
        return render_template('admin.html', orders=[], reviews=[], tracked_order=None)
    finally:
        if cur: 
            try: cur.close()
            except: pass

@app.route('/track-order/<int:order_id>', methods=['GET'])
@login_required
def track_order_details(order_id):
    cur = mysql.connection.cursor(cursorclass=DictCursor) # Use DictCursor for consistency
    cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cur.fetchone()
    cur.close()
    if order:
        return render_template('track_order.html', order=order)
    else:
        flash("Order not found", 'danger') # Added flash message
        return redirect(url_for('trackOrder')) # Redirect to general track order page

@app.route('/update-order-status', methods=['POST'])
@login_required
@admin_required
def update_order_status():
    cur = None # Initialize
    try:
        order_id = request.form['order_id']
        status = request.form['status']
        cur = mysql.connection.cursor(cursorclass=DictCursor) 
        cur.execute("SELECT customer_id FROM Orders WHERE order_id = %s", (order_id,))
        order_data = cur.fetchone()
        customer_id_for_notification = order_data['customer_id'] if order_data else None
        cur.execute("UPDATE Orders SET order_status = %s WHERE order_id = %s", (status, order_id))
        mysql.connection.commit()
        if customer_id_for_notification:
            create_notification(user_id=customer_id_for_notification, 
                                type='order_status', 
                                message=f'The status of your order #{order_id} has been updated to: {status.title()}.',
                                related_order_id=order_id)
        else:
            logging.warning(f"Could not send notification for order {order_id} status update: customer_id not found.")
        flash(f'Order {order_id} status updated to {status}.', 'success') 
    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error updating order status for {order_id}: {e}")
        flash("Error updating order status.", "danger")
    finally:
        if cur: 
            try: cur.close()
            except: pass
    return redirect(url_for('admin'))

@app.route('/submit-review', methods=['POST'])
@login_required
def submit_review():
    cur = None # Initialize cur
    try:
        if not current_user.is_authenticated:
             flash('You must be logged in to submit a review.', 'warning')
             return redirect(url_for('login'))
        restaurant_id = request.form.get('restaurant_id')
        rating = request.form.get('rating')
        comment = request.form.get('review')
        order_id = request.form.get('order_id') 
        customer_id = current_user.id
        if not restaurant_id or not rating or not comment:
            flash('Restaurant, rating, and review comment are required.', 'danger')
            return redirect(url_for('review')) 
        try:
            rating = int(rating)
            if not 1 <= rating <= 5:
                raise ValueError("Rating out of range")
        except (ValueError, TypeError):
             flash('Invalid rating selected.', 'danger')
             return redirect(url_for('review'))
        cur = mysql.connection.cursor()
        cur.execute("SELECT MAX(review_id) FROM Reviews")
        max_id_result = cur.fetchone()
        max_id = max_id_result[0] if max_id_result and max_id_result[0] is not None else 0
        next_review_id = max_id + 1
        logging.info(f"Generating review_id: {next_review_id}")
        db_order_id = int(order_id) if order_id else None
        cur.execute("""
            INSERT INTO Reviews (review_id, customer_id, restaurant_id, order_id, rating, comment)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (next_review_id, customer_id, restaurant_id, db_order_id, rating, comment))
        mysql.connection.commit()
        flash('Thank you for your review!', 'success')
    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Review submission error: {e}")
        flash(f'An error occurred while submitting your review: {e}', 'danger')
    finally:
        if cur: 
            try: cur.close()
            except: pass
    return redirect(url_for('review'))

@app.route('/getMenuDetails', methods=['GET'])
@login_required
@admin_required # Assuming only admins should access all menu details this way
def get_menu_details():
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        # Fetching all menu items, joining with restaurant for context if needed in future
        # The current JS in admin.html seems to primarily use fields directly from the Menu table
        cur.execute("""
            SELECT m.*, r.name as restaurant_name 
            FROM Menu m
            LEFT JOIN Restaurants r ON m.restaurant_id = r.restaurant_id
            ORDER BY m.restaurant_id, m.item_name
        """)
        menu_items = cur.fetchall()
        cur.close()
        # Convert decimal fields to strings for JSON serialization if they exist
        for item in menu_items:
            if 'price' in item and item['price'] is not None:
                item['price'] = str(item['price'])
        return jsonify(menu_items)
    except Exception as e:
        logging.error(f"Error fetching all menu details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/restaurant/<int:restaurant_id>/menu/add', methods=['POST'])
@login_required
@admin_required
def add_menu_item(restaurant_id):
    cur = None # Initialize cur
    try:
        data = request.get_json()
        item_name = data.get('item_name')
        description = data.get('description')
        price = data.get('price')
        category = data.get('category')
        is_available = data.get('is_available', True)
        preparation_time = data.get('preparation_time')
        if not item_name or not price or not category:
            return jsonify({'error': 'Missing required fields: item_name, price, or category'}), 400
        cur = mysql.connection.cursor()
        cur.execute("SELECT MAX(menu_id) FROM Menu")
        max_id = cur.fetchone()[0]
        menu_id = (max_id + 1) if max_id else 1
        logging.info(f"Generated menu_id: {menu_id}") # Corrected logging variable
        cur.execute("""
            INSERT INTO Menu (menu_id, restaurant_id, item_name, description, price, category, is_available, preparation_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (menu_id, restaurant_id, item_name, description, price, category, is_available, preparation_time))
        mysql.connection.commit()
        return jsonify({'message': 'Menu item added successfully!'}), 201
    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error adding menu item for restaurant {restaurant_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cur: 
            try: cur.close()
            except: pass

@app.route('/updateMenu', methods=['PUT'])
@login_required
@admin_required
def update_menu_item_details():
    cur = None
    data = None # Initialize data to ensure it's defined in the scope for the except block
    try:
        data = request.get_json()
        menu_id = data.get('menu_id')
        item_name = data.get('item_name')
        description = data.get('description')
        price = data.get('price')
        category = data.get('category')
        is_available = data.get('is_available', True) # Default to True if not provided
        preparation_time = data.get('preparation_time')

        if not all([menu_id, item_name, price, category]): # Description and prep time can be optional
            return jsonify({'error': 'Missing required fields: menu_id, item_name, price, or category'}), 400
        
        try:
            price = float(price)
            menu_id = int(menu_id)
            if preparation_time is not None and str(preparation_time).strip() != '':
                preparation_time = int(preparation_time)
            else:
                preparation_time = None # Ensure it's None if empty or not provided for DB
        except ValueError:
            return jsonify({'error': 'Invalid data type for price, menu ID, or preparation time.'}), 400

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE Menu 
            SET item_name = %s, description = %s, price = %s, category = %s, 
                is_available = %s, preparation_time = %s
            WHERE menu_id = %s
        """, (item_name, description, price, category, bool(is_available), preparation_time, menu_id))
        
        if cur.rowcount == 0:
            # No rollback needed here as it's a select-like check before commit
            return jsonify({'error': 'Menu item not found or no changes made.'}), 404

        mysql.connection.commit()
        logging.info(f"Admin {current_user.id} updated menu item {menu_id}.")
        return jsonify({'message': f'Menu item {menu_id} updated successfully.'}), 200

    except Exception as e:
        if cur: mysql.connection.rollback()
        # Use a more robust way to get menu_id for logging if data might be None
        log_menu_id = data.get('menu_id', 'unknown') if isinstance(data, dict) else 'unknown'
        logging.error(f"Error updating menu item {log_menu_id} by admin {current_user.id}: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({'error': 'An internal server error occurred while updating the menu item.'}), 500
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in update_menu_item_details: {e_close}")

@app.route('/deleteMenu', methods=['DELETE'])
@login_required
@admin_required
def delete_menu_item_route(): # Renamed to avoid conflict with JS function name if ever imported
    cur = None
    data = None # Initialize for use in exception logging
    try:
        data = request.get_json()
        menu_id = data.get('menu_id')
        if not menu_id:
            return jsonify({'error': 'Menu ID is required.'}), 400
        
        try:
            menu_id = int(menu_id)
        except ValueError:
            return jsonify({'error': 'Invalid Menu ID format.'}), 400

        cur = mysql.connection.cursor()
        # Mark as unavailable instead of deleting
        cur.execute("UPDATE Menu SET is_available = FALSE WHERE menu_id = %s", (menu_id,))
        
        if cur.rowcount == 0:
            # No rollback needed here as it's a select-like check before commit
            return jsonify({'error': 'Menu item not found or already marked as unavailable.'}), 404

        mysql.connection.commit()
        logging.info(f"Admin {current_user.id} marked menu item {menu_id} as unavailable.")
        return jsonify({'message': 'Menu item marked as unavailable successfully.'}), 200

    except Exception as e:
        if cur: mysql.connection.rollback()
        log_menu_id = data.get('menu_id', 'unknown') if isinstance(data, dict) else 'unknown'
        logging.error(f"Error deactivating menu item {log_menu_id} by admin {current_user.id}: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({'error': 'An internal server error occurred while deactivating menu item.'}), 500
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in delete_menu_item_route: {e_close}")

@app.route('/admin/staff', methods=['GET'])
@login_required
@admin_required
def admin_list_staff():
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("""
            SELECT rs.*, r.name as restaurant_name 
            FROM RestaurantStaff rs
            LEFT JOIN Restaurants r ON rs.restaurant_id = r.restaurant_id
            ORDER BY rs.last_name, rs.first_name
        """)
        staff_list = cur.fetchall()
        cur.close()
        return render_template('admin_staff_list.html', staff_list=staff_list)
    except Exception as e:
        logging.error(f"Error fetching staff list: {e}")
        flash('Could not load staff list.', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/staff/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_staff():
    cur = None
    cur_restaurants = None
    try:
        if request.method == 'POST':
            restaurant_id = request.form.get('restaurant_id')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            role = request.form.get('role')
            email = request.form.get('email')
            phone = request.form.get('phone')
            shift_timings = request.form.get('shift_timings')

            if not all([restaurant_id, first_name, last_name, role, email, phone]):
                flash('All fields except shift timings are required.', 'danger')
                cur_restaurants = mysql.connection.cursor(cursorclass=DictCursor)
                cur_restaurants.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
                restaurants = cur_restaurants.fetchall()
                return render_template('admin_edit_staff.html', action='Add', restaurants=restaurants, staff_member=request.form), 400
            
            cur = mysql.connection.cursor()
            cur.execute("SELECT MAX(staff_id) FROM RestaurantStaff")
            max_id_result = cur.fetchone()
            next_staff_id = (max_id_result[0] + 1) if max_id_result and max_id_result[0] is not None else 1
            
            cur.execute("""
                INSERT INTO RestaurantStaff (staff_id, restaurant_id, first_name, last_name, role, email, phone, shift_timings, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (next_staff_id, restaurant_id, first_name, last_name, role, email, phone, shift_timings, True))
            mysql.connection.commit()
            return redirect(url_for('admin_list_staff'))

        cur_restaurants = mysql.connection.cursor(cursorclass=DictCursor)
        cur_restaurants.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
        restaurants = cur_restaurants.fetchall()
        return render_template('admin_edit_staff.html', action='Add', restaurants=restaurants)

    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error adding staff: {e}")
        flash(f'Error adding staff: {str(e)}', 'danger')
        # On error, re-fetch restaurants for the template
        restaurants_for_template = []
        try:
            cur_restaurants_err = mysql.connection.cursor(cursorclass=DictCursor)
            cur_restaurants_err.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
            restaurants_for_template = cur_restaurants_err.fetchall()
            cur_restaurants_err.close()
        except Exception as e_rest:
            logging.error(f"Error fetching restaurants for add staff form after main error: {e_rest}")
        return render_template('admin_edit_staff.html', action='Add', restaurants=restaurants_for_template, staff_member=request.form if request.method == 'POST' else None)
    finally:
        if cur: # Main cursor for DB operations
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing main cursor in admin_add_staff: {e_close}")
        if cur_restaurants: # Cursor for fetching restaurants list for the form
            try:
                cur_restaurants.close()
            except Exception as e_close:
                logging.warning(f"Error closing restaurants_cursor in admin_add_staff: {e_close}")

@app.route('/admin/staff/edit/<int:staff_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_staff(staff_id):
    cur = None
    try:
        if request.method == 'POST':
            restaurant_id = request.form.get('restaurant_id')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            role = request.form.get('role')
            email = request.form.get('email')
            phone = request.form.get('phone')
            shift_timings = request.form.get('shift_timings')
            is_active = 'is_active' in request.form

            if not all([restaurant_id, first_name, last_name, role, email, phone]):
                flash('Required fields are missing.', 'danger')
                # Re-fetch for template
                cur_data = mysql.connection.cursor(cursorclass=DictCursor)
                cur_data.execute("SELECT * FROM RestaurantStaff WHERE staff_id = %s", (staff_id,))
                staff_member = cur_data.fetchone()
                cur_data.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
                restaurants = cur_data.fetchall()
                cur_data.close()
                return render_template('admin_edit_staff.html', action='Edit', staff_member=staff_member, restaurants=restaurants, staff_id=staff_id), 400

            cur = mysql.connection.cursor()
            # Simplified UPDATE query without password
            cur.execute("""
                UPDATE RestaurantStaff SET restaurant_id=%s, first_name=%s, last_name=%s, role=%s, email=%s, 
                       phone=%s, shift_timings=%s, is_active=%s
                WHERE staff_id=%s
            """, (restaurant_id, first_name, last_name, role, email, phone, shift_timings, is_active, staff_id))
            
            mysql.connection.commit()
            flash(f'Staff member {first_name} {last_name} updated successfully.', 'success')
            return redirect(url_for('admin_list_staff'))

        # GET request: Show edit form
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("SELECT * FROM RestaurantStaff WHERE staff_id = %s", (staff_id,))
        staff_member = cur.fetchone()
        cur.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
        restaurants = cur.fetchall()
        
        if not staff_member:
            flash('Staff member not found.', 'danger')
            return redirect(url_for('admin_list_staff'))
        return render_template('admin_edit_staff.html', action='Edit', staff_member=staff_member, restaurants=restaurants, staff_id=staff_id)

    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error editing staff {staff_id}: {e}")
        flash(f'Error editing staff: {str(e)}', 'danger')
        # On error, attempt to re-fetch data for the form
        staff_member_for_template = None
        restaurants_for_template = []
        try:
            cur_err = mysql.connection.cursor(cursorclass=DictCursor)
            cur_err.execute("SELECT * FROM RestaurantStaff WHERE staff_id = %s", (staff_id,))
            staff_member_for_template = cur_err.fetchone()
            cur_err.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
            restaurants_for_template = cur_err.fetchall()
            cur_err.close()
        except Exception as e_data:
            logging.error(f"Error fetching data for edit staff form after main error: {e_data}")

        return render_template('admin_edit_staff.html', action='Edit', staff_member=staff_member_for_template or request.form, restaurants=restaurants_for_template, staff_id=staff_id)
    finally:
        if cur: # Simplified check
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in admin_edit_staff: {e_close}")

@app.route('/admin/staff/deactivate/<int:staff_id>', methods=['POST'])
@login_required
@admin_required
def admin_deactivate_staff(staff_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE RestaurantStaff SET is_active = FALSE WHERE staff_id = %s", (staff_id,))
        mysql.connection.commit()
        affected_rows = cur.rowcount
        cur.close()
        if affected_rows > 0:
            flash('Staff member deactivated successfully.', 'success')
        else:
            flash('Staff member not found or already inactive.', 'warning')
    except Exception as e:
        mysql.connection.rollback()
        logging.error(f"Error deactivating staff {staff_id}: {e}")
        flash(f'Error deactivating staff: {str(e)}', 'danger')
    return redirect(url_for('admin_list_staff'))

@app.route('/admin/staff/activate/<int:staff_id>', methods=['POST'])
@login_required
@admin_required
def admin_activate_staff(staff_id):
    cur = None
    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE RestaurantStaff SET is_active = TRUE WHERE staff_id = %s", (staff_id,))
        mysql.connection.commit()
        flash(f'Staff ID {staff_id} activated successfully.', 'success')
        logging.info(f"Admin {current_user.id} activated staff {staff_id}")
    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error activating staff {staff_id}: {e}")
        flash(f'Error activating staff: {str(e)}', 'danger')
    finally:
        if cur: 
            try: cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in admin_activate_staff: {e_close}")
    return redirect(url_for('admin_list_staff'))

# --- Supplier Management (Admin) ---
@app.route('/admin/suppliers', methods=['GET'])
@login_required
@admin_required
def admin_list_suppliers():
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("SELECT * FROM Supplier ORDER BY name")
        suppliers = cur.fetchall()
        cur.close()
        return render_template('admin_supplier_list.html', suppliers=suppliers)
    except Exception as e:
        logging.error(f"Error fetching supplier list: {e}")
        flash('Could not load supplier list.', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/suppliers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_supplier():
    cur = None
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            contact_person = request.form.get('contact_person')
            email = request.form.get('email')
            phone = request.form.get('phone')
            vehicle_number = request.form.get('vehicle_number')
            supply_type = request.form.get('supply_type')
            assigned_orders = request.form.get('assigned_orders', 0) # Default to 0 if not provided

            if not all([name, contact_person, email, phone, vehicle_number, supply_type]):
                flash('All fields except assigned orders are required.', 'danger')
                return render_template('admin_edit_supplier.html', action='Add', supplier=request.form), 400

            cur = mysql.connection.cursor()
            cur.execute("SELECT MAX(supplier_id) FROM Supplier")
            max_id_result = cur.fetchone()
            next_supplier_id = (max_id_result[0] + 1) if max_id_result and max_id_result[0] is not None else 1
            
            cur.execute("""
                INSERT INTO Supplier (supplier_id, name, contact_person, email, phone, vehicle_number, supply_type, assigned_orders, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (next_supplier_id, name, contact_person, email, phone, vehicle_number, supply_type, int(assigned_orders), True))
            mysql.connection.commit()
            return redirect(url_for('admin_list_suppliers'))

        # GET request: Show add form
        return render_template('admin_edit_supplier.html', action='Add')

    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error adding supplier: {e}")
        flash(f'Error adding supplier: {str(e)}', 'danger')
        return render_template('admin_edit_supplier.html', action='Add', supplier=request.form if request.method == 'POST' else None)
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in admin_add_supplier: {e_close}")

@app.route('/admin/suppliers/edit/<int:supplier_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_supplier(supplier_id):
    cur = None
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            contact_person = request.form.get('contact_person')
            email = request.form.get('email')
            phone = request.form.get('phone')
            vehicle_number = request.form.get('vehicle_number')
            supply_type = request.form.get('supply_type')
            assigned_orders = request.form.get('assigned_orders', 0)
            is_active = 'is_active' in request.form

            if not all([name, contact_person, email, phone, vehicle_number, supply_type]):
                flash('Required fields are missing.', 'danger')
                cur_data = mysql.connection.cursor(cursorclass=DictCursor)
                cur_data.execute("SELECT * FROM Supplier WHERE supplier_id = %s", (supplier_id,))
                supplier = cur_data.fetchone()
                cur_data.close()
                return render_template('admin_edit_supplier.html', action='Edit', supplier=supplier, supplier_id=supplier_id), 400

            cur = mysql.connection.cursor()
            cur.execute("""
                UPDATE Supplier SET name=%s, contact_person=%s, email=%s, phone=%s, 
                       vehicle_number=%s, supply_type=%s, assigned_orders=%s, is_active=%s
                WHERE supplier_id=%s
            """, (name, contact_person, email, phone, vehicle_number, supply_type, int(assigned_orders), is_active, supplier_id))
            mysql.connection.commit()
            flash(f'Supplier {name} updated successfully.', 'success')
            return redirect(url_for('admin_list_suppliers'))

        # GET request: Show edit form
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("SELECT * FROM Supplier WHERE supplier_id = %s", (supplier_id,))
        supplier = cur.fetchone()
        # It is important to close this cursor if it's not the one being managed by the outer try/finally for POST
        if cur: cur.close() # Closed here as it's specific to GET

        if not supplier:
            flash('Supplier not found.', 'danger')
            return redirect(url_for('admin_list_suppliers'))
        return render_template('admin_edit_supplier.html', action='Edit', supplier=supplier, supplier_id=supplier_id)

    except Exception as e:
        # Ensure cur for POST is rolled back, GET request cur is already closed or never opened for POST error path.
        if request.method == 'POST' and cur: mysql.connection.rollback()
        logging.error(f"Error editing supplier {supplier_id}: {e}")
        flash(f'Error editing supplier: {str(e)}', 'danger')
        supplier_for_template = None
        # If error during POST, or GET failed to find supplier initially
        if request.method == 'POST' or not supplier: # Try to refetch for form if POST failed or GET had issues
            try:
                cur_err = mysql.connection.cursor(cursorclass=DictCursor)
                cur_err.execute("SELECT * FROM Supplier WHERE supplier_id = %s", (supplier_id,))
                supplier_for_template = cur_err.fetchone()
                cur_err.close()
            except Exception as e_data:
                logging.error(f"Error fetching data for edit supplier form after main error: {e_data}")

        return render_template('admin_edit_supplier.html', action='Edit', supplier=supplier_for_template or (request.form if request.method == 'POST' else None) , supplier_id=supplier_id)
    finally:
        # This finally block primarily ensures the cursor from a POST request is closed.
        # Cursors for GET or error-path re-fetches should be closed within their respective blocks.
        if request.method == 'POST' and cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing POST cursor in admin_edit_supplier: {e_close}")

@app.route('/admin/suppliers/toggle_active/<int:supplier_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_supplier_active(supplier_id):
    cur = None
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("SELECT is_active FROM Supplier WHERE supplier_id = %s", (supplier_id,))
        supplier = cur.fetchone()
        if not supplier:
            flash('Supplier not found.', 'danger')
            return redirect(url_for('admin_list_suppliers'))

        new_status = not supplier['is_active']
        cur.execute("UPDATE Supplier SET is_active = %s WHERE supplier_id = %s", (new_status, supplier_id))
        mysql.connection.commit()
        flash(f'Supplier status changed to {"Active" if new_status else "Inactive"}.', 'success')
    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error toggling supplier active status for {supplier_id}: {e}")
        flash(f'Error changing supplier status: {str(e)}', 'danger')
    finally:
        if cur: cur.close()
    return redirect(url_for('admin_list_suppliers'))

# --- Coupon Management (Admin) ---
@app.route('/admin/coupons', methods=['GET'])
@login_required
@admin_required
def admin_list_coupons():
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        # Fetch restaurant names and customer names for better display if IDs are present
        cur.execute("""
            SELECT c.*, r.name as restaurant_name, cust.Full_name as customer_name
            FROM Coupons c
            LEFT JOIN Restaurants r ON c.restaurant_id = r.restaurant_id
            LEFT JOIN Customers cust ON c.customer_id = cust.customer_id
            ORDER BY c.coupon_id DESC
        """)
        coupons = cur.fetchall()
        cur.close()
        return render_template('admin_coupon_list.html', coupons=coupons)
    except Exception as e:
        logging.error(f"Error fetching coupon list: {e}")
        flash('Could not load coupon list.', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/coupons/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_coupon():
    cur = None
    cur_options = None
    try:
        if request.method == 'POST':
            coupon_code = request.form.get('coupon_code')
            description = request.form.get('description')
            discount_percent = request.form.get('discount_percent')
            max_discount = request.form.get('max_discount')
            valid_from = request.form.get('valid_from')
            valid_to = request.form.get('valid_to')
            min_order_amount = request.form.get('min_order_amount')
            usage_limit = request.form.get('usage_limit')
            restaurant_id_str = request.form.get('restaurant_id')
            customer_id_str = request.form.get('customer_id')

            # --- Fetch restaurants and customers for form repopulation (needed for all POST error paths) ---
            cur_options = mysql.connection.cursor(cursorclass=DictCursor)
            cur_options.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
            restaurants_for_template = cur_options.fetchall()
            cur_options.execute("SELECT customer_id, Full_name FROM Customers ORDER BY Full_name")
            customers_for_template = cur_options.fetchall()
            # cur_options will be closed in finally

            if not all([coupon_code, discount_percent, max_discount, valid_from, valid_to, min_order_amount, usage_limit]):
                flash('All fields marked * are required.', 'danger')
                return render_template('admin_edit_coupon.html', action='Add', coupon=request.form, restaurants=restaurants_for_template, customers=customers_for_template), 400

            # --- Check for duplicate coupon code ---
            cur = mysql.connection.cursor()
            cur.execute("SELECT coupon_id FROM Coupons WHERE coupon_code = %s", (coupon_code,))
            if cur.fetchone():
                flash(f'Coupon code "{coupon_code}" already exists.', 'danger')
                # cur can be closed here or let finally handle it, for now let finally do it.
                return render_template('admin_edit_coupon.html', action='Add', coupon=request.form, restaurants=restaurants_for_template, customers=customers_for_template), 400
            # cur is still open for the INSERT if no duplicate

            db_restaurant_id = int(restaurant_id_str) if restaurant_id_str else None
            db_customer_id = int(customer_id_str) if customer_id_str else None
            
            cur.execute("SELECT MAX(coupon_id) FROM Coupons")
            max_id_result = cur.fetchone()
            next_coupon_id = (max_id_result[0] + 1) if max_id_result and max_id_result[0] is not None else 1
            
            cur.execute("""
                INSERT INTO Coupons (coupon_id, coupon_code, description, discount_percent, max_discount, 
                                  valid_from, valid_to, min_order_amount, usage_limit, times_used, 
                                  restaurant_id, customer_id, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (next_coupon_id, coupon_code, description, float(discount_percent), float(max_discount),
                  valid_from, valid_to, float(min_order_amount), int(usage_limit), 0, 
                  db_restaurant_id, db_customer_id, True))
            mysql.connection.commit()
            flash(f'Coupon "{coupon_code}" added successfully.', 'success') # Re-added success flash message
            return redirect(url_for('admin_list_coupons'))

        # --- GET request ---
        cur_options = mysql.connection.cursor(cursorclass=DictCursor)
        cur_options.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
        restaurants = cur_options.fetchall()
        cur_options.execute("SELECT customer_id, Full_name FROM Customers ORDER BY Full_name")
        customers = cur_options.fetchall()
        # cur_options will be closed in finally
        return render_template('admin_edit_coupon.html', action='Add', restaurants=restaurants, customers=customers, coupon={}) # Pass empty dict for coupon on GET

    except Exception as e:
        if cur: mysql.connection.rollback() # Rollback only if cur was used for INSERT/UPDATE
        logging.error(f"Error adding coupon: {e}") # Original exception (e.g., DB error other than duplicate)
        flash(f'Error adding coupon: {str(e)}', 'danger')
        
        # --- Re-fetch options if not already fetched (e.g., if error happened before options fetch in POST) ---
        # This is a bit redundant if error is after options fetch, but ensures they are always available
        restaurants_for_template_err, customers_for_template_err = [], []
        if not cur_options or cur_options.closed: # Check if cur_options is None or already closed
             # Defensively create a new cursor if cur_options is not usable
            cur_options_err_fetch = None
            try:
                cur_options_err_fetch = mysql.connection.cursor(cursorclass=DictCursor)
                cur_options_err_fetch.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
                restaurants_for_template_err = cur_options_err_fetch.fetchall()
                cur_options_err_fetch.execute("SELECT customer_id, Full_name FROM Customers ORDER BY Full_name")
                customers_for_template_err = cur_options_err_fetch.fetchall()
            except Exception as e_opts_fetch:
                logging.error(f"Critical error fetching options for add coupon form after main error: {e_opts_fetch}")
            finally:
                if cur_options_err_fetch:
                    try: cur_options_err_fetch.close()
                    except: pass # Ignore close error
        else: # cur_options was opened and potentially used (e.g. in POST before failure)
            # Attempt to reuse if possible, or re-fetch if needed. For simplicity, let's assume it was populated.
            # This path is tricky; the earlier fetch of restaurants_for_template/customers_for_template would be used
            # But to be absolutely safe, we could re-assign them here from the already fetched versions
            # if they were indeed fetched before the error. The current structure is okay if options are always fetched before error.
            # The key is that render_template gets valid lists.
            # The initial options fetch for POST is now outside the main try block for the INSERT logic.
            # So, restaurants_for_template and customers_for_template SHOULD be populated if it was a POST request.
             pass


        # For rendering on error, ensure coupon data is from request.form
        # If it's a GET request error (unlikely here but for robustness), coupon_data would be an empty dict.
        coupon_data_for_template = request.form if request.method == 'POST' else {}
        
        # Use the options fetched at the start of POST or in this except block
        r_template = restaurants_for_template if request.method == 'POST' and 'restaurants_for_template' in locals() else restaurants_for_template_err
        c_template = customers_for_template if request.method == 'POST' and 'customers_for_template' in locals() else customers_for_template_err

        return render_template('admin_edit_coupon.html', action='Add', coupon=coupon_data_for_template, restaurants=r_template, customers=c_template)
    finally:
        if cur: # Main DB operation cursor
            try: cur.close()
            except: pass # Ignore close error
        if cur_options: # Cursor for fetching dropdown options
            try: cur_options.close()
            except: pass # Ignore close error

@app.route('/admin/coupons/edit/<int:coupon_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_coupon(coupon_id):
    cur = None
    try:
        if request.method == 'POST':
            coupon_code = request.form.get('coupon_code')
            description = request.form.get('description')
            discount_percent = request.form.get('discount_percent')
            max_discount = request.form.get('max_discount')
            valid_from = request.form.get('valid_from')
            valid_to = request.form.get('valid_to')
            min_order_amount = request.form.get('min_order_amount')
            usage_limit = request.form.get('usage_limit')
            # times_used is not typically edited directly by admin here
            restaurant_id = request.form.get('restaurant_id')
            customer_id = request.form.get('customer_id')
            is_active = 'is_active' in request.form

            if not all([coupon_code, discount_percent, max_discount, valid_from, valid_to, min_order_amount, usage_limit]):
                flash('All fields marked with * are required.', 'danger')
                # Re-fetch data for the form if validation fails
                cur_data = mysql.connection.cursor(cursorclass=DictCursor)
                # Fetch existing coupon data for repopulation, not request.form directly for the coupon object
                cur_data.execute("SELECT * FROM Coupons WHERE coupon_id = %s", (coupon_id,))
                coupon_for_form = cur_data.fetchone() # This will be the coupon object
                
                cur_data.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
                restaurants_for_form = cur_data.fetchall()
                cur_data.execute("SELECT customer_id, Full_name FROM Customers ORDER BY Full_name")
                customers_for_form = cur_data.fetchall()
                cur_data.close()
                return render_template('admin_edit_coupon.html', action='Edit', coupon=coupon_for_form, restaurants=restaurants_for_form, customers=customers_for_form, coupon_id=coupon_id), 400
            
            # Define db_restaurant_id and db_customer_id from form data
            restaurant_id_str = request.form.get('restaurant_id')
            customer_id_str = request.form.get('customer_id') # Already have customer_id from form, this re-gets it for clarity.
            db_restaurant_id = int(restaurant_id_str) if restaurant_id_str else None
            db_customer_id = int(customer_id_str) if customer_id_str else None

            cur = mysql.connection.cursor()
            cur.execute("""
                UPDATE Coupons SET coupon_code=%s, description=%s, discount_percent=%s, max_discount=%s, 
                               valid_from=%s, valid_to=%s, min_order_amount=%s, usage_limit=%s, 
                               restaurant_id=%s, customer_id=%s, is_active=%s
                WHERE coupon_id=%s
            """, (coupon_code, description, float(discount_percent), float(max_discount), 
                  valid_from, valid_to, float(min_order_amount), int(usage_limit), 
                  db_restaurant_id, db_customer_id, is_active, coupon_id))
            mysql.connection.commit()
            flash(f'Coupon "{coupon_code}" updated successfully.', 'success')
            return redirect(url_for('admin_list_coupons'))

        # GET request
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("SELECT * FROM Coupons WHERE coupon_id = %s", (coupon_id,))
        coupon = cur.fetchone()
        # Fetch restaurants and customers for the dropdowns
        cur.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
        restaurants = cur.fetchall()
        cur.execute("SELECT customer_id, Full_name FROM Customers ORDER BY Full_name")
        customers = cur.fetchall()
        cur.close() # Close cursor after all fetches for this block

        if not coupon:
            flash('Coupon not found.', 'danger')
            return redirect(url_for('admin_list_coupons'))
        return render_template('admin_edit_coupon.html', action='Edit', coupon=coupon, restaurants=restaurants, customers=customers, coupon_id=coupon_id)

    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error editing coupon {coupon_id}: {e}")
        flash(f'Error editing coupon: {str(e)}', 'danger')
        coupon_for_template = None
        restaurants_for_template, customers_for_template = [], []
        # Attempt to fetch data again for the form render on error
        try:
            cur_err = mysql.connection.cursor(cursorclass=DictCursor)
            cur_err.execute("SELECT * FROM Coupons WHERE coupon_id = %s", (coupon_id,))
            coupon_for_template = cur_err.fetchone()
            cur_err.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
            restaurants_for_template = cur_err.fetchall()
            cur_err.execute("SELECT customer_id, Full_name FROM Customers ORDER BY Full_name")
            customers_for_template = cur_err.fetchall()
            cur_err.close()
        except Exception as e_data:
            logging.error(f"Error fetching data for edit coupon form after main error: {e_data}")
        return render_template('admin_edit_coupon.html', action='Edit', coupon=coupon_for_template or request.form, restaurants=restaurants_for_template, customers=customers_for_template, coupon_id=coupon_id)
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in admin_edit_coupon: {e_close}")

@app.route('/admin/coupons/toggle_active/<int:coupon_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_coupon_active(coupon_id):
    cur = None
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("SELECT is_active FROM Coupons WHERE coupon_id = %s", (coupon_id,))
        coupon = cur.fetchone()
        if not coupon:
            flash('Coupon not found.', 'danger')
            return redirect(url_for('admin_list_coupons'))

        new_status = not coupon['is_active']
        cur.execute("UPDATE Coupons SET is_active = %s WHERE coupon_id = %s", (new_status, coupon_id))
        mysql.connection.commit()
        flash(f'Coupon status changed to {"Active" if new_status else "Inactive"}.', 'success')
    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error toggling coupon active status for {coupon_id}: {e}")
        flash(f'Error changing coupon status: {str(e)}', 'danger')
    finally:
        if cur: cur.close()
    return redirect(url_for('admin_list_coupons'))

@app.route('/api/place-order-submission', methods=['POST'], endpoint='api_place_order_submission')
@login_required
def api_place_order_submission():
    cur = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data.'}), 400

        customer_info = data.get('customerInfo') # Assuming this is pre-filled and disabled, thus somewhat trustworthy for address/phone
        items_from_client = data.get('items')
        restaurant_id = data.get('restaurantId')

        if not items_from_client or not isinstance(items_from_client, list) or not items_from_client:
            return jsonify({'error': 'Order items are missing or invalid.'}), 400
        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID is missing.'}), 400
        if not customer_info or not customer_info.get('address'): # Basic check for delivery address
             return jsonify({'error': 'Customer address is missing.'}), 400


        cur = mysql.connection.cursor(cursorclass=DictCursor)
        
        # Verify items and calculate total price from DB
        total_price = 0
        processed_items_for_db = []

        for item_data in items_from_client:
            menu_id = item_data.get('menu_id')
            quantity = item_data.get('quantity')
            if not menu_id or not isinstance(quantity, int) or quantity < 1:
                return jsonify({'error': f'Invalid data for menu item {menu_id}.'}), 400

            cur.execute("SELECT price, item_name FROM Menu WHERE menu_id = %s AND restaurant_id = %s AND is_available = TRUE", 
                        (menu_id, restaurant_id))
            menu_item_db = cur.fetchone()

            if not menu_item_db:
                return jsonify({'error': f'Menu item ID {menu_id} not found, not available, or does not belong to restaurant {restaurant_id}.'}), 400
            
            item_price_from_db = menu_item_db['price']
            total_price += item_price_from_db * quantity
            processed_items_for_db.append({
                'menu_id': menu_id,
                'quantity': quantity,
                'item_price_at_order': item_price_from_db,
                'item_name': menu_item_db['item_name'] # For potential use in notifications or order summary
            })

        if not processed_items_for_db: # Should not happen if items_from_client was not empty, but as a safeguard
             return jsonify({'error': 'No valid items to order.'}), 400

        # Create the order
        cur.execute("SELECT MAX(order_id) FROM Orders")
        max_order_id_result = cur.fetchone()
        next_order_id = (max_order_id_result['MAX(order_id)'] + 1) if max_order_id_result and max_order_id_result['MAX(order_id)'] is not None else 1

        # Delivery address comes from current_user, which should be reliable
        delivery_address = current_user.address
        if not delivery_address: # Fallback if current_user.address is somehow not set, though profile should enforce it
            delivery_address = customer_info.get('address', 'N/A')


        cur.execute("""
            INSERT INTO Orders (order_id, customer_id, restaurant_id, order_status, total_price, final_amount, delivery_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (next_order_id, current_user.id, restaurant_id, 'pending_payment', total_price, total_price, delivery_address))

        # Create order items
        for item in processed_items_for_db:
            cur.execute("SELECT MAX(order_item_id) FROM OrderItems") # Generate OrderItem ID
            max_oi_id_result = cur.fetchone()
            next_oi_id = (max_oi_id_result['MAX(order_item_id)'] + 1) if max_oi_id_result and max_oi_id_result['MAX(order_item_id)'] is not None else 1
            
            cur.execute("""
                INSERT INTO OrderItems (order_item_id, order_id, item_id, quantity, item_price_at_order)
                VALUES (%s, %s, %s, %s, %s)
            """, (next_oi_id, next_order_id, item['menu_id'], item['quantity'], item['item_price_at_order']))
        
        mysql.connection.commit()

        # Prepare response
        payment_selection_url = url_for('payment_selection', order_id=next_order_id, _external=True)
        
        return jsonify({
            'message': 'Order initiated successfully. Proceed to payment.',
            'orderId': next_order_id,
            'totalPrice': float(total_price), # Ensure float for JSON
            'redirectUrl': payment_selection_url
        }), 200

    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error in api_place_order_submission: {e}")
        # Log the full traceback for detailed debugging
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({'error': 'An internal server error occurred while placing the order.'}), 500
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in api_place_order_submission: {e_close}")

@app.route('/payment-selection/<int:order_id>', methods=['GET'])
@login_required
def payment_selection(order_id):
    cur = None
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        # Fetch order details to display on the payment selection page
        cur.execute("""
            SELECT o.order_id, o.total_price, o.final_amount, o.applied_coupon_id, o.discount_amount, 
                   c.Full_name as customer_name, r.name as restaurant_name
            FROM Orders o
            JOIN Customers c ON o.customer_id = c.customer_id
            JOIN Restaurants r ON o.restaurant_id = r.restaurant_id
            WHERE o.order_id = %s AND o.customer_id = %s
        """, (order_id, current_user.id))
        order_details = cur.fetchone()

        if not order_details:
            flash('Order not found or you do not have permission to view it.', 'danger')
            return redirect(url_for('index')) # Or perhaps 'trackOrder'

        # Fetch coupon code if a coupon was applied
        coupon_code = None
        if order_details['applied_coupon_id']:
            cur.execute("SELECT coupon_code FROM Coupons WHERE coupon_id = %s", (order_details['applied_coupon_id'],))
            coupon_data = cur.fetchone()
            if coupon_data:
                coupon_code = coupon_data['coupon_code']

        payment_methods_list = ['credit_card', 'debit_card', 'upi', 'cash_on_delivery'] # Define payment methods

        # For simplicity, we're directly rendering. Ideally, you might fetch OrderItems too for a full summary.
        return render_template('payment_selection.html', 
                               order=order_details, 
                               order_id=order_id, # Pass order_id explicitly for form actions
                               coupon_code=coupon_code,
                               payment_methods=payment_methods_list) # Pass payment_methods

    except Exception as e:
        logging.error(f"Error loading payment selection page for order {order_id}: {e}")
        flash('Could not load payment page. Please try again.', 'danger')
        return redirect(url_for('trackOrder')) # Redirect to a safe page
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in payment_selection: {e_close}")

@app.route('/apply-coupon/<int:order_id>', methods=['POST'])
@login_required
def apply_coupon(order_id):
    cur = None
    try:
        coupon_code = request.form.get('coupon_code')
        if not coupon_code:
            flash('Please enter a coupon code.', 'warning')
            return redirect(url_for('payment_selection', order_id=order_id))

        cur = mysql.connection.cursor(cursorclass=DictCursor)

        # Fetch order details
        cur.execute("SELECT * FROM Orders WHERE order_id = %s AND customer_id = %s", (order_id, current_user.id))
        order = cur.fetchone()

        if not order:
            flash('Order not found.', 'danger')
            return redirect(url_for('index')) # Or a more appropriate error page/redirect

        if order['order_status'] != 'pending_payment':
            flash('Coupon can only be applied to orders pending payment.', 'warning')
            return redirect(url_for('payment_selection', order_id=order_id))

        # Fetch coupon details
        cur.execute("""
            SELECT * FROM Coupons 
            WHERE coupon_code = %s AND is_active = TRUE 
            AND valid_from <= NOW() AND valid_to >= NOW()
            AND times_used < usage_limit
        """, (coupon_code,))
        coupon = cur.fetchone()

        if not coupon:
            flash('Invalid or expired coupon code.', 'danger')
            return redirect(url_for('payment_selection', order_id=order_id))

        # Check restaurant/customer specific coupons (if applicable)
        if coupon['restaurant_id'] and coupon['restaurant_id'] != order['restaurant_id']:
            flash('This coupon is not valid for this restaurant.', 'warning')
            return redirect(url_for('payment_selection', order_id=order_id))
        
        if coupon['customer_id'] and coupon['customer_id'] != order['customer_id']:
            flash('This coupon is not valid for your account.', 'warning')
            return redirect(url_for('payment_selection', order_id=order_id))

        # Check minimum order amount
        order_total_for_coupon_check = order['total_price'] # Use original total_price for min_order_amount check
        if order_total_for_coupon_check < coupon['min_order_amount']:
            flash(f"Minimum order amount of {coupon['min_order_amount']} not met for this coupon.", 'warning')
            return redirect(url_for('payment_selection', order_id=order_id))

        # Calculate discount
        discount_amount = (order_total_for_coupon_check * coupon['discount_percent']) / 100
        if discount_amount > coupon['max_discount']:
            discount_amount = coupon['max_discount']
        
        final_amount = order_total_for_coupon_check - discount_amount
        if final_amount < 0: # Ensure final amount is not negative
            final_amount = 0 

        # Update order
        cur.execute("""
            UPDATE Orders 
            SET applied_coupon_id = %s, discount_amount = %s, final_amount = %s
            WHERE order_id = %s
        """, (coupon['coupon_id'], discount_amount, final_amount, order_id))

        # Increment coupon usage
        cur.execute("UPDATE Coupons SET times_used = times_used + 1 WHERE coupon_id = %s", (coupon['coupon_id'],))
        
        mysql.connection.commit()
        flash('Coupon applied successfully!', 'success')

    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error applying coupon for order {order_id}: {e}")
        flash('An error occurred while applying the coupon.', 'danger')
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in apply_coupon: {e_close}")
        
    return redirect(url_for('payment_selection', order_id=order_id))

@app.route('/process-payment/<int:order_id>', methods=['POST'])
@login_required
def process_payment(order_id):
    cur = None
    try:
        payment_method = request.form.get('payment_method')
        if not payment_method:
            flash('Please select a payment method.', 'warning')
            return redirect(url_for('payment_selection', order_id=order_id))

        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("SELECT * FROM Orders WHERE order_id = %s AND customer_id = %s AND order_status = 'pending_payment'", 
                    (order_id, current_user.id))
        order = cur.fetchone()

        if not order:
            flash('Order not found or not in a payable state.', 'danger')
            return redirect(url_for('trackOrder'))

        # Simulate payment processing
        # In a real app, integrate with a payment gateway here
        payment_successful = True # Assume success for simulation

        if payment_successful:
            # Create Payment record
            cur.execute("SELECT MAX(payment_id) FROM Payment")
            max_payment_id_result = cur.fetchone()
            next_payment_id = (max_payment_id_result['MAX(payment_id)'] + 1) if max_payment_id_result and max_payment_id_result['MAX(payment_id)'] is not None else 1

            cur.execute("""
                INSERT INTO Payment (payment_id, order_id, payment_method, payment_status, amount, transaction_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (next_payment_id, order_id, payment_method, 'completed', order['final_amount'], f'SIM_TXN_{next_payment_id}_{order_id}'))

            # Update Order status
            new_order_status = 'cash_on_delivery' if payment_method == 'cash_on_delivery' else 'placed'
            cur.execute("UPDATE Orders SET order_status = %s WHERE order_id = %s", (new_order_status, order_id))
            
            mysql.connection.commit()

            # Create notification
            create_notification(
                user_id=current_user.id, 
                type='order_status', 
                message=f'Your order #{order_id} has been successfully placed and payment confirmed via {payment_method.replace("_", " ").title()}.',
                related_order_id=order_id
            )

            # flash('Payment successful! Your order has been placed.', 'success') # Removed flash
            # Redirect with a query parameter to indicate success
            return redirect(url_for('order_confirmation', order_id=order_id, payment_status='success'))
        else:
            # Update Payment record (if one was created in a pending state earlier)
            # For this simulation, we'll just assume a direct failure if not successful
            cur.execute("SELECT MAX(payment_id) FROM Payment")
            max_payment_id_result = cur.fetchone()
            next_payment_id = (max_payment_id_result['MAX(payment_id)'] + 1) if max_payment_id_result and max_payment_id_result['MAX(payment_id)'] is not None else 1
            
            cur.execute("""
                INSERT INTO Payment (payment_id, order_id, payment_method, payment_status, amount, transaction_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (next_payment_id, order_id, payment_method, 'failed', order['final_amount'], f'FAIL_SIM_TXN_{next_payment_id}_{order_id}'))
            mysql.connection.commit() # Commit the failed payment attempt

            flash('Payment failed. Please try again or choose a different payment method.', 'danger')
            return redirect(url_for('payment_selection', order_id=order_id))

    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error processing payment for order {order_id}: {e}")
        flash('An error occurred during payment processing.', 'danger')
        return redirect(url_for('payment_selection', order_id=order_id))
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in process_payment: {e_close}")

@app.route('/order-confirmation/<int:order_id>', methods=['GET'])
@login_required
def order_confirmation(order_id):
    cur = None
    payment_success_message = None # Initialize to None
    try:
        # Check for payment success status from query parameter
        payment_status_query = request.args.get('payment_status')
        if payment_status_query == 'success':
            payment_success_message = "Payment successful! Your order has been placed."

        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("""
            SELECT o.order_id, o.final_amount, o.order_status, o.delivery_address, 
                   r.name as restaurant_name, GROUP_CONCAT(oi.quantity, ' x ', m.item_name SEPARATOR '; ') as item_summary
            FROM Orders o
            JOIN Restaurants r ON o.restaurant_id = r.restaurant_id
            JOIN OrderItems oi ON o.order_id = oi.order_id
            JOIN Menu m ON oi.item_id = m.menu_id
            WHERE o.order_id = %s AND o.customer_id = %s
            GROUP BY o.order_id, o.final_amount, o.order_status, o.delivery_address, r.name
        """, (order_id, current_user.id))
        order = cur.fetchone()

        if not order:
            flash('Order details not found.', 'danger')
            return redirect(url_for('index'))

        return render_template('order_confirmation.html', order=order, payment_success_message=payment_success_message)
    except Exception as e:
        logging.error(f"Error loading order confirmation for order {order_id}: {e}")
        flash('Could not load order confirmation. Please check your order history.', 'danger')
        return redirect(url_for('trackOrder')) # Or 'index'
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in order_confirmation: {e_close}")

# --- Route to get restaurants with their categorized menus ---
@app.route('/getRestaurantsWithMenus', methods=['GET'])
def get_restaurants_with_menus():
    cur = None
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        
        # Fetch active restaurants
        cur.execute("SELECT restaurant_id, name FROM Restaurants WHERE is_active = TRUE ORDER BY name")
        restaurants_data = cur.fetchall()
        
        response_data = []
        
        for restaurant in restaurants_data:
            restaurant_id = restaurant['restaurant_id']
            restaurant_info = {
                'restaurant_id': restaurant_id,
                'name': restaurant['name'],
                'menus': [] # This will hold categorized menus
            }
            
            # Fetch available menu items for the current restaurant, ordered by category then item name
            cur.execute("""
                SELECT menu_id, item_name, price, category, description, preparation_time
                FROM Menu 
                WHERE restaurant_id = %s AND is_available = TRUE
                ORDER BY category, item_name
            """, (restaurant_id,))
            menu_items_for_restaurant = cur.fetchall()
            
            # Group menu items by category
            categorized_menus = {}
            for item in menu_items_for_restaurant:
                category_name = item['category']
                if category_name not in categorized_menus:
                    categorized_menus[category_name] = {
                        'category': category_name,
                        'items': []
                    }
                # Convert decimal to string for JSON
                item_price = str(item['price']) if item['price'] is not None else '0.00'
                categorized_menus[category_name]['items'].append({
                    'menu_id': item['menu_id'],
                    'item_name': item['item_name'],
                    'price': item_price,
                    'description': item['description'],
                    'preparation_time': item['preparation_time']
                })
            
            restaurant_info['menus'] = list(categorized_menus.values()) # Convert dict values to list
            response_data.append(restaurant_info)
            
        return jsonify(response_data)
        
    except Exception as e:
        logging.error(f"Error fetching restaurants with menus: {e}")
        return jsonify({'error': str(e), 'message': 'Failed to load restaurant menu data from server.'}), 500
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in get_restaurants_with_menus: {e_close}")

# --- Notification Helper ---
def create_notification(user_id, type, message, related_order_id=None, channel='app'):
    cur = None
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor) # Use DictCursor for fetching MAX id
        cur.execute("SELECT MAX(notification_id) FROM Notifications")
        max_id_result = cur.fetchone()
        next_notification_id = (max_id_result['MAX(notification_id)'] + 1) if max_id_result and max_id_result['MAX(notification_id)'] is not None else 1

        # Switch to a standard cursor for the INSERT if DictCursor causes issues, 
        # or ensure INSERT statement column order matches table definition if not specifying columns.
        # For now, assuming DictCursor is fine for execute if parameter types are correct.
        cur.execute("""
            INSERT INTO Notifications (notification_id, user_id, type, message, related_order_id, channel, sent_time, is_read)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), FALSE)
        """, (next_notification_id, user_id, type, message, related_order_id, channel))
        mysql.connection.commit()
        logging.info(f"Notification created for user {user_id} with ID {next_notification_id}: {message[:50]}...")
    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error creating notification for user {user_id}: {e}")
        # Log traceback for more details on the error
        import traceback
        logging.error(traceback.format_exc())
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in create_notification: {e_close}")

# --- Notification API Endpoints ---
@app.route('/api/notifications', methods=['GET'], endpoint='api_get_notifications')
@login_required
def api_get_notifications():
    cur = None
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        cur.execute("""
            SELECT notification_id, type, message, sent_time, is_read, related_order_id, channel
            FROM Notifications
            WHERE user_id = %s
            ORDER BY is_read ASC, sent_time DESC
            LIMIT 20 
        """, (current_user.id,))
        notifications = cur.fetchall()
        
        for notification in notifications:
            if isinstance(notification['sent_time'], datetime):
                notification['sent_time'] = notification['sent_time'].isoformat()

        return jsonify(notifications)
    except Exception as e:
        logging.error(f"Error fetching notifications for user {current_user.id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in api_get_notifications: {e_close}")

@app.route('/api/notifications/mark-read', methods=['POST'], endpoint='api_mark_notifications_read')
@login_required
def api_mark_notifications_read():
    cur = None
    try:
        data = request.get_json()
        notification_ids = data.get('ids')

        if not notification_ids or not isinstance(notification_ids, list):
            return jsonify({'error': 'Invalid or missing notification IDs.'}), 400
        
        if not notification_ids:
            return jsonify({'message': 'No notifications to mark as read.'}), 200

        safe_notification_ids = [int(id_val) for id_val in notification_ids]
        
        placeholders = ','.join(['%s'] * len(safe_notification_ids))
        query = f"""
            UPDATE Notifications
            SET is_read = TRUE
            WHERE user_id = %s AND notification_id IN ({placeholders})
        """
        
        params = [current_user.id] + safe_notification_ids
        
        cur = mysql.connection.cursor()
        cur.execute(query, tuple(params))
        mysql.connection.commit()
        
        return jsonify({'message': f'{cur.rowcount} notification(s) marked as read.'}), 200
    except ValueError:
        return jsonify({'error': 'Invalid notification ID format.'}), 400
    except Exception as e:
        if cur: mysql.connection.rollback()
        logging.error(f"Error marking notifications as read for user {current_user.id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in api_mark_notifications_read: {e_close}")

# --- API Endpoint for Order Tracking ---
@app.route('/api/trackOrder/<int:order_id>', methods=['GET'])
@login_required
def api_track_order_details(order_id):
    cur = None
    try:
        cur = mysql.connection.cursor(cursorclass=DictCursor)
        
        # Fetch basic order details and customer ID first
        cur.execute("SELECT customer_id, restaurant_id, order_status, order_placed_time, final_amount AS totalPrice, delivery_address FROM Orders WHERE order_id = %s", (order_id,))
        order_base = cur.fetchone()

        if not order_base:
            return jsonify({'error': 'Order not found.'}), 404

        # Authorization check
        if not current_user.is_admin and order_base['customer_id'] != current_user.id:
            return jsonify({'error': 'Access denied. You can only track your own orders.'}), 403

        # Fetch restaurant name
        cur.execute("SELECT name FROM Restaurants WHERE restaurant_id = %s", (order_base['restaurant_id'],))
        restaurant_data = cur.fetchone()
        restaurant_name = restaurant_data['name'] if restaurant_data else "N/A"

        # Fetch order items
        cur.execute("""
            SELECT oi.quantity, m.item_name, oi.item_price_at_order AS price
            FROM OrderItems oi
            JOIN Menu m ON oi.item_id = m.menu_id
            WHERE oi.order_id = %s
        """, (order_id,))
        items_data = cur.fetchall()
        
        # Ensure 'price' is float for JSON compatibility, though it should be from DB already
        items_list = []
        for item in items_data:
            items_list.append({
                'itemName': item['item_name'],
                'quantity': item['quantity'],
                'price': float(item['price']) 
            })

        # Construct the response
        response_data = {
            'orderId': order_id,
            'restaurantName': restaurant_name,
            'deliveryAddress': order_base['delivery_address'],
            'placedTime': order_base['order_placed_time'].isoformat() if order_base['order_placed_time'] else None,
            'items': items_list,
            'totalPrice': float(order_base['totalPrice']),
            'status': order_base['order_status']
        }
        
        return jsonify(response_data), 200

    except Exception as e:
        logging.error(f"Error in api_track_order_details for order {order_id}: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({'error': 'An internal server error occurred.'}), 500
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in api_track_order_details: {e_close}")

# --- API Endpoint for Admin Review Management ---
@app.route('/api/admin/review/<int:review_id>', methods=['PUT'])
@login_required
@admin_required
def admin_update_review(review_id):
    cur = None
    try:
        data = request.get_json()
        new_comment = data.get('comment')

        if not new_comment:
            return jsonify({'error': 'Comment cannot be empty.'}), 400

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE Reviews
            SET comment = %s, is_edited = TRUE
            WHERE review_id = %s
        """, (new_comment, review_id))
        
        if cur.rowcount == 0:
            mysql.connection.rollback() # Rollback if no row was updated (review_id not found)
            return jsonify({'error': 'Review not found or no changes made.'}), 404
            
        mysql.connection.commit()
        logging.info(f"Admin {current_user.id} updated review {review_id}. New comment: {new_comment[:50]}...")
        return jsonify({'message': f'Review {review_id} updated successfully.'}), 200

    except Exception as e:
        if cur:
            mysql.connection.rollback()
        logging.error(f"Error updating review {review_id} by admin {current_user.id}: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({'error': 'An internal server error occurred while updating the review.'}), 500
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in admin_update_review: {e_close}")

@app.route('/api/admin/review/<int:review_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_review(review_id):
    cur = None
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM Reviews WHERE review_id = %s", (review_id,))
        
        if cur.rowcount == 0:
            mysql.connection.rollback() # Rollback if no row was deleted (review_id not found)
            return jsonify({'error': 'Review not found.'}), 404

        mysql.connection.commit()
        logging.info(f"Admin {current_user.id} deleted review {review_id}.")
        return jsonify({'message': f'Review {review_id} deleted successfully.'}), 200

    except Exception as e:
        if cur:
            mysql.connection.rollback()
        # Check for foreign key constraint violation if deletion is complex
        if "1451" in str(e) or "foreign key constraint" in str(e).lower():
             logging.error(f"Foreign key constraint error trying to delete review {review_id} by admin {current_user.id}: {e}")
             return jsonify({'error': 'Cannot delete review due to related data. This should not happen if ON DELETE CASCADE is set.'}), 409
        
        logging.error(f"Error deleting review {review_id} by admin {current_user.id}: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({'error': 'An internal server error occurred while deleting the review.'}), 500
    finally:
        if cur:
            try:
                cur.close()
            except Exception as e_close:
                logging.warning(f"Error closing cursor in admin_delete_review: {e_close}")

if __name__ == '__main__':
    app.run(debug=True)
