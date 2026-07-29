import './style.scss';

const canvas = document.getElementById('canvas') as HTMLCanvasElement;
const canvasContainer = document.querySelector('.canvas_container') as HTMLDivElement;
const dpr = window.devicePixelRatio || 1;
const logicalWidth = 3200;
const logicalHeight = 2400;
canvas.width = logicalWidth * dpr;
canvas.height = logicalHeight * dpr;
canvas.style.width = `${logicalWidth}px`;
canvas.style.height = `${logicalHeight}px`;
const worker = new Worker(new URL('./paint.worker.ts', import.meta.url), { type: 'module' });
const offscreen = canvas.transferControlToOffscreen();
const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const isLocal = window.location.hostname === 'localhost' || window.location.hostname.startsWith('192.168.');
const wsHost = isLocal ? `${window.location.hostname}:8000` : window.location.host;
const wsURI = `${wsProtocol}${wsHost}/ws`;

worker.postMessage({
    type: 'INIT',
    canvas: offscreen,
    wsURI: wsURI,
    width: canvas.width,
    height: canvas.height,
    dpr: dpr
}, [offscreen]);

const brushColor = document.getElementById('brushColor') as HTMLInputElement;
const brushColorSpan = document.getElementById('brushColorValue') as HTMLSpanElement;
brushColor.addEventListener('input', (e) => {
    const target = e.target as HTMLInputElement;
    brushColorSpan.textContent = target.value.toUpperCase();
});
const brushSize = document.getElementById('brushSize') as HTMLInputElement;
const brushSizeValue = document.getElementById('brushSizeValue') as HTMLSpanElement;
brushSize.addEventListener('input', (e) => {
    const target = e.target as HTMLInputElement;
    brushSizeValue.textContent = target.value;
});

const paintToggle = document.getElementById('paintToggle') as HTMLInputElement;
const toggleText = document.querySelector('.toggle_text') as HTMLSpanElement;
let isDrawing: boolean = false;
let isPaintMode: boolean = true;
let isScroll: boolean = false;
let startX = 0;
let startY = 0;
let startScrollLeft = 0;
let startScrollTop = 0;

canvas.addEventListener('contextmenu', (e: PointerEvent) => {
    e.preventDefault();
});
paintToggle.addEventListener('click', () => {
    if (isPaintMode === true) {
        isDrawing = false;
        isPaintMode = false;
        toggleText.textContent = '이동 모드';
        canvas.classList.add('is-dragging');
    }
    else if (isPaintMode === false) {
        isPaintMode = true;
        toggleText.textContent = '그리기 모드';
        canvas.classList.remove('is-dragging');
    }
});
canvas.addEventListener('pointerdown', (e: PointerEvent) => {
    if (e.button === 2) return;
    if (isPaintMode === false) {
        isScroll = true;
        startX = e.clientX;
        startY = e.clientY;
        startScrollLeft = canvasContainer.scrollLeft;
        startScrollTop = canvasContainer.scrollTop;
    }
    else if (isPaintMode === true) {
        isDrawing = true;
        worker.postMessage({
            type: 'DRAW_START',
            offsetX: e.offsetX,
            offsetY: e.offsetY,
            color: brushColor.value,
            size: Number(brushSize.value)
        });
    }
});
canvas.addEventListener('pointermove', (e: PointerEvent) => {
    if (isDrawing === true && isPaintMode === true) {
        worker.postMessage({
            type: 'DRAW_MOVE',
            offsetX: e.offsetX,
            offsetY: e.offsetY,
            color: brushColor.value,
            size: Number(brushSize.value)
        });
    }
});
window.addEventListener('pointermove', (e: PointerEvent) => {
    if (isScroll === true) {
        const walkX = e.clientX - startX;
        const walkY = e.clientY - startY;
        canvasContainer.scrollLeft = startScrollLeft - walkX;
        canvasContainer.scrollTop = startScrollTop - walkY;
    }
});
window.addEventListener('pointerup', () => {
    isScroll = false;
    if (isDrawing === true) {
        isDrawing = false;
        worker.postMessage({ type: 'DRAW_END' });
    }
});
