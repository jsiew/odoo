from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from odoo import _,api, fields, models
from odoo.api import Environment
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
from ..depends import (
    odoo_env,
)


class ShipmentOrderEndpoint(models.Model):

    _inherit = "fastapi.endpoint"

    app: str = fields.Selection(
        selection_add=[("wcs", "WCS Interface")], ondelete={"wcs": "cascade"}
    )
    
    def _get_fastapi_routers(self):
        if self.app == "wcs":
            return [wcs_api_router]
        return super()._get_fastapi_routers()

class wcs_interface_notification(BaseModel):
    result: bool
    msg: str
    responseType: str
    statusCode: int
    code: int
    data: dict

class wcs_apiresponse(BaseModel):
    status: str
    message: str

# create a router
wcs_api_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # use token authentication

def api_key_auth( env: Environment = Depends(odoo_env), api_key: str = Depends(oauth2_scheme)):
    wms_api_key = env['ir.config_parameter'].sudo().get_param('shipment_order.wms_interface_api_key')

    if api_key != wms_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forbidden: Incorrect API Key"
        )
    else: 
        print(api_key) 

@wcs_api_router.post(
        "/notifications/create", 
        response_model=wcs_apiresponse, 
        status_code=status.HTTP_201_CREATED, 
        dependencies=[Depends(api_key_auth)])
