
Overview of the ``<threed>`` View XML Architecture
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This view is composable with multiple elements that you should get familiar with. They will be described in detail in the following sections but for a global overview, this is what it looks like:

.. code-block:: xml

   <threed>
       <camera x="" y="" z="" fov="50" />
       <scene>
           <ground>
               <!-- field representing the ground surface -->
               <field name="my_related_model_id">
                   <!-- Planimetry data -->
                   <planimetry
                       name_field="name"
                       image_field="planimetry_image"
                       sizex_field="spacex"
                       sizey_field="spacey"
                       sizez_field="spacez"
                   >
                   </planimetry>
               </field>
           </ground>
           <objects>
               <!-- fields to include, ie:
               <field name="posx" type="position" axis="x" />
               -->
           </objects>
       </scene>
       <legend/>
       <templates>
           <!-- Here we have access to "record" containing the result of the server_action -->
           <t t-name="threedview-popup-info" server_action="get_3d_view_item_info">
               <!-- content -->
           </t>
       </templates>
   </threed>

The main encapsulating ``<threed>`` View element
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every 3D View is encapuslated by the ``<threed>`` tag element, the possible attributes are these ones

.. list-table::
   :header-rows: 1

   * - Attribute
     - Required?
     - Description
   * - ``no_item``
     - No
     - Defines the text to display when no 3D Items are present.
   * - ``no_area_loaded``
     - No
     - Defines the text to display when no 3D Areas were found with the current Items.
   * - ``auto_refresh``
     - No
     - Defines an auto refresh of the Data shown in the view on a given interval in **seconds**


And the containing elements:

.. list-table::
   :header-rows: 1

   * - Elements
     - Required?
     - Description
   * - ``<scene>``
     - **Yes**
     - Represent the 3D Scenes, will contains the ``<ground>`` and ``<objects>`` elements.
   * - ``<camera>``
     - No
     - Represent the Camera config.
   * - ``<legend>``
     - No
     - Define the legend shown on the top-right
   * - ``<templates>``
     - No
     - Custom templates for the popup show one 3D Item details


Example:

.. code-block:: xml

   <threed
       name="3d View"
       no_area_loaded="No areas have been loaded. Please check whether the areas have a planimetry image and the dimensions correctly set."
       no_item="No product."
       auto_refresh="50"
       >
       <!-- Content of the view -->
       <scene>
           <ground/>
           <objects/>
       </scene>
   </threed>

The ``<scene>`` Element containing the ``<ground>`` and the ``<objects>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The scene will make the bridge between the objects shown, (main model of the View) and the ground/area which is usually a related model. For example the 3D Scene on the the ``stock.location`` where ``stock.location`` are the main object will be comprised of ``stock.location`` ``<objects>`` and the ``<ground>`` will be the ``stock.warehouse``.

Creating the ``<ground>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This element should contains only one ``<field>`` present on the main model, here ``warehouse_id`` is present on the main model ``stock.location``

.. code-block:: xml

   <ground>
       <field name="warehouse_id">
           <planimetry
               name_field="name"
               image_field="planimetry_image"
               sizex_field="spacex"
               sizey_field="spacey"
               sizez_field="spacez"
           >
           </planimetry>
       </field>
   </ground>

Inside that field should be the ``<planimetry>`` Element that represents the planimetry Image of the "ground".

.. list-table::
   :header-rows: 1

   * - Attribute
     - Required?
     - Description
   * - ``name_field``
     - **Yes**
     - Field name representing the "name" on the related Odoo Model
   * - ``image_field``
     - **Yes**
     - Field name representing the "image" (Binary Field) of the planimetry floor on the related Odoo Model
   * - ``sizex_field``
     - **Yes**
     - Field name representing the "X Size" of the planimetry on the related Odoo Model
   * - ``sizey_field``
     - **Yes**
     - Field name representing the "Y Size" of the planimetry on the related Odoo Model
   * - ``sizez_field``
     - **Yes**
     - Field name representing the "Z Size" of the planimetry on the related Odoo Model


Creating the ``<objects>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objects are 3D Items that will be visible on the ground and that corresponds to the ``res_model`` of the View, so here you can use ``<field>`` that are present on that ``res_model``\ , these fields should be typed with the adequate ``type`` attribute to give the necessary 3D Rendering info to position the objects on the 3D Scene, for example:

