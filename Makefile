shell:
	django-admin.py shell --settings=ci.settings

run:
	foreman start

syncdb:
	django-admin.py syncdb  --settings=ci.settings --noinput

user:
	django-admin.py createsuperuser --settings=ci.settings
