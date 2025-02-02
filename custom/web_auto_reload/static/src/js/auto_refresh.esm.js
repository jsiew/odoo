/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { useBus } from "@web/core/utils/hooks";
import { actionService } from "@web/webclient/actions/action_service";

patch(WebClient.prototype, "webAutoRefresh", {
    auto_refresh(currentController, actionService, mode){
        var self = this;
        if(this.action_timer){
            clearTimeout(this.action_timer);
        }
        console.log('patch')
        console.log(currentController)
        if(currentController && currentController.action && currentController.action.reload_time){
            self.action_timer = setTimeout(function(){
                if(currentController.view){
                    if(currentController.view.type == 'kanban' || currentController.view.type == 'list' || currentController.view.type == 'tree'){
                        actionService.loadState();
                        self.auto_refresh(currentController, self.actionService, mode);
                    }
                }else{
                    actionService.loadState();
                    self.auto_refresh(currentController, self.actionService, mode);
                }
            },currentController.action.reload_time);
        }
    },
    setup() {
        this._super(...arguments);
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", (mode) => {
            var self = this
            if(this.action_timer){
                clearTimeout(this.action_timer);
            }
            const currentController = this.actionService.currentController;
            console.log('setup')
            console.log(currentController)
            console.log(this.actionService)
            if(currentController && currentController.action && currentController.action.reload_time){
                if(currentController.view){
                    if(currentController.view.type != 'form'){
                        this.auto_refresh(currentController, this.actionService, mode);
                    }
                }else{
                    this.auto_refresh(currentController, this.actionService, mode);
                }
            }
            if (mode !== "new") {
                this.state.fullscreen = mode === "fullscreen";
            }
        });
    }
});
