import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
// We can't easily run Three.js without a DOM unless we use headless-gl or something.
// But we can just use python to read the min/max from the accessors in GLTF!
