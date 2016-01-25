To deploy under mod_wsgi on Apache 2 

1. Install Apache 2.2
2. Install mod_wsgi
    1. On Ubuntu 14.04: sudo apt-get install libapache2-mod-wsgi-py3
3. Add the following to your Apache config:

```
<VirtualHost *:80>
    WSGIDaemonProcess morphgroup python-path=/installpath/MorphologyServiceAPI/venv/lib/python3.4/site-packages

    WSGIScriptAlias /svc /installpath/MorphologyServiceAPI/app.wsgi process-group=morphgroup

    <Directory /installpath/MorphologyServiceAPI>
       WSGIProcessGroup morphgroup
       Require all granted
    </Directory>
```


