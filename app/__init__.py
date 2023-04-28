from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_caching import Cache
from app.celery import make_celery
from flask_mail import Message, Mail
from celery.schedules import crontab
from pytz import timezone
from weasyprint import HTML
from jinja2 import Template


app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_URL': 'redis://localhost:6379/0'})
cache.init_app(app)
app.config['SECRET_KEY'] = '13041e5e95e6e69331e30c8f4e579162'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


loginmanager = LoginManager(app)
loginmanager.login_view = 'login'
loginmanager.login_message_category = 'info'

celery_app = make_celery(app)


app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'admin@gmail.com'
app.config['MAIL_PASSWORD'] = 'password'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_SUPPRESS_SEND'] = False
mail = Mail(app)


from pytz import timezone

@celery_app.task(name="send_email")
def monthly_task():
    user = User.query.filter_by(username=current_user.username).first()
    tz = timezone(user.timezone)  # assuming user.timezone is a valid timezone string
    msg = Message('Monthly Report',
                  sender='admin@gmail.com',
                  recipients=[user.email])
    msg.body = f"""
        Hello, {user.name}
        This is your monthly report.
        <a href="{url_for('download_csv')}"><button>Download</button></a>
        Regards,
        Admin
        """
    scheduled_time = crontab(hour=7, minute=0, day_of_week='*', day_of_month=1, month_of_year='*', timezone=tz.zone)
    msg.schedule = scheduled_time
    mail.send(msg)
    return "Monthly Report Sent"



from pytz import timezone

@celery_app.task(name="send_email")
def daily_task():
    user = User.query.filter_by(username=current_user.username).first()
    tz = timezone(user.timezone)
    msg = Message('Daily Report',
                  sender='admin@gmail.com',
                  recipients=[user.email])
    msg.body = f"""
        Hello, {user.name}
        This is your daily report.
        <a href="{url_for('download_csv')}"><button>Download</button></a>
        Regards,
        Admin
        """
    scheduled_time = crontab(hour=7, minute=0, day_of_week='*', day_of_month='*', month_of_year='*', 
                            timezone=tz.zone)
    msg.schedule = scheduled_time
    mail.send(msg)
    return "Daily Report Sent"


#api
from app.routes import *
