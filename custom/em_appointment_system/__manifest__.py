# -*- coding: utf-8 -*-
{
    'name': "Appointment Management System",

    'summary': """Allows you to easily manage Appointments in your organization""",

    'description': """This app will save time and chaos for both appointee and customers. You can  Create multiple 
     appointees,  Create customers' appointments, send reminder mails to customers etc. 
     The module makes it easy to track and  manage each  meeting in your business.""",

    'author': "ErpMstar Solutions",
    'category': 'Management',
    'version': '1.1',

    # any module necessary for this one to work correctly
    'depends': ['sale_management', 'website', 'contacts'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/appointment_ir_sequence.xml',
        'data/appointment_mail_template.xml',
        'report/appointment_report_template.xml',
        'views/views.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': True,
    'live_test_url': 'https://youtu.be/jA7RRf14oak',
    'price': 50,
    'currency': 'EUR',
}
