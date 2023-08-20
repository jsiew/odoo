/** @odoo-module */
const {
    onWillUnmount,
    onMounted,
    onWillUpdateProps,
    useState,
    useRef,
    Component,
    markup,
    useEffect,
} = owl;
import {deepCopy} from "@web/core/utils/objects";
import {useAbsoluteThreedPopUp} from "./hooks/use_absolute_threed_popup";
import {useThreedScene} from "./hooks/use_threed_scene";
import {deepEqual} from "./utils/deep_equal";

/**
 * @param {Element} element
 */
function getOffset(element) {
    if (!element.getClientRects().length) {
        return {top: 0, left: 0};
    }

    let rect = element.getBoundingClientRect();
    let win = element.ownerDocument.defaultView;
    return {
        top: rect.top + win.pageYOffset,
        left: rect.left + win.pageXOffset,
    };
}

export class ThreedRenderer extends Component {
    setup() {
        super.setup();
        this.sceneDOMContainer = useRef("scene-container");
        /** @type {{el: HTMLDivElement}} */
        this.root = useRef("root");
        /** @type {{el: HTMLDivElement}} */
        this.barcodeLabel = useRef("barcode-label");
        /** @type {{el: HTMLSpanElement}} */
        this.loadingIcon = useRef("loading-icon");
        this.threeDScene = useThreedScene(
            "scene-container",
            this.derive3DSceneConfigFromProps(this.props)
        );
        this.state = useState({
            currentArea: deepCopy(
                this.props.groundAreas.find(
                    (/** @type { import("./web_threed_model").GroundArea} */ area) =>
                        area.id === this.props.selectedGroundAreaId
                )
            ),
            isFullscreen: false,
            isLoading: true,
            rendererWidth: 0,
            rendererHeight: 0,
        });
        /** @type {{visible: boolean; text: any}} */
        this.coordinatesDisplay = useState({
            visible: false,
            text: "",
        });
        this.itemInfoPopup = useAbsoluteThreedPopUp("item3d-popup", "scene-container");
        this.record = useState({});

        onMounted(() => {
            if (this.state.currentArea) {
                this.threeDScene.renderGround();
                this._setRendererSize();
                this._addEventHandlers();
                this.showWireframesForAllItems3d();
                this.showMeshesForSelectedItems3d(this.props.selected3dItems);
            }
            this.state.isLoading = false;
        });

        onWillUpdateProps(async (nextProps) => {
            if (nextProps.selectedGroundAreaId !== this.props.selectedGroundAreaId) {
                this.state.currentArea = deepCopy(
                    nextProps.groundAreas.find(
                        (/** @type {import("./web_threed_model").GroundArea} */ area) =>
                            area.id === nextProps.selectedGroundAreaId
                    )
                );
            }
            if (!deepEqual(nextProps.selected3dItems, this.props.selected3dItems)) {
                this.showMeshesForSelectedItems3d(nextProps.selected3dItems);
            }
        });

        useEffect(
            () => {
                this.threeDScene.setConfig(
                    this.derive3DSceneConfigFromProps(this.props)
                );
                ["wireframes", "meshes"].forEach((item) => {
                    this.threeDScene.areaObjects[item].forEach((obj) => {
                        obj.visible = obj.userData.area == this.state.currentArea.id;
                    });
                });
                this.threeDScene.renderGround();
                this.manageGLTFObjectsVisibility();
            },
            () => [this.state.currentArea]
        );

        onWillUnmount(() => this._unbindEventHandlers());
    }

