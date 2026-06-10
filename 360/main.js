import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js';

// ═══════════════════════════════════════════════════════════════════════════════
//  CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

// Center stone can change by shape
const SHAPES = {
    RND: {
        stoneFile: 'assets/RND.gltf',
        ringFile: 'assets/Ring_17346_JV_RND_100.gltf',
        crownFrac: 0.505,
        label: 'Round',
        sideAnchorPattern: /SIDE_Anchor/i,
        icon: '⬤',
    },
    OVL: {
        stoneFile: 'assets/OVL.gltf',
        ringFile: 'assets/Ring_17346_JV_OVL_100.gltf',
        crownFrac: 0.505,
        label: 'Oval',
        sideAnchorPattern: /SIDE_Anchor/i,
        icon: '⬭',
    },
    CSH: {
        stoneFile: 'assets/CSH.gltf',
        ringFile: 'assets/Ring_17346_JV_CSH_100.gltf',
        crownFrac: 0.505,
        label: 'Cushion',
        sideAnchorPattern: /SIDE_Anchor/i,
        icon: '⬮',
    },
    PRNC: {
        stoneFile: 'assets/PRNC.gltf',
        ringFile: 'assets/Ring_17346_JV_PRNC_100.gltf',
        crownFrac: 0.505,
        label: 'Princess',
        sideAnchorPattern: /SIDE_Anchor/i,
        icon: '■',
    }
};

// Side stones should ALWAYS be round
const SIDE_STONE_SHAPE = 'RND';

// Mat names confirmed from GLTF inspection:
//   Mat_Gold_002 → band  (colour changes with selector)
//   Mat_Gold_001 → prongs (fixed platinum white)
const BAND_MAT_NAME = 'Mat_Gold_002';
const PRONG_MAT_NAME = 'Mat_Gold_001';

const METALS = {
    platinum: {
        color: 0xD9DADD,
        roughness: 0.10,
        label: 'Platinum',
        swatch: 'linear-gradient(135deg,#f0f0f0,#bfbfbf)'
    },
    whitegold14k: {
        color: 0xE5E7E9,
        roughness: 0.16,
        label: '14K White Gold',
        swatch: 'linear-gradient(135deg,#f1efe6,#c9c4b3)'
    },
    yellowgold14k: {
        color: 0xE7C58F,
        roughness: 0.18,
        label: '14K Yellow Gold',
        swatch: 'linear-gradient(135deg,#f3d06a,#c6971d)'
    },
    rosegold14k: {
        color: 0xE3B09A,
        roughness: 0.20,
        label: '14K Rose Gold',
        swatch: 'linear-gradient(135deg,#e4b09a,#b06a53)'
    },
    whitegold18k: {
        color: 0xECEDEF,
        roughness: 0.14,
        label: '18K White Gold',
        swatch: 'linear-gradient(135deg,#f3f0e7,#cdc7b7)'
    },
    yellowgold18k: {
        color: 0xEED4A3,
        roughness: 0.16,
        label: '18K Yellow Gold',
        swatch: 'linear-gradient(135deg,#f5d77a,#c89d22)'
    },
};

// ═══════════════════════════════════════════════════════════════════════════════
//  RENDERER / SCENE
// ══════════════════════════════
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(25, window.innerWidth / window.innerHeight, 0.0001, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.2;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.getElementById('container').appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.autoRotate = true;
controls.autoRotateSpeed = 1.5;

// ═══════════════════════════════════════════════════════════════════════════════
//  LOADERS
// ═══════════════════════════════════════════════════════════════════════════════

const dracoLoader = new DRACOLoader();
dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');
const gltfLoader = new GLTFLoader();
gltfLoader.setDRACOLoader(dracoLoader);

// ═══════════════════════════════════════════════════════════════════════════════
//  MATERIALS
// ═══════════════════════════════════════════════════════════════════════════════

// Diamond — main stone (fully transparent, glass-like with spectral fire)
const diamondMat = new THREE.MeshPhysicalMaterial({
    color: 0xffffff,
    metalness: 0,
    roughness: 0,
    transmission: 1.0,
    thickness: 1.2,
    ior: 2.417,
    dispersion: 0.6,
    envMapIntensity: 4.5,
    clearcoat: 1.0,
    clearcoatRoughness: 0.0,
    reflectivity: 1.0,
    transparent: true,
    opacity: 1,
    side: THREE.DoubleSide,
    depthWrite: false,
});

diamondMat.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
        '#include <common>',
        `
        #include <common>
        vec3 spectralFire(float intensity) {
            vec3 c;
            c.r = sin(intensity * 6.283 + 0.0) * 0.5 + 0.5;
            c.g = sin(intensity * 6.283 + 2.0) * 0.5 + 0.5;
            c.b = sin(intensity * 6.283 + 4.0) * 0.5 + 0.5;
            return c;
        }
        `
    );
    shader.fragmentShader = shader.fragmentShader.replace(
        '#include <output_fragment>',
        `
        float viewAngle   = dot(normalize(vViewPosition), normal);
        float fireStrength = pow(1.0 - abs(viewAngle), 3.0);
        vec3  fire         = spectralFire(viewAngle * 2.0);
        gl_FragColor.rgb  += fire * fireStrength * 0.6;
        #include <output_fragment>
        `
    );
};

