/** @odoo-module **/
const {useState, useRef, onPatched, onMounted, onWillDestroy} = owl;

/**
 * @typedef SceneConfig
 * @property {number} [groundX_real]
 * @property {number} [groundY_real]
 * @property {number} [heightZ_real]
 * @property {number} [camPosX_real]
 * @property {number} [camPosY_real]
 * @property {number} [camPosZ_real]
 * @property {number} [camFov]
 * @property {number} [targetX_real]
 * @property {number} [targetY_real]
 * @property {number} [targetZ_real]
 * @property {number} [groundX_3dv]
 * @property {number} [groundZ_3dv]
 * @property {number} [heightY_3dv]
 * @property {number} [scale]
 * @property {string} [planimetryImage]
 */

/**
 * Hook to manage the 3D scene.
 *
 * This hook is used to manage the 3D scene. It is used by the 3D view.
 *
 * @param {string} containerRef will be used to get the container element via useRef hook
 * @param {SceneConfig} initConfig
 *
 */
export function useThreedScene(containerRef, initConfig) {
    const sceneContainerRef = useRef(containerRef);

    /** @type {import("three/src/Three").PerspectiveCamera} */
    let camera = undefined;
    /** @type {import("three/examples/jsm/controls/OrbitControls").OrbitControls} */
    let controls = undefined;
    /** @type {import("three/src/Three").WebGLRenderer} */
    let renderer = undefined;
    /** @type {import("three/src/Three").Scene} */
    let scene = undefined;
    /** @type {import("three/src/Three").Mesh} */
    let target = undefined;
    /** @type {import("three/src/Three").Raycaster} */
    let raycaster = undefined;
    /** @type {import("three/src/Three").Vector2} */
    let mouse = undefined;
    let areaObjects = {
        wireframes: [], // for all items3d
        meshes: [], // for selected items3d
        gltfModels: [], // for rendered GLTF models
        gltfObjects: {}, // a container of GLTF objects and their accessories
    };
    /** @type {SceneConfig} */
    const config = useState(initConfig);
    let GLTFLoader = new THREE.GLTFLoader();
    let JSONObjectLoader = new THREE.ObjectLoader(); // see https://threejs.org/docs/#api/en/loaders/ObjectLoader

    onPatched(() => {
        renderScene();
    });

    onMounted(() => {
        console.log("mounted in Hook");
        init3d();
    });

    onWillDestroy(() => {
        console.log("will destroy in Hook");
        $(window).off("resize");
        try {
            scene.traverse(dispose);
            for (const [_key, value] of Object.entries(areaObjects)) {
                if (Array.isArray(value) && value.length > 0) {
                    value.forEach(dispose);
                }
            }
            scene = undefined;
            controls.dispose();
            renderer.dispose();
            renderer = null;
            raycaster = null;
            mouse = null;
            JSONObjectLoader = null;
            GLTFLoader = null;
            areaObjects = null;
        } catch (e) {
            console.error("Cleanup THREE.js object error", e);
        }

        function dispose(threeJSObject) {
            if (threeJSObject.geometry) {
                threeJSObject.geometry.dispose();
            }
            if (threeJSObject.material) {
                if (Array.isArray(threeJSObject.material)) {
                    threeJSObject.material.forEach((mtl) => mtl.dispose());
                } else {
                    threeJSObject.material.dispose();
                }
            }
        }
    });

    /**
     * @param {SceneConfig} newConfig
     */
    function setConfig(newConfig) {
        Object.assign(config, newConfig);
    }

    /**
     * Initialize threejs world
     *
     * @private
     */
    function init3d() {
        // camera
        camera = new THREE.PerspectiveCamera(
            config.camFov,
            window.innerWidth / window.innerHeight,
            1,
            3000
        );
        camera.position.fromArray(
            realTo3dvSizes(
                config.camPosX_real,
                -config.camPosY_real,
                config.camPosZ_real
            )
        );
        // controls
        controls = new THREE.OrbitControls(camera, sceneContainerRef.el);
        controls.rotateSpeed = 1.0;
        controls.zoomSpeed = 1.2;
        controls.panSpeed = 0.8;
        controls.enableZoom = true;
        controls.enablePan = true;
        controls.enableDamping = true;
        controls.dampingFactor = 0.3;
        controls.addEventListener("change", renderScene);

        // raycaster
        raycaster = new THREE.Raycaster();
        mouse = new THREE.Vector2();

        // world
        scene = new THREE.Scene();

        // target object to camera
        target = new THREE.Mesh(
            new THREE.BoxGeometry(4, 4, 4),
            new THREE.MeshPhongMaterial({
                color: new THREE.Color("red"),
                opacity: 1,
                transparent: true,
            })
        );
        target.position.fromArray(
            realTo3dvSizes(
                config.targetX_real,
                -config.targetY_real,
                config.targetZ_real
            )
        );
        target.name = "target";
        target.visible = false;
        scene.add(target);

        camera.updateProjectionMatrix();

        // lights
        scene.add(new THREE.AmbientLight(0xffffff));

        // renderer
        renderer = new THREE.WebGLRenderer({antialias: true});
        renderer.setClearColor(0xdfdfdf);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;
        sceneContainerRef.el.appendChild(renderer.domElement);
        camera.lookAt(target.position);
        camera.userData.scene = scene;
        controls.target.copy(target.position);
        controls.update();
    }

    /**
     * Fix the renderer size according to the available space on screen
     * @param {number} width
     * @param {number} height
     * @param {boolean} [fullwidth=false]
     * @private
     */
    function setRendererSize(width, height, fullwidth = false) {
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        if (fullwidth) {
            renderer.setSize(width, height);
        } else {
            renderer.setSize(width - 20, height - 20);
        }
    }

    /**
     * Map millimeters to 3js units (only sizes)
     *
     * @private
     * @param {number} x
     * @param {number} y
     * @param {number} z
     * @param {number} [scale]
     * @returns {[number, number, number]} a three-items array of sizes, scaled
     */
    function realTo3dvSizes(x, y, z, scale = config.scale) {
        return [x / scale, z / scale, y / scale];
    }

    /**
     * Map millimeters to 3js units (coordinates and sizes)
     *
     * @private
     * @param {number} x
     * @param {number} y
     * @param {number} z
     * @param {number} sizex
     * @param {number} sizey
     * @param {number} sizez
     * @param {number} [scale]
     * @returns {[number, number, number]} a three-items array of coordinates, scaled
     */
    function realTo3dvCoords(x, y, z, sizex, sizey, sizez, scale = config.scale) {
        return [
            (x + sizex / 2) / scale,
            (z + sizez / 2) / scale,
            -(y + sizey / 2) / scale,
        ];
    }

    /**
     * Map 3js units to millimeters, creating an object
     *
     * @private
     * @returns {{x:number; y:number; z:number}} an object with 'x', 'y', and 'z' properties
     */
    function realCoords(xcoord, y, z, scale = config.scale) {
        return {
            x: Math.round(xcoord * scale),
            y: -Math.round(z * scale),
            z: Math.round(y * scale),
        };
    }

    /**
     * Add an actual object to the scene.
     *
     * This called by addMesh() and addWireframe.
     * The object will be a BoxGeometry. According to the second parameter, it will be a mesh
     * or a wireframe.
     *
     * The object will be added both to the scene and to the warehouseObjects collection.
     * @param {import("../web_threed_model").Item3d} item3d
     * @param {'mesh' | 'wireframe'} type , either 'mesh' or 'wireframe'
     * @param {number} defaultScale
     */
    function addObject(item3d, type, defaultScale) {
        const size = realTo3dvSizes(
            item3d.sizex,
            item3d.sizey,
            item3d.sizez,
            defaultScale
        );

        let geometry;
        let scale_factor = 1;
        /** @type {import("three/src/Three").Object3D | undefined} */
        let customObj = undefined;
        /** @type {"meshes" | "wireframes"} */
        let key = undefined;

        if (item3d.geometry) {
            customObj = JSONObjectLoader.parse(JSON.parse(atob(item3d.geometry)));
            scale_factor = item3d.scaleFactor;
        } else {
            geometry = new THREE.BoxGeometry(size[0], size[1], size[2]);
        }

        switch (type) {
            case "mesh":
                let meshPongMaterial = new THREE.MeshPhongMaterial({
                    color: new THREE.Color(item3d.color),
                    flatShading: true,
                    opacity: item3d.opacity / 1000,
                    transparent: true,
                });
                // var obj = new THREE.Mesh( geometry, material );
                if (item3d.geometry) {
                    obj = customObj;

                    obj.traverse(function (child) {
                        if (child instanceof THREE.Mesh && child.isMesh) {
                            child.material = meshPongMaterial;
                            child.userData.item3d = item3d;
                            child.userData.area = item3d.areaId;
                            child.userData.parent = customObj;
                            areaObjects["meshes"].push(child);
                        }
                    });

                    obj.scale.set(scale_factor, scale_factor, scale_factor);
                    //obj.updateMatrix();
                } else {
                    obj = new THREE.Mesh(geometry, meshPongMaterial);
                }
                obj.receiveShadow = true;
                key = "meshes";
                break;
            case "wireframe":
                let lineBasicMaterial = new THREE.LineBasicMaterial({
                    color: 0x4d4d4d,
                    linewidth: 1,
                });

                var obj;

                if (item3d.geometry) {
                    obj = new THREE.Group();

                    customObj.traverse(function (child) {
                        if (child instanceof THREE.Mesh && child.isMesh) {
                            var wf = new THREE.LineSegments(
                                new THREE.WireframeGeometry(child.geometry),
                                lineBasicMaterial
                            );
                            wf.position.copy(child.position);
                            wf.rotation.copy(child.rotation);
                            obj.add(wf);
                        }
                    });
                    obj.scale.set(scale_factor, scale_factor, scale_factor);
                } else {
                    var edges = new THREE.EdgesGeometry(geometry); // or WireframeGeometry
                    obj = new THREE.LineSegments(edges, lineBasicMaterial);
                }
                key = "wireframes";
                break;
        }

        obj.position.fromArray(
            realTo3dvCoords(
                item3d.positionx,
                item3d.positiony,
                item3d.positionz,
                item3d.sizex,
                item3d.sizey,
                item3d.sizez,
                defaultScale
            )
        );
        /* LORIS
          if (!item3d.gltf) {
              obj.rotation.fromArray([
                  Math.PI*parseInt(item3d.rotx, 10)/180,
                  Math.PI*parseInt(item3d.roty, 10)/180,
                  Math.PI*parseInt(item3d.rotz, 10)/180,
              ]);
          }
          */
        obj.name = type + item3d.id;
        obj.userData.item3d = item3d;
        obj.userData.area = item3d.areaId;
        obj.visible = true;
        scene.add(obj);
        areaObjects[key].push(obj);
    }

    /**
     * Remove an object from the 3D scene.
     *
     * @param the name of the object, as defined in the object itself before being added to the scene
     * @private
     */
    function removeObject(name) {
        var object = scene.getObjectByName(name);
        if (object) {
            scene.remove(object);
            if (object instanceof THREE.Mesh) object.geometry.dispose();
            if (object instanceof THREE.Mesh) object.material.dispose();
        }
    }

    /**
     * Create the ground by placing the image stored in the database.
     *
     * This function uses the information stored in the currentArea object.
     *
     * @private
     */
    function renderGround() {
        // we remove the ground that might be there
        removeObject("ground");
        removeObject("underground");
        removeObject("grid");

        var groundImage = document.createElement("img");
        var texture = new THREE.Texture(groundImage);
        groundImage.onload = () => {
            texture.needsUpdate = true;
            renderScene();
        };
        groundImage.src = "data:image/png;base64," + config.planimetryImage;
        texture.wrapS = THREE.ClampToEdgeWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;

        var groundGeometry = new THREE.BoxGeometry(
            config.groundX_3dv,
            2,
            config.groundZ_3dv
        );
        var groundMaterial = new THREE.MeshStandardMaterial({
            map: texture,
            flatShading: true,
        });
        var ground = new THREE.Mesh(groundGeometry, groundMaterial);
        ground.position.fromArray(
            realTo3dvCoords(0, 0, 0, config.groundX_real, config.groundY_real, 0)
        ).y = -1;

        // the mesh used for the ground will show its texture on the under face, which we don't want
        // so, here's a simple hack: we create a different mesh just to cover it
        var underground = new THREE.Mesh(
            new THREE.BoxGeometry(config.groundX_3dv, 2, config.groundZ_3dv),
            new THREE.MeshPhongMaterial({
                color: new THREE.Color("gray"),
                opacity: 1,
                transparent: false,
            })
        );
        underground.position.fromArray(
            realTo3dvCoords(0, 0, 0, config.groundX_real, config.groundY_real, 0)
        ).y = -3;
        ground.name = "ground";
        underground.name = "underground";
        scene.add(ground);
        scene.add(underground);

        var grid = new THREE.GridHelper(
            2000,
            (2 * config.groundX_real) / config.groundX_3dv
        );
        grid.position.x = config.groundX_3dv / 2;
        grid.position.y = -1;
        grid.position.z = -config.groundZ_3dv / 2;
        grid.name = "grid";
        scene.add(grid);
    }

    /**
     * Find a item3d by using the raycaster.
     *
     * This function only searches the meshes array (thus, only selected items3d)
     *
     * @param {{ clientX: number; clientY: number; }} event
     * @param {(object:any) => boolean} filterCallback
     * @returns {Object | null}
     */
    function findObjectOnClick(event, filterCallback) {
        mouse.x =
            ((event.clientX - $(sceneContainerRef.el).offset().left - 10) /
                renderer.domElement.clientWidth) *
                2 -
            1;
        mouse.y =
            -(
                (event.clientY - $(sceneContainerRef.el).offset().top - 10) /
                renderer.domElement.clientHeight
            ) *
                2 +
            1;
        raycaster.setFromCamera(mouse, camera);

        var intersects = raycaster.intersectObjects(
            areaObjects.meshes.filter(filterCallback)
        );
        if (intersects.length > 0) {
            return intersects[0].object;
        }
        return null;
    }

    /**
     * Call the actual ThreeJS Renderer
     *
     * @private
     */
    function renderScene() {
        // console.log("controls.target", controls.target);
        if (target && renderer) {
            target.position.copy(controls.target);
            renderer.render(scene, camera);
        }
    }

    return {
        renderGround,
        renderScene,
        realTo3dvSizes,
        realTo3dvCoords,
        realCoords,
        addObject,
        setRendererSize,
        setConfig,
        removeObject,
        findObjectOnClick,
        GLTFLoader,
        JSONObjectLoader,
        get renderer() {
            return renderer;
        },
        get areaObjects() {
            return areaObjects;
        },
        get mouse() {
            return mouse;
        },
        get raycaster() {
            return raycaster;
        },
        get target() {
            return target;
        },
        get scene() {
            return scene;
        },
        get controls() {
            return controls;
        },
        get camera() {
            return camera;
        },
        get config() {
            return config;
        },
    };
}
