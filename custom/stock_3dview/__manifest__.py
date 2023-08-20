# Copyright 2022 Openindustry.it SAS
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Stock 3D View",
    "version": "16.0.11.0.0",
    "license": "AGPL-3",
    "summary": """
        Stock 3D View Multi Warehouse enable to view pan and zoom multi warehouse locations in a 3d space
    """,
    "category": "Inventory",
    "company": "https://openindustry.it",
    "author": "Openindustry.it,Tissino.it",
    "maintainers": ["andreampiovesana"],
    "support": "andrea.m.piovesana@gmail.com",
    "website": "https://openindustry.it",
    "depends": [
        "stock_3dbase",
        "web_threed",
        "web",
    ],
    "data": [
        "views/stock_view.xml",
    ],
    "assets": {},
    "images": [
        "images/stock_3dview.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "price": 50.00,
    "currency": "EUR",
}
