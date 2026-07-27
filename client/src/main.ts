import './style.scss';

const canvas = document.getElementById('canvas') as HTMLCanvasElement;
const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;

const brushColor = document.getElementById('brushColor') as HTMLInputElement;
const brushColorSpan = document.getElementById('brushColorValue') as HTMLSpanElement;
brushColor.addEventListener('input', (event) => {
    const target = event.target as HTMLInputElement;
    const selectedColor = target.value;
    brushColorSpan.textContent = selectedColor.toUpperCase();
});

const brushSize = document.getElementById('brushSize') as HTMLInputElement;
const brushSizeValue = document.getElementById('brushSizeValue') as HTMLSpanElement;
brushSize.addEventListener('input', (e) => {
    const target = e.target as HTMLInputElement;
    brushSizeValue.textContent = target.value;
});


const paintToggle = document.getElementById('paintToggle') as HTMLInputElement;
const toggleText = document.querySelector('.toggle_text') as HTMLSpanElement;
const canvasContainer = document.querySelector('.canvas_container') as HTMLDivElement;



let isDrawing: boolean = false;
canvas.width = 3200;
canvas.height = 2400;
ctx.lineCap = 'round';
ctx.lineJoin = 'round';
