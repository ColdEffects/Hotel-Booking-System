from app import app, db, Staff
from werkzeug.security import generate_password_hash

with app.app_context():
    # Create hashed password
    hashed_pw = generate_password_hash('123')

    # Create new staff instance
    staff = Staff(username='finn', password=hashed_pw, role='admin') #password: 123
    # staff = Staff(username='jake', password=hashed_pw, role='receptionist') #password: 123

    # Insert into database
    db.session.add(staff)
    db.session.commit()

    print("Staff inserted successfully!")
