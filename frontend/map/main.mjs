import { createMap } from './map-component.mjs';
import { mount } from './controller.mjs';
mount(document, (element, scene, pick) => createMap(window.L, element, scene, pick));
