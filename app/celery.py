from celery import Celery
from flask_login import current_user


def make_celery(app):
    celery = Celery(app.import_name, 
                    broker="redis://localhost:6379/1", 
                    backend="redis://localhost:6379/2"
                    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery




