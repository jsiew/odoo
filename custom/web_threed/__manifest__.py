# Copyright 2022 Openindustry.it SAS
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Web 3D View",
    "version": "16.0.2.0.0",
    "license": "AGPL-3",
    "summary": """
        Web 3D View enable to view pan and zoom an area (Model) in a 3d space with 3D rendered Items
    """,
    "category": "Web",
    "company": "https://openindustry.it",
    "author": "Openindustry.it,Tissino.it,Codingdodo.com",
    "maintainers": ["andreampiovesana"],
    "support": "andrea.m.piovesana@gmail.com",
    "website": "https://openindustry.it",
    "depends": [
        "web",
    ],
    "assets": {
        "web.assets_backend": [
            "web_threed/static/lib/three.min.js",
            "web_threed/static/lib/stats.min.js",
            "web_threed/static/lib/dat.gui.min.js",
            "web_threed/static/lib/OrbitControls.js",
            "web_threed/static/lib/GLTFLoader.js",
            "web_threed/static/src/js/utils/deep_equal.js",
            "web_threed/static/src/js/hooks/use_absolute_threed_popup.js",
            "web_threed/static/src/js/hooks/use_threed_scene.js",
            "web_threed/static/src/js/web_threed_controller.xml",
            "web_threed/static/src/js/web_threed_controller.js",
            "web_threed/static/src/js/web_threed_controller.scss",
            "web_threed/static/src/js/web_threed_model.js",
            "web_threed/static/src/js/web_threed_arch_parser.js",
            "web_threed/static/src/js/web_threed_renderer.js",
            "web_threed/static/src/js/web_threed_renderer.xml",
            "web_threed/static/src/js/web_threed_renderer.scss",
            "web_threed/static/src/js/web_threed_view.js",
        ],
    },
    "images": [
        "images/web_threed.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "price": 200.00,
    "currency": "EUR",
}
