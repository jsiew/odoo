/** @odoo-module */

import {XMLParser} from "@web/core/utils/xml";

/**
 *
 * @typedef {Object} ItemFieldsMapping
 * @property {string} nameField
 * @property {string} areaField
 * @property {string} gltfField
 * @property {string} scaleFactorField
 * @property {string} geometryField
 * @property {string} colorField
 * @property {string} opacityField
 * @property {string} sizexField
 * @property {string} sizeyField
 * @property {string} sizezField
 * @property {string} positionxField
 * @property {string} positionyField
 * @property {string} positionzField
 * @property {string} rotationxField
 * @property {string} rotationyField
 * @property {string} rotationzField
 *
 *
 *
 * @typedef {Object} AreaFieldsMapping
 * @property {string} planimetryImageField
 * @property {string} nameField
 * @property {string} sizexField
 * @property {string} sizeyField
 * @property {string} sizezField
 *
 * @typedef {Object} LegendFieldsMapping
 * @property {string} nameField
 * @property {string} colorField
 * @property {string} opacityField
 *
 * @typedef {Object} CameraConfig
 * @property {number} [camx]
 * @property {number} [camy]
 * @property {number} [camz]
 * @property {number} [camfov]
 *
 * @typedef {Object} ArchInfo
 * @property {string} arch
 * @property {string} allItems
 * @property {string} allAreas
 * @property {string} selectedItems
 * @property {string} legend
 * @property {string} selectedItems
 * @property {string} areaId
 * @property {string} rendererArea
 * @property {string} settings
 * @property {string} noAreaLoaded
 * @property {string} noItem
 * @property {string} legendModel
 * @property {CameraConfig} camera
 * @property {AreaFieldsMapping} areaFieldsMapping
 * @property {ItemFieldsMapping} itemFieldsMapping
 * @property {LegendFieldsMapping} legendFieldsMapping
 * @property {string[]} readFields
 * @property {number | null} autoRefresh
 * @property {string} [itemInfoserverAction]
 */

export class ThreedArchParser extends XMLParser {
    parse(arch) {
        const xmlDoc = this.parseXML(arch);
        const noAreaLoaded = xmlDoc.getAttribute("no_area_loaded");
        const noItem = xmlDoc.getAttribute("no_item");
        let autoRefreshAttrNode = xmlDoc.getAttribute("auto_refresh");
        let itemInfoserverAction = "get_3d_view_item_info";
        let autoRefresh = null;
        if (autoRefreshAttrNode) {
            autoRefresh = parseInt(autoRefreshAttrNode, 10);
        }
        let legendModel = "";
        /** @type {CameraConfig} */
        const camera = {};
        /** @type {LegendFieldsMapping | Object} */
        const legendFieldsMapping = {};
        /** @type {AreaFieldsMapping | Object} */
        const areaFieldsMapping = {};
        /** @type {ItemFieldsMapping | Object} */
        const itemFieldsMapping = {};
        /** @type {Array.<string>} */
        const readFields = [];
        /** @type {Record<string, Element>} */
        const templateDocs = {};

        this.visitXML(arch, (node) => {
            if (node.hasAttribute("t-name")) {
                templateDocs[node.getAttribute("t-name")] = node;
                if (node.getAttribute("server_action")) {
                    itemInfoserverAction = node.getAttribute("server_action");
                }
            }
            switch (node.tagName) {
                case "camera": {
                    if (
                        node.getAttribute("x") &&
                        !isNaN(parseInt(node.getAttribute("x")))
                    ) {
                        camera.camx = parseInt(node.getAttribute("x"));
                    }
                    if (
                        node.getAttribute("y") &&
                        !isNaN(parseInt(node.getAttribute("y")))
                    ) {
                        camera.camy = parseInt(node.getAttribute("y"));
                    }
                    if (
                        node.getAttribute("z") &&
                        !isNaN(parseInt(node.getAttribute("z")))
                    ) {
                        camera.camz = parseInt(node.getAttribute("z"));
                    }
                    if (
                        node.getAttribute("fov") &&
                        !isNaN(parseInt(node.getAttribute("fov")))
                    ) {
                        camera.camfov = parseInt(node.getAttribute("fov"));
                    }
                    break;
                }
                case "planimetry": {
                    Object.assign(areaFieldsMapping, {
                        planimetryImageField: node.getAttribute("image_field"),
                        nameField: node.getAttribute("name_field"),
                        sizexField: node.getAttribute("sizex_field"),
                        sizeyField: node.getAttribute("sizey_field"),
                        sizezField: node.getAttribute("sizez_field"),
                    });
                    break;
                }
                case "legend": {
                    legendModel = node.getAttribute("comodel_name") ?? "";
                    Object.assign(legendFieldsMapping, {
                        nameField: node.getAttribute("name_field"),
                        colorField: node.getAttribute("color_field"),
                        opacityField: node.getAttribute("opacity_field"),
                    });
                    break;
                }
                case "field": {
                    readFields.push(node.getAttribute("name"));
                    if (node.parentNode) {
                        switch (node.parentNode.nodeName) {
                            case "ground": {
                                itemFieldsMapping.areaField = node.getAttribute("name");
                                break;
                            }
                            case "objects": {
                                if (node.getAttribute("type") === "gltf") {
                                    itemFieldsMapping.gltfField =
                                        node.getAttribute("name");
                                    break;
                                }
                                if (node.getAttribute("type") === "scale_factor") {
                                    itemFieldsMapping.scaleFactorField =
                                        node.getAttribute("name");
                                    break;
                                }
                                if (node.getAttribute("type") === "name") {
                                    itemFieldsMapping.nameField =
                                        node.getAttribute("name");
                                    break;
                                }
                                if (node.getAttribute("type") === "geometry") {
                                    itemFieldsMapping.geometryField =
                                        node.getAttribute("name");
                                    break;
                                }
                                if (node.getAttribute("type") === "color") {
                                    itemFieldsMapping.colorField =
                                        node.getAttribute("name");
                                    break;
                                }
                                if (node.getAttribute("type") === "opacity") {
                                    itemFieldsMapping.opacityField =
                                        node.getAttribute("name");
                                    break;
                                }
                                if (node.getAttribute("type") === "size") {
                                    itemFieldsMapping[
                                        `size${node.getAttribute("axis")}Field`
                                    ] = node.getAttribute("name");
                                    break;
                                }
                                if (node.getAttribute("type") === "position") {
                                    itemFieldsMapping[
                                        `position${node.getAttribute("axis")}Field`
                                    ] = node.getAttribute("name");
                                    break;
                                }
                                if (node.getAttribute("type") === "rotation") {
                                    itemFieldsMapping[
                                        `rotation${node.getAttribute("axis")}Field`
                                    ] = node.getAttribute("name");
                                    break;
                                }
                            }
                        }
                    }
                    break;
                }
            }
        });
        return {
            arch,
            noAreaLoaded,
            noItem,
            camera,
            areaFieldsMapping,
            itemFieldsMapping,
            readFields,
            legendFieldsMapping,
            legendModel,
            autoRefresh,
            templateDocs,
            itemInfoserverAction,
        };
    }
}
