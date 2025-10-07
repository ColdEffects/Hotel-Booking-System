from flask import Flask, render_template, url_for, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    user_type = session.get('user_type')

    if user_type == 'staff':
        return Staff.query.get(int(user_id))
    elif user_type == 'customer':
        return Customer.query.get(int(user_id))

    # Fallback
    return None

class MakeRoom(db.Model):
    __tablename__ = 'makeroom'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    price_per_night = db.Column(db.Float, nullable=False)
    num_of_rooms = db.Column(db.Integer)
    adult_capacity = db.Column(db.Integer)
    child_capacity = db.Column(db.Integer)

    # Relationships
    rooms = db.relationship('Room', backref='makeroom', lazy=True)
    images = db.relationship('RoomImage', backref='makeroom', lazy=True)
    promos = db.relationship('Promo', backref='makeroom', lazy=True)


class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    makeroom_id = db.Column(db.Integer, db.ForeignKey('makeroom.id'), nullable=False)
    room_number = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='available')  # available, occupied

    # Relationships
    reservations = db.relationship('Reservation', backref='room', lazy=True)
    availability = db.relationship('RoomAvailability', backref='room', lazy=True)


class RoomAvailability(db.Model):
    __tablename__ = 'room_availability'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)  # specific day
    is_available = db.Column(db.Boolean, default=True)


class Promo(db.Model):
    __tablename__ = 'promo'
    id = db.Column(db.Integer, primary_key=True)
    makeroom_id = db.Column(db.Integer, db.ForeignKey('makeroom.id'))
    title = db.Column(db.String(50))
    description = db.Column(db.String(200))
    discount = db.Column(db.Float)
    date_start = db.Column(db.Date)
    date_end = db.Column(db.Date)


class RoomImage(db.Model):
    __tablename__ = 'room_images'
    id = db.Column(db.Integer, primary_key=True)
    makeroom_id = db.Column(db.Integer, db.ForeignKey('makeroom.id'))
    image_path = db.Column(db.String(200), nullable=False)
    is_thumbnail = db.Column(db.Boolean, default=False)




class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))
    check_in = db.Column(db.Date)
    check_out = db.Column(db.Date)
    payments = db.relationship('Payment', backref='reservation', lazy=True)


class Customer(UserMixin, db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    mobile_number = db.Column(db.String(20), unique=True)
    address = db.Column(db.String(200))
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    reservations = db.relationship('Reservation', backref='customer', lazy=True)
    reviews = db.relationship('Review', backref='customer', lazy=True)

class Payment(db.Model):
    __tablename__ = 'payments' 
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.id'))  # fixed
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))  # e.g., credit card
    transaction_id = db.Column(db.String(100))
    status = db.Column(db.String(20))  # success, failed, refunded

class Staff(UserMixin, db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200)) 
    role = db.Column(db.String(20))  # admin, receptionist

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    review_date = db.Column(db.DateTime, default=datetime.utcnow)

    
@app.route('/')
def index():
    return render_template("index.html")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        mobile_number = request.form['mobile_number']
        address = request.form['address']
        username = request.form['username']
        password = request.form['password']
        if Customer.query.filter_by(email=email).first() or Customer.query.filter_by(mobile_number=mobile_number).first() or Customer.query.filter_by(username=username).first():
            return 'Username, email or mobile_number already exists!'
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_customer = Customer(full_name=full_name, email=email, mobile_number=mobile_number, address=address, username=username, password=hashed_password)
        db.session.add(new_customer)
        db.session.commit()
        if current_user.is_authenticated:
            logout_user()
            session.clear()
        login_user(new_customer)
        return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username']
        password = request.form['password']

        # Check for customer
        customer = Customer.query.filter(
            (Customer.username == identifier) | (Customer.email == identifier)
        ).first()

        if customer and check_password_hash(customer.password, password):
            login_user(customer)
            session['user_type'] = 'customer'
            return redirect(url_for('dashboard'))

        # Check for staff
        staff = Staff.query.filter_by(username=identifier).first()
        if staff and check_password_hash(staff.password, password):
            login_user(staff)
            session['user_type'] = 'staff'
            # Redirect based on staff role
            if staff.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif staff.role == 'receptionist':
                return redirect(url_for('reception_dashboard'))
            else:
                return "Unknown staff role", 403
        return 'Invalid credentials!'
    return render_template('login.html')


@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return "Unauthorized", 403
    return render_template("admin_dashboard.html", hide_header=True, hide_footer=True)

@app.route('/receptionist_dashboard')
@login_required
def reception_dashboard():
    if not hasattr(current_user, 'role') or current_user.role != 'receptionist':
        return "Unauthorized", 403
    return render_template("receptionist_dashboard.html", hide_header=True, hide_footer=True)


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html", hide_header=True, hide_footer=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()  # 👈 clear user_type and everything else
    return redirect(url_for('login'))

@app.route('/gallery')
def gallery():
    return render_template("gallery.html")

@app.route('/about_us')
def about_us():
    return render_template("about_us.html")

@app.route('/forgot_password')
def forgot_password():
    return render_template("forgot_password.html")

@app.route('/book_now')
def book_now():
    return render_template("book_now.html")

@app.route('/rooms')
def rooms():
    return render_template("rooms.html")

@app.route('/add_room')
def add_room():
    return render_template("add_room.html")

@app.route('/make_room')
def make_room():
    return render_template("make_room.html")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)