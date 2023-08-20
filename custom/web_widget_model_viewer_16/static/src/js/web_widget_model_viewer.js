/** @odoo-module **/
const {useRef, useState, onWillStart} = owl;
import {registry} from "@web/core/registry";
import {ImageField, imageCacheKey} from "@web/views/fields/image/image_field";
import {url} from "@web/core/utils/urls";
import {isBinarySize} from "@web/core/utils/binary";
import {loadJSModule} from "./assets";

const placeholder = "/web_widget_model_viewer_16/static/glb/placeholder.glb";

export class ModelViewerField extends ImageField {
    setup() {
        super.setup();
        this.modelViewerRef = useRef("modelViewer");
        this.windowState = useState({
            isFullscreen: false,
            jsLibLoaded: false,
        });
        onWillStart(async () => {
            if (!this.windowState.jsLibLoaded) {
                await loadJSModule(
                    "/web_widget_model_viewer_16/static/lib/model-viewer.min.js"
                );
                this.windowState.jsLibLoaded = true;
            }
        });
    }

    /**
     * @param {string} previewFieldName
     */
    getUrl(previewFieldName) {
        if (this.state.isValid && this.props.value) {
            if (isBinarySize(this.props.value)) {
                return url("/web/content", {
                    model: this.props.record.resModel,
                    id: this.props.record.resId,
                    field: previewFieldName,
                    unique: imageCacheKey(this.rawCacheKey),
                });
            } else {
                return `data:model/gltf-binary;base64,${this.props.value}`;
            }
        }
        return placeholder;
    }

    /**
     * @param {Event} ev
     */
    fullscreen(ev) {
        const isFullscreenAvailable = document.fullscreenEnabled || false;
        var modelViewerElem = this.modelViewerRef.el;
        if (isFullscreenAvailable) {
            var fullscreenElement = document.fullscreenElement;
            if (fullscreenElement) {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                    this.windowState.isFullscreen = false;
                }
            } else {
                modelViewerElem.requestFullscreen();
                this.windowState.isFullscreen = true;
            }
        } else {
            console.error("ERROR : full screen not supported by web browser");
        }
    }

    get sizeStyle() {
        let style = "";
        if (this.props.width) {
            style += `max-width: ${this.props.width}px;`;
        }
        if (this.props.height) {
            style += `max-height: ${this.props.height}px;`;
        }
        return style;
    }
}
ModelViewerField.template = "web_widget_model_viewer_16.ModelViewerField";
ModelViewerField.defaultProps = {
    acceptedFileExtensions: "model/gltf-binary",
};

registry.category("fields").add("model_viewer", ModelViewerField);
