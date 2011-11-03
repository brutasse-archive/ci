shell:
	django-admin.py shell --settings=ci.settings

run:
	foreman start

syncdb:
	django-admin.py syncdb  --settings=ci.settings --noinput

user:
	django-admin.py createsuperuser --settings=ci.settings

tests:
	django-admin.py test projects --settings=ci.test_settings --failfast

livetests:
	django-admin.py test livetests --settings=ci.test_settings --failfast
