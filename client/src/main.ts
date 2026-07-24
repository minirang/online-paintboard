import './style.scss';
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