def create_notification(
    notification: wcs_interface_notification,
    env: Environment = Depends(odoo_env)
) -> wcs_apiresponse:  # noqa: B008
    wcs_order_obj = env['shipment_order.move']
    wcs_log_obj = env['shipment_order.movelog']
    res = {}
    try:
        notification_type = notification.responseType
        message = notification.msg
        code = notification.code
        statusCode = notification.statusCode
        data = notification.data['response']
        print("Notification received: " + str(notification))
        #AGV id
        subsystem_id = notification.data['subsystem_id']

        if notification_type == 'notification' and code == 50000 :
            wcs_order = wcs_order_obj.search(['|',
                                ('wcs_id_1', '=', notification.data['wcs_id']),
                                ('wcs_id_2', '=', notification.data['wcs_id']),
                                ], limit=1)
            if wcs_order.id:
                #get link to the wcs transport order form
                web_base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
                wcs_order_action_id = env.ref('shipment_order.act_shipment_order_move', raise_if_not_found=False)
                wcs_order_link = """{}/web#id={}&view_type=form&model=shipment_order.move&action={}""".format(web_base_url, wcs_order.id, wcs_order_action_id.id)
                #web#id=209&cids=1&menu_id=111&action=236&active_id=1&model=stock.picking&view_type=form

                if notification.data['wcs_id'] == wcs_order.wcs_id_1:
                    order_seq = 1
                else: order_seq = 2
                if order_seq == 1:
                    wcs_order.write({'wcs_state_1': notification.data['wcs_state'],})
                    pickup_location = wcs_order.wcs_pickup_1
                    dropoff_location = wcs_order.wcs_dropoff_1
                else: 
                    wcs_order.write({'wcs_state_2': notification.data['wcs_state'],})
                    pickup_location = wcs_order.wcs_pickup_2
                    dropoff_location = wcs_order.wcs_dropoff_2
                elevated_tray = env['shipment_order.elevated.tray'].search(['|',
                                ('open_side_code','=',dropoff_location),
                                ('closed_side_code','=',dropoff_location)
                                ], limit=1)
                

                match notification.data['wcs_state']:
                    case "completed":
                        #confirm move line if both wcs TOs are completed (or there is only 1 TO)

                        #Free up elevated tray
                        if elevated_tray.id != False:
                            elevated_tray.write({'occupied_state' : 'Empty'})

                        if wcs_order.wcs_id_2 == False or wcs_order.wcs_id_2 == '' or (wcs_order.wcs_state_1 == 'completed' and wcs_order.wcs_state_2 == 'completed'):
                            if wcs_order.move_line_id.id:
                                #If move line is added to a picking with done state, its state is automatically set to done, do not repeat
                                if wcs_order.move_line_id.state != 'done':
                                    wcs_order.move_line_id.write({'qty_done': 1})
                                    wcs_order.move_line_id._action_done()
                                    wcs_order.move_line_id.write({'state': 'confirmed'})
                                
                        notification_message = '{}<br /><a href="{}">Pallet {} [Bkg/BL No.: {}]</a><br />Moved from {} to {}<br />WCS ID: {}, WMS Doc ID: {}'
                        notification_message = notification_message.format(message,wcs_order_link, wcs_order.pallet_id.name, wcs_order.picking_id.ref_number, 
                                                    pickup_location, dropoff_location,
                                                    notification.data['wcs_id'], wcs_order.picking_id.name)
                        
                        env.user.notify_success(message=notification_message,title="WCS Order Completed", sticky=False)
                                
                    case "cancelled":
                        
                        if elevated_tray.id != False:
                            elevated_tray.write({'occupied_state' : 'Empty'})

                        notification_message = '{}<br />Pallet {} [Bkg/BL No.: {}]<br />Moving from {} to {}<br />WCS ID: {}, WMS Doc ID: {}'
                        notification_message = notification_message.format(message, wcs_order.pallet_id.name, wcs_order.picking_id.ref_number, 
                                                                           pickup_location, dropoff_location,
                                                                           str(wcs_order.wcs_id_1) + (('/' + wcs_order.wcs_id_2) if wcs_order.wcs_id_2 else '') ,
                                                                            wcs_order.picking_id.name)
                    
                        env.user.notify_warning(message=notification_message,title="WCS Order Cancelled", sticky=True)
                        
                     
                    case _:
                        notification_message = '{}<br /><a href="{}">Pallet {} [Bkg/BL No.: {}]</a><br />Moving from {} to {}<br />WCS ID: {}, WMS Doc ID: {}'
                        notification_message = notification_message.format(message,wcs_order_link, wcs_order.pallet_id.name, wcs_order.picking_id.ref_number, wcs_order.location_id.name,
                                                                           wcs_order.location_dest_id.name,
                                                                           str(wcs_order.wcs_id_1) + (('/' + wcs_order.wcs_id_2) if wcs_order.wcs_id_2 else '') ,
                                                                           wcs_order.picking_id.name)
                        env.user.notify_info(message=notification_message,title="WCS Notification Received", sticky=False)

                #Write to log
                log_id = wcs_log_obj.create({'remarks': 'WCS Notification Received',
                                'wcs_message': message + ' [AGV: ' + subsystem_id + ']',
                                'wcs_message_type':notification_type,
                                'wcs_message_code': statusCode,
                                'wcs_notification_code': code,
                                'wcs_timestamp': datetime.today(),
                                'wcs_raw_data':data,
                                'transport_order' : wcs_order.id if notification.data['wcs_state'] != "cancelled" else None,
                                'transport_order_number': order_seq if notification.data['wcs_state'] != "cancelled" else None,
                                'wcs_id':notification.data['wcs_id']})
                res = {
                    'status': 'success',
                    'message': 'Notification Updated [Order '+ wcs_order.picking_id.name + ', Pallet ' + wcs_order.pallet_id.name +']'
                }

                
                #delete cancelled order for incoming
                if notification.data['wcs_state'] == "cancelled" and wcs_order.move_line_id.state != 'done':
                    picking_type_code = wcs_order.move_line_id.picking_type_id.code
                    if picking_type_code == 'incoming':
                        wcs_order.move_line_id.write({'qty_done': 0, 'reserved_uom_qty':0, 'state': 'draft'})
                        wcs_order.move_line_id.unlink()
                    else:
                        #clear staging state
                        staging_id = env['shipment_order.staging.state'].search([
                                                    ('pallet_id','=', wcs_order.pallet_id.id)
                                                ])
                        if staging_id.id:
                            staging_id.write({'pallet_id':None, 'pallet_date':None})

            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='WCS ID ' + notification.data['wcs_id'] + ' not found'
                )
        elif notification_type == 'error':
            match notification.data['error_type']:
                case 'transport_order':
                    wcs_order = wcs_order_obj.search(['|',
                                ('wcs_id_1', '=', notification.data['wcs_id']),
                                ('wcs_id_2', '=', notification.data['wcs_id']),
                                ], limit=1)
                    if wcs_order.id:
                        
                        if notification.data['wcs_id'] == wcs_order.wcs_id_1:
                            order_seq = 1
                        else: order_seq = 2
                        if order_seq == 1:
                            wcs_order.write({'wcs_state_1': notification.data['wcs_state'],})
                            dropoff_location = wcs_order.wcs_dropoff_1
                        else: 
                            wcs_order.write({'wcs_state_2': notification.data['wcs_state'],})
                            dropoff_location = wcs_order.wcs_dropoff_2

                        elevated_tray = env['shipment_order.elevated.tray'].search(['|',
                                        ('open_side_code','=',dropoff_location),
                                        ('closed_side_code','=',dropoff_location)
                                        ], limit=1)
                        
                        if elevated_tray.id != False:
                            elevated_tray.write({'occupied_state' : 'Empty'})
                            
                        #get link to the wcs transport order form
                        web_base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
                        wcs_order_action_id = env.ref('shipment_order.act_shipment_order_move', raise_if_not_found=False)
                        wcs_order_link = """{}/web#id={}&view_type=form&model=shipment_order.move&action={}""".format(web_base_url, wcs_order.id, wcs_order_action_id.id)
                        
                        
                        notification_message = '{}<br /><a href="{}">Pallet {} [BL/Bkg No.: {}]</a><br />Moving from {} to {}<br />WCS ID: {}, WMS Doc ID: {}, AGV: {}'
                        notification_message = notification_message.format(message, wcs_order_link, wcs_order.pallet_id.name, wcs_order.picking_id.ref_number, wcs_order.location_id.name,
                                                                           wcs_order.location_dest_id.name,
                                                                           str(wcs_order.wcs_id_1) + (('/' + wcs_order.wcs_id_2) if wcs_order.wcs_id_2 else '') ,
                                                                            wcs_order.picking_id.name,subsystem_id)
                        env.user.notify_danger(message=notification_message,title="WCS Transport Order Error", sticky=True)
            
                        log_id = wcs_log_obj.create({'remarks': 'WCS Transport Order Error Received',
                                                'wcs_message': message + ' [' + subsystem_id + ']',
                                                'wcs_message_type':notification_type,
                                                'wcs_message_code': statusCode,
                                                'wcs_notification_code': code,
                                                'wcs_timestamp': datetime.today(),
                                                'wcs_raw_data':data,
                                                'transport_order' : wcs_order.id,
                                                'transport_order_number': order_seq,
                                                'wcs_id': notification.data['wcs_id'] })
                        res = {
                            'status': 'success',
                            'message': 'Notification Updated [Order '+ wcs_order.picking_id.name + ', Pallet ' + wcs_order.pallet_id.name +']'
                        }

                    else:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail='WCS ID ' + notification.data['wcs_id'] + ' not found'
                        )

                case _:
                    notification_message = '{}<br />AGV: {}'
                    notification_message = notification_message.format(message,subsystem_id)
                    env.user.notify_danger(message=notification_message,title="WCS General Error", sticky=True)

                    log_id = wcs_log_obj.create({'remarks': 'WCS General Error Received',
                                                'wcs_message': message + ' [' + subsystem_id + ']',
                                                'wcs_message_type':notification_type,
                                                'wcs_message_code': statusCode,
                                                'wcs_notification_code': code,
                                                'wcs_timestamp': datetime.today(),
                                                'wcs_raw_data':data})
                    res = {
                        'status': 'Success',
                        'message': 'General Error Notification Updated'
                    }
        elif notification_type == 'notification' and code >= 70000 and code <80000:
            notification_message = '{}<br />AGV: {}'
            notification_message = notification_message.format(message,subsystem_id)
            
            env.user.notify_warning(message=notification_message,title="WCS Warning", sticky=True)
            log_id = wcs_log_obj.create({'remarks': 'WCS General Error Received (70000)',
                                                'wcs_message': message + ' [' + subsystem_id + ']',
                                                'wcs_message_type':notification_type,
                                                'wcs_message_code': statusCode,
                                                'wcs_notification_code': code,
                                                'wcs_timestamp': datetime.today(),
                                                'wcs_raw_data':data})
            res = {
                        'status': 'Success',
                        'message': 'General Error Notification Updated (70000)'
                    }
                
            
    except Exception as e:
        raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
    return res