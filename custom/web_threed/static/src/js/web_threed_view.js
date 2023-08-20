/** @odoo-module */

import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {ThreedArchParser} from "./web_threed_arch_parser";
import {ThreedController} from "./web_threed_controller";
import {ThreedModel} from "./web_threed_model";
import {ThreedRenderer} from "./web_threed_renderer";

export const webThreedView = {
    type: "threed",
    display_name: _t("3D"),
    icon: "fa fa-cubes",
    multiRecord: true,
    Controller: ThreedController,
    ArchParser: ThreedArchParser,
    Model: ThreedModel,
    Renderer: ThreedRenderer,

    props(genericProps, view) {
        const {ArchParser} = view;
        const {arch, relatedModels} = genericProps;
        const archInfo = new ArchParser().parse(arch);
        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            archInfo,
        };
    },
};

registry.category("views").add("threed", webThreedView);
