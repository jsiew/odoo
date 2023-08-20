/** @odoo-module */
/** @typedef {import("./web_threed_model").ThreedModel} ThreedModel */
import {Layout} from "@web/search/layout";
import {useService} from "@web/core/utils/hooks";
import {useViewCompiler} from "@web/views/view_compiler";
import {ViewCompiler} from "@web/views/view_compiler";

const {Component, onWillStart, onWillUpdateProps, useState, useEffect, useRef} = owl;

export class ThreedController extends Component {
    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        /** @type ThreedModel */
        this.model = useState(
            new this.props.Model(
                this.orm,
                this.props.resModel,
                this.props.fields,
                this.props.archInfo,
                this.props.domain,
                this.props.context,
                this.rpc
            )
        );

        const {arch, templateDocs} = this.props.archInfo;
        this.templates = useViewCompiler(ViewCompiler, arch, templateDocs, {});

        this.state = useState({
            groundAreas: [],
            selectedGroundAreaId: undefined,
            showLegend: false,
            showAutoRefreshCountdown:
                this.props.archInfo.autoRefresh && this.props.archInfo.autoRefresh > 5,
            autoRefreshCountdown: this.props.archInfo.autoRefresh || 0,
            error: undefined,
        });

        onWillStart(async () => {
            await this.model.load();
            if (this.model.all3dItems.length === 0) {
                this.state.error = {
                    title: "No 3D items found",
                    message: `No 3D items found, please check that the items (${this.model.resModel}) are correctly configured with (size X, Y, Z).`,
                };
                return;
            }
            if (this.model.all3dItems.length && this.model.groundAreas.length < 1) {
                this.state.error = {
                    title: "No Area loaded",
                    message: `No area (${this.model.areaModel}) with Planimetry Image and size (X, Y, Z) were found for these items.`,
                };
                return;
            }
            if (this.model.groundAreas.length < 1) {
                this.state.error = {
                    title: "No Area loaded",
                    message: `No area (${this.model.areaModel}) with Planimetry Image and size (X, Y, Z) were found for these items.`,
                };
            } else {
                this.state.selectedGroundAreaId = this.model.groundAreas[0].id;
            }
        });

        onWillUpdateProps(async (nextProps) => {
            if (
                JSON.stringify(nextProps.domain) !== JSON.stringify(this.props.domain)
            ) {
                this.model.domain = nextProps.domain;
                await this.model.load();
            }
        });

        useEffect(
            (_archInfo, groundAreas) => {
                if (groundAreas && groundAreas.length > 0) {
                    this.state.selectedGroundAreaId = groundAreas[0].id;
                }
            },
            () => [this.props.archInfo, this.model.groundAreas]
        );

        if (this.state.showAutoRefreshCountdown) {
            useEffect(
                () => {
                    this.autoUpdateInterval = setInterval(async () => {
                        this.state.autoRefreshCountdown--;
                        if (this.state.autoRefreshCountdown <= 0) {
                            this.model.update();
                            this.state.autoRefreshCountdown =
                                this.props.archInfo.autoRefresh;
                        }
                    }, 1000);
                    return () => clearInterval(this.autoUpdateInterval);
                },
                () => [this.props.archInfo.autoRefresh]
            );
        }
    }

    /**
     * @param {{ target: { value: string; }; }} event
     */
    _updateSelectedAreaId(event) {
        this.state.selectedGroundAreaId = parseInt(event.target.value);
    }

    /**
     * @param {number } res_id
     */
    async onLoadInfoForObjectId(res_id) {
        const record = await this.orm.call(
            this.props.resModel,
            this.props.archInfo.itemInfoserverAction,
            [res_id],
            {}
        );
        return record;
    }
}

ThreedController.template = "web_threed.View";
ThreedController.components = {Layout};
