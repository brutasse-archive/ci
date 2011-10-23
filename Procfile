web: django-admin.py runserver --settings=ci.settings

celery: django-admin.py celeryd -l info --settings=ci.settings

compass: compass watch --force --no-line-comments --output-style compressed --require less --sass-dir $PROJECT/$APP/static/$APP/css --css-dir $PROJECT/$APP/static/$APP/css --image-dir /static/ $PROJECT/$APP/static/$APP/css/screen.scss
