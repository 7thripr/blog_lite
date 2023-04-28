from app import db, loginmanager
from datetime import datetime
from flask_login import UserMixin


@loginmanager.user_loader
def load_user(user_id):
    return User.query.get(int (user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    profile_photo = db.Column(db.String(20), nullable=False, default='default_pp.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    follower_count = db.Column(db.Integer, default=0)
    blog_count = db.Column(db.Integer, default=0)
    followers = db.Column(db.String, default='')
    following = db.Column(db.String, default='')


    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.profile_photo}', '{self.follower_count}', '{self.blog_count}, '{self.followers})"

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email
        }

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', content='{self.content}', user_id='{self.user_id})"

