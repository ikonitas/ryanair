# -*- coding: utf-8 -*-
import datetime
import smtplib

from decimal import Decimal
from email.mime.text import MIMEText

import psycopg2
import scrapy

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.mail import MailSender
from xvfbwrapper import Xvfb

from .settings import RYANAIR_SETTINGS


class RyanairSpider(scrapy.spider.BaseSpider):
    """
    RyanAir spider to check price on website and send email about changes.

    Command to run:

    scrapy crawl ryanair
    """
    name = "ryanair"
    allowed_domains = ["ryanair.com", "www.bookryanair.com"]
    start_urls = [
        "http://www.ryanair.com",
    ]

    FROM_EMAIL = RYANAIR_SETTINGS.get('FROM_EMAIL')
    RECIPIENTS = RYANAIR_SETTINGS.get('RECIPIENTS')
    FAILURE_EMAIL = RYANAIR_SETTINGS.get('FAILURE_EMAIL')

    FLIGHT_FROM = {
        'AIRPORT_NAME': RYANAIR_SETTINGS['FLIGHT']['FROM'].get('AIRPORT_NAME'),
        'YEAR': RYANAIR_SETTINGS['FLIGHT']['FROM'].get('YEAR'),
        'MONTH': RYANAIR_SETTINGS['FLIGHT']['FROM'].get('MONTH'),
        'DATE': RYANAIR_SETTINGS['FLIGHT']['FROM'].get('DATE'),
    }
    FLIGHT_TO = {
        'AIRPORT_NAME': RYANAIR_SETTINGS['FLIGHT']['TO'].get('AIRPORT_NAME'),
        'YEAR': RYANAIR_SETTINGS['FLIGHT']['TO'].get('YEAR'),
        'MONTH': RYANAIR_SETTINGS['FLIGHT']['TO'].get('MONTH'),
        'DATE': RYANAIR_SETTINGS['FLIGHT']['TO'].get('DATE'),
    }
    FLIGHT_PERSONS = {
        'ADULTS_NO': RYANAIR_SETTINGS['FLIGHT'].get('ADULTS_NO', 1),
        'KIDS_NO': RYANAIR_SETTINGS['FLIGHT'].get('KIDS_NO', 0),
    }
    DATABASE = {
        'NAME': RYANAIR_SETTINGS['DATABASE'].get('NAME'),
        'USER': RYANAIR_SETTINGS['DATABASE'].get('USER'),
        'PASSWORD': RYANAIR_SETTINGS['DATABASE'].get('PASSWORD'),
    }

    def __init__(self, *args, **kwargs):
        """ Initialize headless firefox. """
        self.vdisplay = Xvfb()
        self.vdisplay.start()
        self.driver = webdriver.Firefox()

    def open_connection_to_database(self):
        """ Open connection to database. """
        connection = psycopg2.connect(
            'dbname=ryanair user={0} password={1}'.format(
                self.DATABASE['USER'],
                self.DATABASE['PASSWORD'],
            )
        )
        return connection

    def parse(self, response):

        self.create_database_table()

        # Settings window size as per github issue-#11637 phantomjs
        self.driver.set_window_size(1024, 768)

        self.driver.get(response.url)

        # Wait for 10 seconds till is loads.
        self.driver.implicitly_wait(10)

        # From airport input
        from_airport = self.driver.find_element_by_name('fromAirportName')

        # Requires click first to trigger adults selection
        from_airport.click()
        from_airport.clear()
        from_airport.send_keys(self.FLIGHT_FROM['AIRPORT_NAME'])

        # To airport input
        # Requires click first to trigger adults selection
        to_airport = self.driver.find_element_by_css_selector(
            'input[name="toAirportIATA"]'
        )
        to_airport.click()
        to_airport.send_keys(self.FLIGHT_TO['AIRPORT_NAME'])

        # Display extra options
        self.driver.execute_script(
            "document.getElementsByClassName('form-options')[0].style.display='block';"
        )
        # From date triggers a click to display dropdown
        from_data = self.driver.find_element_by_class_name(
            'datepicker-flight-from-trigger'
        )

        from_data.click()

        # Gets datepicker element dirty hack as click not always works
        while True:
            try:
                datepicker = self.driver.find_element_by_class_name(
                    'datepicker'
                )
            except:
                from_data = self.driver.find_element_by_class_name(
                    'datepicker-flight-from-trigger'
                )
                from_data.click()
            else:
                break

        # Check the month name
        month_element_from_text = datepicker.find_element_by_css_selector(
            '.datepicker-days .table-condensed .datepicker-switch'
        ).text

        while self.FLIGHT_FROM['MONTH'] not in month_element_from_text:
            datepicker.find_element_by_class_name('next').click()
            month_element_from_text = datepicker.find_element_by_css_selector(
                '.datepicker-days .table-condensed .datepicker-switch'
            ).text

        # Gets all days in calendar
        days_elements = datepicker.find_elements_by_class_name('day')

        # Loops through and triggers a click
        for day in days_elements:
            if "old" in day.get_attribute('class'):
                continue
            if day.text == self.FLIGHT_FROM['DATE']:
                day.click()
                break

        # To date triggers a click to display dropdown
        self.driver.find_element_by_class_name(
            'datepicker-flight-to-trigger'
        ).click()

        self.driver.implicitly_wait(40)

        # Gets datepicker element
        datepicker = self.driver.find_element_by_class_name('datepicker-days')

        # Check the month name
        month_element_to_text = datepicker.find_element_by_css_selector(
            '.datepicker-days .table-condensed .datepicker-switch'
        ).text

        while self.FLIGHT_TO['MONTH'] not in month_element_to_text:
            datepicker.find_element_by_class_name('next').click()
            month_element_to_text = datepicker.find_element_by_css_selector(
                '.datepicker-days .table-condensed .datepicker-switch'
            ).text

        # Gets all days in calendar
        days_elements = datepicker.find_elements_by_class_name('day')

        # Loops through and triggers a click
        for day in days_elements:
            if "old" in day.get_attribute('class'):
                continue
            if day.text == self.FLIGHT_TO['DATE']:
                day.click()
                break

        adult_elements = (
            self.driver.find_elements_by_class_name('adults-basic-item')
        )
        # Selecting two Adults
        for element in adult_elements:
            if element.text == str(self.FLIGHT_PERSONS['ADULTS_NO']):
                element.click()

        if self.FLIGHT_PERSONS['KIDS_NO']:
            # Triggers children dropdown
            self.driver.find_element_by_name('CHILD').click()

            # Selecting two childrens
            children_elements = (
                self.driver.find_elements_by_css_selector(
                    '.children .custom-dropdown-item'
                )
            )

            for element in children_elements:
                if element.text == str(self.FLIGHT_PERSONS['KIDS_NO']):
                    element.click()

        # Submit a form
        submit_button = self.driver.find_element_by_class_name(
            'submit-button-validation'
        )

        actions = ActionChains(self.driver)
        actions.move_to_element(submit_button).click(submit_button).perform()

        self.driver.implicitly_wait(60)

        # Gets total price
        price = self.driver.find_element_by_css_selector(
            '.prc.flr.ng-binding'
        ).text

        price = Decimal(price.strip('GBP'))

        self.save_to_database(price)

    def save_to_database(self, price):
        """ Saves price in database with dates. """

        date_from = datetime.datetime.strptime('{} {} {}'.format(
            self.FLIGHT_FROM['DATE'],
            self.FLIGHT_FROM['MONTH'],
            self.FLIGHT_FROM['YEAR'],
        ), "%d %B %Y")

        date_to = datetime.datetime.strptime('{} {} {}'.format(
            self.FLIGHT_TO['DATE'],
            self.FLIGHT_TO['MONTH'],
            self.FLIGHT_TO['YEAR'],
        ), "%d %B %Y")

        # Opens connection to database
        connection = self.open_connection_to_database()
        cursor = connection.cursor()

        # Get latest price
        cursor.execute(
            """SELECT price FROM prices WHERE date_from = %s AND date_to = %s
            ORDER BY id DESC LIMIT 1""", [date_from, date_to]
        )

        try:
            previous_price = cursor.fetchone()[0]
        except TypeError:
            previous_price = Decimal('0')

        # Email body text
        msg = MIMEText(
            """
            Current price: {} Previous price: {} \n
            Date form: {} Date to: {}
            """.format(
                price, previous_price, date_from.date(), date_to.date()
            )
        )
        recipients = self.RECIPIENTS
        msg['From'] = self.FROM_EMAIL
        msg['To'] = ", ".join(recipients)
        smtp = smtplib.SMTP('localhost')

        if previous_price > price:
            msg['Subject'] = "Price went down"
            smtp.sendmail(self.FROM_EMAIL, recipients, msg.as_string())
            smtp.quit()
        elif previous_price < price:
            msg['Subject'] = "Price went up"
            smtp.sendmail(self.FROM_EMAIL, recipients, msg.as_string())
            smtp.quit()

        cursor.execute(
            """INSERT INTO prices (
                airport_from, airport_to, price, date_created, date_from, date_to
            )
            VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                self.FLIGHT_FROM['AIRPORT_NAME'],
                self.FLIGHT_TO['AIRPORT_NAME'],
                price,
                datetime.datetime.now(),
                date_from,
                date_to
            )
        )
        # Commit changes.
        connection.commit()

        # Close connections
        cursor.close()
        connection.close()

        self.driver.quit()
        self.vdisplay.stop()

    def create_database_table(self):
        """ Create table prices if doesn't exist. """
        connection = self.open_connection_to_database()
        check_if_table_exists = """
            SELECT EXISTS (
            SELECT 1
            FROM   information_schema.tables
            WHERE  table_name = 'prices'
            );
        """
        cursor = connection.cursor()

        # Get latest price.
        cursor.execute(check_if_table_exists)
        results = cursor.fetchone()
        # Create table if doesn't exists.
        if not results[0]:
            cursor.execute(
                """
                CREATE TABLE prices
                (
                  id serial NOT NULL,
                  airport_from character varying(30) NOT NULL,
                  airport_to character varying(30) NOT NULL,
                  price numeric(12,2) NOT NULL,
                  date_created timestamp with time zone NOT NULL,
                  date_from date,
                  date_to date,
                  CONSTRAINT prices_pkey PRIMARY KEY (id)
                )
                WITH (
                  OIDS=FALSE
                );
                """
            )
            # Commit changes.
            connection.commit()

        # Close connections
        cursor.close()
        connection.close()

    def spider_error(failure):
        """Send errors email."""
        from_email = RYANAIR_SETTINGS['FROM_EMAIL']
        to_email = RYANAIR_SETTINGS['FAILURE_EMAIL']
        mailer = MailSender(mailfrom=from_email)
        mailer.send(
            to=[to_email],
            subject="Ryanair flights error",
            body=failure.getErrorMessage(),
        )
    dispatcher.connect(spider_error, signals.spider_error)