// Side-stone diamond — same optical properties, slightly lighter dispersion
// so they complement rather than compete with the centre stone.
const sideDiamondMat = new THREE.MeshPhysicalMaterial({
    color: 0xffffff,
    metalness: 0,
    roughness: 0,
    transmission: 1.0,
    thickness: 0.6,
    ior: 2.417,
    dispersion: 0.4,
    envMapIntensity: 3.5,
    clearcoat: 1.0,
    clearcoatRoughness: 0.0,
    reflectivity: 1.0,
    transparent: true,
    opacity: 1,
    side: THREE.DoubleSide,
    depthWrite: false,
});

sideDiamondMat.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
        '#include <common>',
        `
        #include <common>
        vec3 spectralFire(float intensity) {
            vec3 c;
            c.r = sin(intensity * 6.283 + 0.0) * 0.5 + 0.5;
            c.g = sin(intensity * 6.283 + 2.0) * 0.5 + 0.5;
            c.b = sin(intensity * 6.283 + 4.0) * 0.5 + 0.5;
            return c;
        }
        `
    );
    shader.fragmentShader = shader.fragmentShader.replace(
        '#include <output_fragment>',
        `
        float viewAngle    = dot(normalize(vViewPosition), normal);
        float fireStrength = pow(1.0 - abs(viewAngle), 3.0);
        vec3  fire         = spectralFire(viewAngle * 2.0);
        gl_FragColor.rgb  += fire * fireStrength * 0.45;
        #include <output_fragment>
        `
    );
};

// Band — colour controlled by metal selector
const bandMat = new THREE.MeshPhysicalMaterial({
    color: 0xE6C15A,
    metalness: 1.0,
    roughness: 0.18,
    reflectivity: 1.0,
    clearcoat: 1.0,
    clearcoatRoughness: 0.03,
    envMapIntensity: 2.5,
});

bandMat.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
        '#include <common>',
        `
        #include <common>
        float fresnel(vec3 viewDir, vec3 normal) {
            return pow(1.0 - dot(viewDir, normal), 3.0);
        }
        `
    );
    shader.fragmentShader = shader.fragmentShader.replace(
        '#include <output_fragment>',
        `
        float f = fresnel(normalize(vViewPosition), normal);
        gl_FragColor.rgb += vec3(0.8, 0.6, 0.2) * f * 0.25;
        #include <output_fragment>
        `
    );
};

// Prongs — always platinum white, never changes
const prongMat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(0xdcdcda),
    metalness: 1.0,
    roughness: 0.04,
    envMapIntensity: 1.5,
});

// ═══════════════════════════════════════════════════════════════════════════════
//  HDRI ENVIRONMENT
// ═══════════════════════════════════════════════════════════════════════════════

new RGBELoader().load('assets/environment.hdr', (texture) => {
    texture.mapping = THREE.EquirectangularReflectionMapping;
    scene.environment = texture;
    scene.environmentIntensity = 2.5;
});

// ═══════════════════════════════════════════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════════════════════════════════════════

let currentShape = 'RND';
let currentMetal = 'platinum';
let activeRing = null;
let isLoading = false;

