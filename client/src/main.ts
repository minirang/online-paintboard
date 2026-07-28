import './style.scss';

const canvas = document.getElementById('canvas') as HTMLCanvasElement;
const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;

const brushColor = document.getElementById('brushColor') as HTMLInputElement;
const brushColorSpan = document.getElementById('brushColorValue') as HTMLSpanElement;
brushColor.addEventListener('input', (e) => {
    const target = e.target as HTMLInputElement;
    const selectedColor = target.value;
    brushColorSpan.textContent = selectedColor.toUpperCase();
});
const brushSize = document.getElementById('brushSize') as HTMLInputElement;
const brushSizeValue = document.getElementById('brushSizeValue') as HTMLSpanElement;
brushSize.addEventListener('input', (e) => {
    const target = e.target as HTMLInputElement;
    const selectedSize = target.value;
    brushSizeValue.textContent = selectedSize;
});

const paintToggle = document.getElementById('paintToggle') as HTMLInputElement;
const toggleText = document.querySelector('.toggle_text') as HTMLSpanElement;
const canvasContainer = document.querySelector('.canvas_container') as HTMLDivElement;
let isDrawing: boolean = false;
let isPaintMode: boolean = true;
let isScroll: boolean = false;
let startX = 0;
let startY = 0;
let startScrollLeft = 0;
let startScrollTop = 0;
let lastX = 0;
let lastY = 0;
canvas.width = 3200;
canvas.height = 2400;
ctx.lineCap = 'round';
ctx.lineJoin = 'round';

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
        lastX = e.offsetX;
        lastY = e.offsetY;
        ctx.strokeStyle = brushColor.value;
        ctx.lineWidth = Number(brushSize.value);
        ctx.beginPath();
        ctx.moveTo(lastX, lastY);
        ctx.lineTo(e.offsetX, e.offsetY);
        ctx.stroke();
    }
});
canvas.addEventListener('pointermove', (e: PointerEvent) => {
    if (isDrawing === true && isPaintMode === true) {
        ctx.strokeStyle = brushColor.value;
        ctx.lineWidth = Number(brushSize.value);
        ctx.beginPath();
        ctx.moveTo(lastX, lastY);
        ctx.lineTo(e.offsetX, e.offsetY);
        ctx.stroke();
        lastX = e.offsetX;
        lastY = e.offsetY;
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
    isDrawing = false;
});
