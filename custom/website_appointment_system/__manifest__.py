# -*- coding: utf-8 -*-
{
    'name': "Online Appointment Booking System",

    'summary': """Allows clients to easily book Appointments from portal""",

    'description': """
        This app will save time and chaos for both appointee and customers. Now customers/clients can easily book an 
        appointment easily from your website portal. You can also Create multiple 
        appointees,  Create customers' appointments, send reminder mails to customers etc. 
        The module makes it easy to track and  manage each  meeting in your business.
    """,

    'author': "ErpMstar Solutions",
    'category': 'Management',
    'version': '1.1',

    # any module necessary for this one to work correctly
    'depends': ['em_appointment_system', 'website','account_payment'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',

        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [

    ],
    'assets': {
        'web.assets_frontend': [
            '/website_appointment_system/static/src/js/script.js',
            '/website_appointment_system/static/src/css/website_calendar.scss.css',

        ]
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'live_test_url': 'https://youtu.be/qv-JMIQAuBY',
    'price': 50,
    'currency': 'EUR',
}