// ═══════════════════════════════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Attach a stone to an anchor by cloning the entire GLTF scene.
 * This preserves the original GLTF transforms, so the stone sits
 * exactly where the exporter intended (relative to the anchor origin).
 *
 * @param {THREE.Object3D} anchor       - the anchor node in the ring scene
 * @param {THREE.Object3D} stoneScene   - the loaded GLTF scene root
 * @param {THREE.Material} mat          - material to assign to all meshes
 * @param {number}         [scale=1]    - optional corrective uniform scale
 */
function attachStone(anchor, stoneScene, mat, scale = 1) {
    const clone = stoneScene.clone(true);
    if (scale !== 1) {
        clone.scale.multiplyScalar(scale);
    }
    clone.traverse(child => {
        if (child.isMesh) {
            child.material = mat;
        }
    });
    anchor.add(clone);
}

/**
 * Check if a stone GLTF needs a corrective scale.
 * Some GLTFs (e.g. PRNC) have geometry in centimeters (no 0.01 scale node),
 * while others (RND, OVL, CSH) already have scale=0.01 baked in their node.
 */
function getCorrectiveScale(gltfScene) {
    const box = new THREE.Box3().setFromObject(gltfScene);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    if (maxDim > 0.05) {
        return 0.01;
    }
    return 1;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  LOAD VIEWER  (ring + stones)
// ═══════════════════════════════════════════════════════════════════════════════

async function loadViewer(shapeKey) {
    if (isLoading) return;
    isLoading = true;
    showLoader(true);

    const cfg = SHAPES[shapeKey];
    const sideCfg = SHAPES[SIDE_STONE_SHAPE];

    try {
        // Remove old ring
        if (activeRing) {
            scene.remove(activeRing);
            activeRing = null;
        }

        // Load center stone GLTF — keep the full scene graph intact
        const centerStoneGLTF = await gltfLoader.loadAsync(cfg.stoneFile);
        const centerStoneScene = centerStoneGLTF.scene;
        const centerScale = getCorrectiveScale(centerStoneScene);

        // Load side stone GLTF (always round)
        const sideStoneGLTF = await gltfLoader.loadAsync(sideCfg.stoneFile);
        const sideStoneScene = sideStoneGLTF.scene;
        const sideScale = getCorrectiveScale(sideStoneScene);

        // Dynamically discover ring parts
        let availableAssets = [];
        try {
            const assetRes = await fetch('assets/asset_list.json');
            if (assetRes.ok) availableAssets = await assetRes.json();
        } catch(e) { console.warn("No asset_list.json found"); }

        let ringGltfPath = cfg.ringFile; // Fallback
        let shankGltfPath = null;
        let headGltfPath = null;

        for (const file of availableAssets) {
            if (file.startsWith('Ring_') && file.endsWith('.gltf')) ringGltfPath = 'assets/' + file;
            if (file.startsWith('Shank_') && file.endsWith('.gltf')) shankGltfPath = 'assets/' + file;
            if (file.startsWith('Head_') && file.endsWith('.gltf')) headGltfPath = 'assets/' + file;
        }

        let ring;
        if (shankGltfPath && headGltfPath) {
            const shankGLTF = await gltfLoader.loadAsync(shankGltfPath);
            const headGLTF = await gltfLoader.loadAsync(headGltfPath);
            ring = shankGLTF.scene;
            const head = headGLTF.scene;
            
            // Connect modular parts
            const shankAnchor = ring.getObjectByName('ConnectionAnchor') || ring.getObjectByName('MainAnchor');
            if (shankAnchor) {
                if (shankAnchor.name === 'MainAnchor') shankAnchor.name = "ShankAnchor";
                shankAnchor.add(head);
            } else {
                ring.add(head);
            }
        } else {
            const ringGLTF = await gltfLoader.loadAsync(ringGltfPath);
            ring = ringGLTF.scene;
        }

        // Assign band / prong materials
        ring.traverse(child => {
            if (!child.isMesh) return;

            const mName = child.material?.name ?? '';

            if (mName === BAND_MAT_NAME) {
                child.material = bandMat.clone();
                child.userData.role = 'band';
            }
            else if (mName === PRONG_MAT_NAME) {
                child.material = prongMat.clone();
                child.userData.role = 'prong';
            }
            else {
                // IMPORTANT: don't accidentally color random meshes
                child.material = prongMat.clone();
                child.userData.role = 'prong';
            }
        });

        // Main stone at MainAnchor — preserve full GLTF scene transforms
        const mainAnchor = ring.getObjectByName('MainAnchor');
        if (mainAnchor) {
            attachStone(mainAnchor, centerStoneScene, diamondMat.clone(), centerScale);
        }

        // Side stones at SIDE_Anchor nodes, always round
        ring.traverse(node => {
            if (!cfg.sideAnchorPattern.test(node.name)) return;
            attachStone(node, sideStoneScene, sideDiamondMat.clone(), sideScale);
        });

        // Fit camera
        const box = new THREE.Box3().setFromObject(ring);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);

        ring.position.sub(center);

        camera.near = maxDim * 0.001;
        camera.far = maxDim * 100;
        camera.position.set(0, maxDim * 0.3, maxDim * 3.5);
        camera.updateProjectionMatrix();

        controls.target.set(0, 0, 0);
        controls.minDistance = maxDim * 1.1;
        controls.maxDistance = maxDim * 8;
        controls.update();

        scene.add(ring);
        activeRing = ring;

        // Re-apply selected metal after reload
        applyMetal(currentMetal);

    } catch (err) {
        console.error('Viewer error:', err);
    }

    isLoading = false;
    showLoader(false);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  APPLY METAL  (live update — no reload)
// ═══════════════════════════════════════════════════════════════════════════════

function applyMetal(metalKey) {
    const m = METALS[metalKey];
    if (!activeRing) return;

    activeRing.traverse(child => {
        if (!child.isMesh) return;

        if (child.userData.role === 'band' || child.userData.role === 'prong') {
            child.material.color.set(m.color);
            child.material.roughness = m.roughness;
            child.material.needsUpdate = true;
        }
    });
}

// ═══════════════════════════════════════════════════════════════════════════════
//  ANIMATION LOOP
// ═══════════════════════════════════════════════════════════════════════════════

(function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
})();

