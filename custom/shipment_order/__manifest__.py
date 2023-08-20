{

    'author': "MetaMind Technologies Pte. Ltd.",
    'category': 'Inventory',
    'version': '1.0',

    'name': 'Shipment Order',
    'version': '0.1',
    'category': 'Inventory',
    'summary': 'Manage Shipment Orders',
    'description': "",
    'website': 'http://www.metamind.tech',
    'depends': [
        'base',
        'stock'
    ],
    'data': [
        'views/stock_picking_views.xml',
        'views/stock_picking_type_views.xml',
        'views/stock_location_views.xml',
        'views/stock_storage_category_views.xml',
        'views/stock_move_views.xml',
        'views/stock_move_line_views.xml',
        'views/shipment_wizard_view.xml',
        'views/shipment_outbound_wizard_view.xml',
        'views/res_config_settings_views.xml',
        'views/shipment_order_views.xml',
        'security/ir.model.access.csv'
    ],
    'assets': {
        'web.assets_common': [
            'shipment_order/static/src/js/stock_picking_functions.js',
        ],
        'web.assets_backend': [
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': True,
}