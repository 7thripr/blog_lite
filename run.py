from app import app
from app import celery_app

celery = celery_app

if __name__ == '__main__':
    app.run(debug=True)