// ═══════════════════════════════════════════════════════════════════════════════
//  UI — inject panel + styles
// ═══════════════════════════════════════════════════════════════════════════════

function buildUI() {

    document.head.insertAdjacentHTML('beforeend', `<style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body { overflow: hidden; background: #f0ede8; }
        #container { position: fixed; inset: 0; }

        #jv-panel {
            position: fixed;
            bottom: 28px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            gap: 0;
            background: rgba(255,255,255,0.94);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(0,0,0,0.09);
            border-radius: 22px;
            padding: 14px 24px;
            box-shadow: 0 12px 40px rgba(0,0,0,0.14);
            z-index: 10;
            white-space: nowrap;
        }
        .jv-section {
            display: flex; flex-direction: column; align-items: center;
            gap: 8px; padding: 0 20px;
        }
        .jv-section:first-child { padding-left: 0; }
        .jv-section:last-child  { padding-right: 0; }
        .jv-section-title {
            font: 700 9px/1 'Helvetica Neue', sans-serif;
            letter-spacing: 0.2em; text-transform: uppercase; color: #b0a898;
        }
        .jv-row { display: flex; gap: 8px; }
        .jv-divider { width: 1px; height: 52px; background: rgba(0,0,0,0.09); flex-shrink: 0; }

        .jv-shape {
            display: flex; flex-direction: column; align-items: center; gap: 5px;
            padding: 9px 20px; border: 1.5px solid #e0dbd4; border-radius: 14px;
            background: #fdfcfb; cursor: pointer; transition: all 0.18s ease;
            min-width: 72px; font-family: inherit;
        }
        .jv-shape:hover { border-color: #c0b8ae; }
        .jv-shape.active { background: #1a1a1a; border-color: #1a1a1a; color: #fff; }
        .jv-shape-icon  { font-size: 18px; line-height: 1; }
        .jv-shape-label { font: 10px/1 'Helvetica Neue', sans-serif; letter-spacing: 0.04em; }

        .jv-metal {
            display: flex; flex-direction: column; align-items: center; gap: 6px;
            padding: 8px 16px; border: 1.5px solid #e0dbd4; border-radius: 14px;
            background: #fdfcfb; cursor: pointer; transition: all 0.18s ease;
            min-width: 76px; font-family: inherit;
        }
        .jv-metal:hover { border-color: #c0b8ae; }
        .jv-metal.active { border-color: #1a1a1a; box-shadow: 0 0 0 1.5px #1a1a1a; }
        .jv-swatch {
            width: 28px; height: 28px; border-radius: 50%;
            border: 1.5px solid rgba(0,0,0,0.12);
            box-shadow: inset 0 -3px 6px rgba(0,0,0,0.18), 0 2px 4px rgba(0,0,0,0.08);
        }
        .jv-metal-label { font: 9px/1 'Helvetica Neue', sans-serif; letter-spacing: 0.07em; color: #666; }
        .jv-metal.active .jv-metal-label { color: #1a1a1a; font-weight: 600; }

        #jv-loader {
            position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
            background: rgba(240,237,232,0.75); backdrop-filter: blur(6px);
            z-index: 20; transition: opacity 0.3s;
        }
        #jv-loader.hidden { opacity: 0; pointer-events: none; }
        .jv-spinner {
            width: 40px; height: 40px; border: 2.5px solid #ddd; border-top-color: #666;
            border-radius: 50%; animation: jv-spin 0.75s linear infinite;
        }
        @keyframes jv-spin { to { transform: rotate(360deg); } }

        @media (max-width: 520px) {
            #jv-panel { flex-direction: column; gap: 12px; border-radius: 18px; padding: 16px 20px; }
            .jv-divider { width: 80%; height: 1px; }
            .jv-section { padding: 0; }
        }
    </style>`);

    document.body.insertAdjacentHTML('beforeend', `
        <div id="jv-loader"><div class="jv-spinner"></div></div>
    `);

    const panel = document.createElement('div');
    panel.id = 'jv-panel';

    // Shape section
    const shapeSection = document.createElement('div');
    shapeSection.className = 'jv-section';
    shapeSection.innerHTML = '<div class="jv-section-title">Shape</div>';
    const shapeRow = document.createElement('div');
    shapeRow.className = 'jv-row';

    Object.entries(SHAPES).forEach(([key, cfg]) => {
        const btn = document.createElement('button');
        btn.className = `jv-shape${key === currentShape ? ' active' : ''}`;
        btn.innerHTML = `<span class="jv-shape-icon">${cfg.icon}</span><span class="jv-shape-label">${cfg.label}</span>`;
        btn.addEventListener('click', () => {
            if (key === currentShape || isLoading) return;
            panel.querySelectorAll('.jv-shape').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentShape = key;
            loadViewer(key);
        });
        shapeRow.appendChild(btn);
    });
    shapeSection.appendChild(shapeRow);

    const divider = document.createElement('div');
    divider.className = 'jv-divider';

    // Metal section
    const metalSection = document.createElement('div');
    metalSection.className = 'jv-section';
    metalSection.innerHTML = '<div class="jv-section-title">Metal</div>';
    const metalRow = document.createElement('div');
    metalRow.className = 'jv-row';

    Object.entries(METALS).forEach(([key, m]) => {
        const btn = document.createElement('button');
        btn.className = `jv-metal${key === currentMetal ? ' active' : ''}`;
        btn.innerHTML = `
            <div class="jv-swatch" style="background:${m.swatch}"></div>
            <span class="jv-metal-label">${m.label}</span>
        `;
        btn.addEventListener('click', () => {
            if (key === currentMetal) return;
            panel.querySelectorAll('.jv-metal').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMetal = key;
            applyMetal(key);
        });
        metalRow.appendChild(btn);
    });
    metalSection.appendChild(metalRow);

    panel.appendChild(shapeSection);
    panel.appendChild(divider);
    panel.appendChild(metalSection);
    document.body.appendChild(panel);
}

function showLoader(visible) {
    document.getElementById('jv-loader')?.classList.toggle('hidden', !visible);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  RESIZE
// ═══════════════════════════════════════════════════════════════════════════════

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// ═══════════════════════════════════════════════════════════════════════════════
//  BOOT
// ═══════════════════════════════════════════════════════════════════════════════

buildUI();
loadViewer(currentShape);