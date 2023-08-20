/** @odoo-module **/

const {useEffect, useState, useRef} = owl;

/**
 * @param {string} popupRef
 * @param {string} containerRef
 */
export function useAbsoluteThreedPopUp(popupRef, containerRef) {
    const state = useState({
        visible: false,
        mousePositionX: 0,
        mousePositionY: 0,
        currentId: 0,
    });
    const infoPopupRef = useRef(popupRef);
    const sceneContainerRef = useRef(containerRef);

    useEffect(_popUpPositionRenderer, () => [
        infoPopupRef,
        state.visible,
        state.mousePositionX,
        state.mousePositionY,
        sceneContainerRef,
    ]);

    /**
     * @param {{ el: HTMLDivElement; }} popupRef
     * @param {boolean} showPopUp
     * @param {number} mousePositionX
     * @param {number} mousePositionY
     * @param {{ el: HTMLDivElement; }} sceneContainerRef
     */
    function _popUpPositionRenderer(
        popupRef,
        showPopUp,
        mousePositionX,
        mousePositionY,
        sceneContainerRef
    ) {
        if (showPopUp) {
            const $popup = $(popupRef.el);
            const $container = $(sceneContainerRef.el);
            $popup.css({
                top: mousePositionY - $container.offset().top - 10,
                left: mousePositionX - $container.offset().left - 10,
            });
            if (parseInt($popup.css("right"), 10) < 0) {
                $popup.css(
                    "left",
                    mousePositionX - $container.offset().left - $popup.width() - 30
                );
            }
            if (parseInt($popup.css("bottom"), 10) < 0) {
                $popup.css(
                    "top",
                    mousePositionY - $container.offset().top - $popup.height() - 30
                );
            }
            if (parseInt($popup.css("bottom"), 10) < 0) {
                $popup.css(
                    "top",
                    mousePositionY - $container.offset().top - $popup.height() - 30
                );
            }
        }
    }

    /**
     * @param {{ clientX: any; clientY: any; }} event
     * @param {any} currentId
     */
    function show(event, currentId) {
        Object.assign(state, {
            visible: true,
            currentId: currentId,
            mousePositionX: event.clientX,
            mousePositionY: event.clientY,
        });
    }

    function hide() {
        Object.assign(state, {
            visible: false,
            mousePositionX: 0,
            mousePositionY: 0,
            currentId: 0,
        });
    }

    return {
        state,
        show,
        hide,
    };
}
