from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import datetime
import os
from random import sample
import random


UPLOAD_FOLDER = 'static/uploads'  # Specify the folder where uploaded images will be saved

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Replace with a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # SQLite database to store user data
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Add the UPLOAD_FOLDER configuration
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    posts = db.relationship('Post', backref='user', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    caption = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@app.route('/')
def home():
    user_id = session.get('user_id')
    if user_id:
        # User is logged in, get the username from the database
        user = User.query.get(user_id)
        if not user:
            # If the user does not exist, log them out
            session.pop('user_id', None)
            flash('Your session has expired. Please log in again.', 'error')
            return redirect(url_for('login'))

        # Retrieve posts excluding the logged-in user's own posts
        other_users_posts = Post.query.filter(Post.user_id != user.id).all()
        return render_template('home.html', username=user.username, posts=other_users_posts)

    # Anonymous user, retrieve all posts and show them randomly
    all_posts = Post.query.all()
    random.shuffle(all_posts)  # Shuffle the posts randomly
    return render_template('home.html', username=None, posts=all_posts)


@app.route('/post/<int:post_id>')
def post_details(post_id):
    post = Post.query.get(post_id)
    if not post:
        flash('Post not found.', 'error')
        return redirect(url_for('home'))

    return render_template('post_details.html', post=post)



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        retype_password = request.form['retype_password']

        if not username or not password or not retype_password:
            flash('Username, password, and retype password are required.', 'error')
            return redirect(url_for('signup'))

        if password != retype_password:
            flash('Password and retype password do not match.', 'error')
            return redirect(url_for('signup'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('signup'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully. You can now log in!', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login(): 
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Logged in successfully.', 'success')
            return redirect(url_for('home'))  # Redirect to the home page after successful login
        else:
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')
@app.route('/account', methods=['GET', 'POST'])
def account():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST' and 'delete_account' in request.form:
        # Delete the user's account from the database
        db.session.delete(user)
        db.session.commit()

        # Logout the user by removing their session
        session.pop('user_id', None)
        flash('Your account has been deleted successfully.', 'success')
        return redirect(url_for('home'))  # Redirect to the home page after account deletion

    return render_template('account.html', username=user.username)






@app.route('/logout')
def logout():
    # Logout the user by removing their session
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))  # Redirect to the homepage (handles both logged-in and anonymous users)

@app.route('/my_post')
def my_posts():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))

    # Retrieve the posts created by the current user
    posts = Post.query.filter_by(user_id=user.id).all()

    return render_template('my_post.html', username=user.username, posts=posts)

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        caption = request.form['caption']
        image = request.files['image']

        if not title or not caption or not image:
            flash('Title, caption, and image are required.', 'error')
            return redirect(url_for('create_post'))

        # Ensure the UPLOAD_FOLDER exists; if not, create it
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        # Save the image to the UPLOAD_FOLDER
        image_filename = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + '_' + image.filename
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        new_post = Post(title=title, caption=caption, image=image_filename, user_id=user.id)
        db.session.add(new_post)
        db.session.commit()

        flash('Post created successfully.', 'success')
        return redirect(url_for('my_posts'))

    return render_template('create_post.html', username=user.username)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