    /**
     * Create the configuration object for the 3D scene from the props.
     *
     * @param {{groundAreas: import("./web_threed_model").GroundArea[]; selectedGroundAreaId: number; cameraConfig: import("./web_threed_arch_parser").CameraConfig}} props
     */
    derive3DSceneConfigFromProps(props) {
        /** @type {import("./web_threed_model").GroundArea} */
        const area = props.groundAreas.find(
            (/** @type {import("./web_threed_model").GroundArea} */ a) =>
                a.id === props.selectedGroundAreaId
        );
        /** @type {import("./hooks/use_threed_scene").SceneConfig} */
        const config = {
            groundX_real: area.sizex,
            groundY_real: area.sizey,
            heightZ_real: area.sizez,
            camPosX_real: props.cameraConfig.camx ?? (area.sizex / 2 || 1000),
            camPosY_real: props.cameraConfig.camy ?? (area.sizey / 2 || 1000),
            camPosZ_real: props.cameraConfig.camz ?? (area.sizez * 8 || 1000),
            camFov: props.cameraConfig.camfov ?? 50,
            planimetryImage: area.planimetryImage,
        };
        config.targetX_real = area.sizex / 2;
        config.targetY_real = area.sizey / 2;
        config.targetZ_real = 0;
        config.groundX_3dv = 500;
        config.groundZ_3dv = Math.round(
            (config.groundY_real / config.groundX_real) * config.groundX_3dv
        );
        config.heightY_3dv = Math.round(
            (config.heightZ_real / config.groundX_real) * config.groundX_3dv
        );
        config.scale = config.groundX_real / config.groundX_3dv;
        return config;
    }

    /**
     * Add a new mesh for an item3d.
     *
     * This is used for the selected items3d, that must be shown in full color (or gray).
     *
     * @param {import("./web_threed_model").Item3d} item3d
     * @private
     */
    addMesh(item3d) {
        this.threeDScene.addObject(item3d, "mesh", this.getScaleForArea(item3d.areaId));
    }

    /**
     * Add a new wireframe for a warehose item3d.
     *
     * This is used for all the items3d, that must be shown anyway.
     *
     * @param {import("./web_threed_model").Item3d} item3d
     * @private
     */
    addWireframe(item3d) {
        this.threeDScene.addObject(
            item3d,
            "wireframe",
            this.getScaleForArea(item3d.areaId)
        );
    }

    /**
     * @param {number} areaId
     */
    getScaleForArea(areaId) {
        const area = this.props.groundAreas.find(
            (/** @type {import("./web_threed_model").GroundArea} */ a) =>
                a.id === areaId
        );
        return (area && area.scale) || this.threeDScene.scale;
    }

    /**
     * Show the wireframes for all the items3d.
     *
     * @private
     */
    showWireframesForAllItems3d() {
        this.props.all3dItems.forEach(
            (/** @type {import("./web_threed_model").Item3d} */ item3d) => {
                this.addWireframe(item3d);
            }
        );
        this.threeDScene.renderScene();
    }

    /**
     * Show the meshes for the selected items3d.
     *
     * Since this is called every time a new selection is done, we
     * switch area when all selected items3d belong to one area only.
     *
     * @private
     * @param {import("./web_threed_model").Item3d[]} selected3dItems
     */
    showMeshesForSelectedItems3d(selected3dItems) {
        // first, we remove all existing meshes from the scene
        this.threeDScene.areaObjects.meshes.forEach((obj) => {
            this.threeDScene.removeObject(obj.name);
        });
        this.threeDScene.areaObjects.meshes = [];
        selected3dItems.forEach(
            (/** @type {import("./web_threed_model").Item3d} */ item3d) => {
                this.addMesh(item3d);
                if (item3d.gltf_load_url) {
                    this.showGLTFModel(item3d);
                }
            }
        );
        this.manageGLTFObjectsVisibility();
    }

    manageGLTFObjectsVisibility() {
        ["wireframes", "meshes"].forEach((item) => {
            this.threeDScene.areaObjects[item].forEach((obj) => {
                obj.visible = obj.userData.area == this.state.currentArea.id;
            });
        });
        for (let key in this.threeDScene.areaObjects.gltfObjects) {
            this.threeDScene.areaObjects.gltfObjects[key].model.visible =
                this.threeDScene.areaObjects.gltfObjects[key].area ==
                this.state.currentArea.id;
            this.threeDScene.areaObjects.gltfObjects[key].light.intensity =
                this.threeDScene.areaObjects.gltfObjects[key].area ==
                this.state.currentArea.id
                    ? 7
                    : 0;
        }
    }