.. code-block:: xml

   <objects>
       <field name="posx" type="position" axis="x" />
       <field name="posy" type="position" axis="y" />
       <field name="posz" type="position" axis="z" />
       <field name="sizex" type="size" axis="x" />
       <field name="sizey" type="size" axis="y" />
       <field name="sizez" type="size" axis="z" />
       <field name="scale_factor" type="scale_factor" />
       <field name="rotx" type="rotation" axis="x" />
       <field name="roty" type="rotation" axis="y" />
       <field name="rotz" type="rotation" axis="z" />
       <field name="gltf_3d_model" type="gltf" /> <!-- my Odoo model contains gltf_3d_model = fields.Binary("... -->
       <field name="shape_file" type="geometry" /> <!-- my Odoo model contains shape_file = fields.Binary("... -->
       <field name="color" type="color" />
       <field name="opacity" type="opacity" />
       <field name="barcode" type="name" />
       <field name="usage" />
       <field name="warehouse_id" />
   </objects>

List of types to put on field:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Type
     - Required?
     - Other Attribute
     - Description
   * - ``type="position"``
     - **Yes**
     - ``axis`` = ``x,y,z``
     - Set this Field as holding the 3D Position of the item, combined with the ``axis`` attribute x, y or z.
   * - ``type="size"``
     - **Yes**
     - ``axis`` = ``x,y,z``
     - Set this Field as holding the 3D Size of the item, combined with the ``axis`` attribute x, y or z.
   * - ``type="rotation"``
     - **Yes**
     - ``axis`` = ``x,y,z``
     - Set this Field as holding the 3D Rotation of the item, combined with the ``axis`` attribute x, y or z.
   * - ``type="scale_factor"``
     - **Yes**
     - No
     - Set this Field as holding the scale of the 3D Model
   * - ``type="name"``
     - **Yes**
     - No
     - Set this Field as holding the name
   * - ``type="gltf"``
     - No
     - No
     - Set this Field as holding GLTF Model (Binary Field)
   * - ``type="geometry"``
     - No
     - No
     - Set this Field as holding Shape File (Binary Field)
   * - ``type="color"``
     - No
     - No
     - Set this Field as holding the color
   * - ``type="opacity"``
     - No
     - No
     - Set this Field as holding the opacity


Optional ``<camera>`` element
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This element can be created to specify configuration of the Camera used in the 3D Scene, attributes are:

.. list-table::
   :header-rows: 1

   * - Attribute
     - Required?
     - Description
   * - ``x``
     - No
     - Default to area size X / 2 or fallback to 1000
   * - ``y``
     - No
     - Default to area size Y / 2 or fallback to 1000
   * - ``z``
     - No
     - Default to area size z x 8 or fallback to 1000
   * - ``fov``
     - No
     - Field of view, default to 50


Handling the legend with the Optional ``<legend>`` element
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set legend with ``context``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Legend can be set statically inside the ``context`` used to open the view, example from XML (can also be set from python):

.. code-block:: xml

   <field name="context">{
       "force_legend_items": [
           {
               "name": "blocked",
               "color": "#F06050",
               "opacity": 1,
           },
           {
               "name": "normal",
               "color": "#F7CD1F",
               "opacity": 1,
           },
           {
               "name": "done",
               "color": "#30C381",
               "opacity": 1,
           }
       ]
   }</field>

``force_legend_items`` should be a **list** of dict containing the keys, ``name``\ , ``color``\ , ``opacity`` (Optional).

Set legend from another Model via XML
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Legend can also be loaded dynamically from another model, like so:

.. code-block:: xml

   <legend
       comodel_name="stock.location.tag"
       name_field="name"
       color_field="color_hex"
       opacity_field="opacity"/>

The attributes on this element are used to define the Legend

.. list-table::
   :header-rows: 1

   * - Attribute
     - Required?
     - Description
   * - ``comodel_name``
     - No
     - The Odoo Model representing the legends, if present an RPC call will be made to that model to fetch all the legends.
   * - ``name_field``
     - No
     - The key of the resulting dict representing the **name** , defaults to "name"
   * - ``color_field``
     - No
     - The key of the resulting dict representing the **color** , defaults to "color"
   * - ``opacity_field``
     - No
     - The key of the resulting dict representing the **opacity** , defaults to "opacity"


Custom Templates
~~~~~~~~~~~~~~~~

Optionally you can declare a custom template, which will be used to render the

popup when you click on a 3D item. You have to name the template 'threedview-popup-info' with the attribute ``server_action``.


*
  ``server_action`` attribute the corresponds to a @api.model action on the main model of the view.

*
  ``record``\ : to access the fields values returned by the server action specified in ``server_action``.

Example:

.. code-block:: xml

       <templates>
           <!-- Here we have access to "record" containing the result of the server_action -->
           <t t-name="threedview-popup-info" server_action="get_3d_view_item_info">
               <header>
                   <span class="item3d_data" t-esc="record.barcode" />
               </header>
               <t t-if="!record.stock_quants || record.stock_quants.length == 0">
                   <p>No product is stored here at the moment.</p>
               </t>
               <!-- etc... -->
          </t>
       </templates>

Complete example
~~~~~~~~~~~~~~~~

.. code-block:: xml

       <?xml version="1.0" encoding="utf-8"?>
       <odoo>
           <record id="view_location_threed_threed" model="ir.ui.view">
               <field name="name">stock.location.threed</field>
               <field name="model">stock.location</field>
               <field name="type">threed</field>
               <!--field name="auto_refresh" eval="10"></field-->
               <field name="arch" type="xml">
                   <threed
                       name="3d View"
                       noAreaLoaded="No areas have been loaded. Please check whether the areas have a planimetry image and the dimensions correctly set."
                       noItem="No product."
                   >
                       <camera x="" y="" z="" fov="50" />
                       <scene>
                           <ground>
                               <field name="warehouse_id">
                                   <planimetry
                                       name_field="name"
                                       image_field="planimetry_image"
                                       sizex_field="spacex"
                                       sizey_field="spacey"
                                       sizez_field="spacez"
                                   >
                                   </planimetry>
                               </field>
                           </ground>
                           <objects>
                               <field name="posx" type="position" axis="x" />
                               <field name="posy" type="position" axis="y" />
                               <field name="posz" type="position" axis="z" />
                               <field name="sizex" type="size" axis="x" />
                               <field name="sizey" type="size" axis="y" />
                               <field name="sizez" type="size" axis="z" />
                               <field name="scale_factor" type="scale_factor" />
                               <field name="rotx" type="rotation" axis="x" />
                               <field name="roty" type="rotation" axis="y" />
                               <field name="rotz" type="rotation" axis="z" />
                               <field name="gltf_3d_model" type="gltf" />
                               <field name="shape_file" type="geometry" />
                               <field name="color" type="color" />
                               <field name="opacity" type="opacity" />
                               <field name="barcode" type="name" />
                               <field name="usage" />
                               <field name="warehouse_id" />
                           </objects>
                       </scene>
                       <legend
                           comodel_name="stock.location.tag"
                           name_field="name"
                           color_field="color_hex"
                           opacity_field="opacity"
                       />
                       <templates>
                           <!-- Here we have access to "record" containing the result of the server_action -->
                           <t t-name="threedview-popup-info" server_action="get_3d_view_item_info">
                               <header>
                                   <span class="item3d_data" t-esc="record.barcode" />
                               </header>
                               <t t-if="!record.stock_quants || record.stock_quants.length == 0">
                                   <p>No product is stored here at the moment.</p>
                               </t>
                               <t t-else="">
                                   <ul style="padding-left: 16px;">
                                       <t t-foreach="record.stock_quants" t-as="stock_quant">
                                           <li>
                                               <t t-if="stock_quant.product_code or stock_quant.product_lot">
                                                   <t t-if="stock_quant.product_code">
                                                       <t t-esc="stock_quant.product_code" />
                                                   </t>
                                                   <t t-if="stock_quant.product_lot">
                                                       Lot:<t t-esc="stock_quant.product_lot" />
                                                   </t>
                                                   :
                                               </t>
                                               <t t-esc="stock_quant.product_name" /> (<t
                                                   t-esc="stock_quant.product_qty"
                                               />)
                                           </li>
                                       </t>
                                   </ul>
                               </t>
                           </t>
                       </templates>
                   </threed>
               </field>
           </record>

           <record id="stock_3dbase.act_warehouse_stock_locations" model="ir.actions.act_window">
               <field name="view_mode">tree,form,pivot,threed</field>
               <field
                   name="view_ids"
                   eval="[(5, 0, 0),
                           (0, 0, {'view_mode': 'tree', 'view_id': ref('view_location_tree_threed')}),
                           (0, 0, {'view_mode': 'form', 'view_id': ref('view_location_form_threed')}),
                           (0, 0, {'view_mode': 'pivot', 'view_id': ref('view_location_pivot_threed')}),
                           (0, 0, {'view_mode': 'threed', 'view_id': ref('view_location_threed_threed')})]"
               />
               <field name="search_view_id" ref="stock_3dbase.view_location_search_wh" />
           </record>
       </odoo>
