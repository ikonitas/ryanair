=======
Ryanair
=======

Ryanair changes their filight prices few times a week. 

This spider checks for price on ryanair website and saves in database its sends email when price goes up or down.

Database: **Postgresql**


Install
~~~~~~~
Packages required on **Ubuntu**:

.. code-block:: bash

    $ apt-get install python-pip python-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev libpq-dev firefox


.. code-block:: bash
    
    $ pip install -r requirements.txt



Configuration
~~~~~~~~~~~~~
File to set your configuration is located in ``ryanair/spiders/settings.py``

You have to set following settings:

.. code-block:: bash


    RYANAIR_SETTINGS = {
        'RECIPIENTS': [],
        'FAILURE_EMAIL': [],
        'FROM_EMAIL': '',
    
        'DATABASE': {
            'NAME': '',
            'USER': '',
            'PASSWORD': '',
        },
        'FLIGH': {
            'FROM': {
                'AIRPORT_NAME': '',
                'YEAR': '',
                'MONTH': '',
                'DATE': '',
            },
            'TO': {
                'AIRPORT_NAME': '',
                'YEAR': '',
                'MONTH': '',
                'DATE': '',
            },
            'ADULTS_NO': '',
            'KIDS_NO': 0,
        },
    }

``RECIPIENTS`` - A list of strings, each an email address.

``FAILURE_EMAIL`` - All failures will be reported to this email address.


Run crawler
~~~~~~~~~~~

.. code-block:: bash

   $ scrapy crawl ryanair
    