    /**
     * @param {import("./web_threed_model").Item3d} item3d
     */
    showGLTFModel(item3d) {
        if (this.threeDScene.areaObjects.gltfModels.indexOf(item3d.gltf) > -1) {
            return;
        }
        this.threeDScene.GLTFLoader.load(item3d.gltf_load_url, (gltf) => {
            let mod = gltf.scene;
            mod.traverse(function (model) {
                if (model instanceof THREE.Mesh && model.isMesh) {
                    model.castShadow = true;
                }
            });
            if (mod.children && mod.children[0]) {
                mod.children[0].scale.set(
                    item3d.scaleFactor,
                    item3d.scaleFactor,
                    item3d.scaleFactor
                );
            } else {
                mod.scale.set(
                    item3d.scaleFactor,
                    item3d.scaleFactor,
                    item3d.scaleFactor
                );
            }
            mod.position.set(item3d.positionx, item3d.positiony, item3d.positionz);
            mod.position.fromArray(
                this.threeDScene.realTo3dvCoords(
                    item3d.positionx,
                    item3d.positiony,
                    item3d.positionz,
                    item3d.sizex,
                    item3d.sizey,
                    item3d.sizez,
                    this.getScaleForArea(item3d.areaId)
                )
            );
            mod.rotation.fromArray([
                (Math.PI * item3d.rotationx) / 180,
                (Math.PI * item3d.rotationy) / 180,
                (Math.PI * item3d.rotationz) / 180,
            ]);
            mod.castShadow = true;
            mod.receiveShadow = true;
            mod.visible = item3d.areaId == this.state.currentArea.id;

            this.threeDScene.scene.add(mod);

            let plight = new THREE.PointLight(0xffffff, 7, 140, 2); // color : Integer, intensity : Float, distance : Number, decay : Float
            plight.position.set(
                mod.position.x + 20,
                this.threeDScene.config.heightY_3dv,
                mod.position.z + 15
            );
            plight.castShadow = true;
            plight.shadow.mapSize.width = 1024;
            plight.shadow.mapSize.height = 1024;
            plight.shadow.radius = 2;

            this.threeDScene.scene.add(plight);

            this.threeDScene.areaObjects.gltfModels.push(item3d.gltf);
            this.threeDScene.areaObjects.gltfObjects[item3d.gltf] = {
                model: mod,
                light: plight,
                area: item3d.areaId,
            };
        });
    }

    /**
     * Double click event handler
     *
     * On double click on a item3d, we retrieve some information from Odoo about that item3d
     *
     * @param {{ preventDefault?: any; clientX: number; clientY: number; }} event
     */
    async onContainerDoubleClick(event) {
        event.preventDefault();
        if (this.itemInfoPopup.state.visible) {
            return;
        }
        this.barcodeLabel.el.style.display = "none";
        let item3d = this.threeDScene.findObjectOnClick(
            event,
            (obj) => obj.userData.area == this.state.currentArea.id
        );
        if (item3d && item3d instanceof THREE.Mesh) {
            item3d.material.color.setHex(0xbebebe);
            let wireframe = this.threeDScene.scene.getObjectByName(
                "wireframe" + item3d.userData.item3d.id
            );
            if (wireframe && wireframe instanceof THREE.LineSegments) {
                wireframe.material.linewidth = 2;
                wireframe.material.color.setHex(0xa3498b);
            }
            const info = await this.props.loadInfoForObjectId(
                item3d.userData.item3d.id
            );
            this.itemInfoPopup.show(event, item3d.userData.item3d.id);
            this.record = info;
            this.threeDScene.controls.enabled = false;
        }
    }

    /**
     * Mouse move event handler
     *
     * @param {{ clientY: number; clientX: number; }} event
     */
    onContainerMouseMove(event) {
        if (this.coordinatesDisplay.visible && !this.itemInfoPopup.state.visible) {
            this.showCoordinates();
            let item3d = this.threeDScene.findObjectOnClick(
                event,
                (obj) => obj.userData.area == this.state.currentArea.id
            );
            if (item3d) {
                this.barcodeLabel.el.style.display = "block";
                this.barcodeLabel.el.style.left =
                    event.clientX -
                    getOffset(this.sceneDOMContainer.el).left +
                    20 +
                    "px";
                this.barcodeLabel.el.style.top =
                    event.clientY - getOffset(this.sceneDOMContainer.el).top - 5 + "px";
                this.barcodeLabel.el.textContent = item3d.userData.item3d.name;
            } else {
                this.barcodeLabel.el.style.display = "none";
            }
        } else {
            return;
        }
    }

    /**
     * Window resize event handler
     *
     * @private
     */
    onWindowResize() {
        this._setRendererSize();
    }

    /**
     * Fix the renderer size according to the available space on screen
     *
     * @private
     */
    _setRendererSize() {
        let width;
        let height;
        if (this.state.isFullscreen) {
            width = document.body.getBoundingClientRect().width;
            height = document.body.getBoundingClientRect().height;
        } else {
            const contentRect = document
                .querySelector(".o_content")
                .getBoundingClientRect();
            width = contentRect.width;
            height = contentRect.height;
        }
        this.threeDScene.setRendererSize(width, height, this.state.isFullscreen);
        this.state.rendererWidth = width;
        this.state.rendererHeight = height;
    }

    closeItemInfoPopup(e) {
        e.preventDefault();
        var item3d = this.threeDScene.scene.getObjectByName(
            "mesh" + this.itemInfoPopup.state.currentId
        );
        if (item3d && item3d instanceof THREE.Mesh) {
            item3d.material.color = new THREE.Color(item3d.userData.item3d.color);
            var wireframe = this.threeDScene.scene.getObjectByName(
                "wireframe" + item3d.userData.item3d.id
            );
            if (wireframe && wireframe instanceof THREE.LineSegments) {
                wireframe.material.linewidth = 1;
                wireframe.material.color = new THREE.Color(0x4d4d4d);
            }
        }
        this.itemInfoPopup.hide();
        this.threeDScene.controls.enabled = true;
        e.stopPropagation();
    }

    toggleFullscreen() {
        this.state.isFullscreen = !this.state.isFullscreen;
        this.root.el.classList.toggle("fullscreen");
        this._setRendererSize();
    }

    /**
     * Add event handlers
     *
     * @private
     */
    _addEventHandlers() {
        window.addEventListener("resize", this.onWindowResize.bind(this));
    }

    showCoordinates() {
        this.threeDScene.target.visible = true;
        var c = this.threeDScene.realCoords(
            this.threeDScene.camera.position.x,
            this.threeDScene.camera.position.y,
            this.threeDScene.camera.position.z
        );
        var t = this.threeDScene.realCoords(
            this.threeDScene.target.position.x,
            this.threeDScene.target.position.y,
            this.threeDScene.target.position.z
        );
        this.coordinatesDisplay.visible = true;
        this.coordinatesDisplay.text = markup(
            `camera: ${c.x.toFixed(2)}, ${c.y.toFixed(2)}, ${c.z.toFixed(2)}
             <br/>
             target: ${t.x.toFixed(2)}, ${t.y.toFixed(2)}, ${t.z.toFixed(2)}`
        );
    }

    hideCoordinates() {
        this.coordinatesDisplay.visible = false;
        this.threeDScene.target.visible = false;
    }

    /**
     * Add event handlers
     *
     * @private
     */
    _unbindEventHandlers() {
        window.removeEventListener("resize", this.onWindowResize.bind(this));
    }

    get loadingIconAbsolutePosition() {
        return {
            left: this.state.rendererWidth / 2 - 50,
            top: this.state.rendererHeight / 2 - 50,
        };
    }
}

// const components = { TreeItem };
ThreedRenderer.components = {};
ThreedRenderer.defaultProps = {
    noItem: "Nothing is here.",
};
ThreedRenderer.template = "web_threed.ThreedRenderer";
ThreedRenderer.props = {
    all3dItems: {
        type: Array,
        optional: true,
    },
    selected3dItems: {
        type: Array,
        optional: true,
    },
    noAreaLoaded: {
        type: String,
        optional: true,
    },
    noItem: {
        type: String,
        optional: true,
    },
    selectedGroundAreaId: {
        type: Number,
        optional: true,
    },
    loadInfoForObjectId: {
        type: Function,
        optional: true,
    },
    groundAreas: {
        type: Array,
    },
    cameraConfig: {
        type: Object,
        optional: true,
    },
    templates: {
        type: Object,
        optional: true,
    },
};

export default ThreedRenderer;
