let ctx: OffscreenCanvasRenderingContext2D | null = null;
let ws: WebSocket | null = null;
let lastX = 0;
let lastY = 0;
let workerDpr = 1;

self.onmessage = (e: MessageEvent) => {
    const { type, canvas, wsURI, width, height, offsetX, offsetY, color, size, dpr } = e.data;

    switch (type) {
        case 'INIT':
            canvas.width = width;
            canvas.height = height;
            ctx = canvas.getContext('2d') as OffscreenCanvasRenderingContext2D;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            workerDpr = dpr || 1;
            ctx.scale(workerDpr, workerDpr);
            ws = new WebSocket(wsURI);
            ws.onopen = () => {
                console.log('Worker: WebSocket connection established');
            };
            ws.onmessage = (msgEvent) => {
                if (!ctx) return;
                const rawData = JSON.parse(msgEvent.data);

                ctx.strokeStyle = rawData.color;
                ctx.lineWidth = Number(rawData.size);
                ctx.beginPath();
                ctx.moveTo(rawData.lastX, rawData.lastY);
                ctx.lineTo(rawData.currentX, rawData.currentY);
                ctx.stroke();
            };
            break;

        case 'DRAW_START':
            if (!ctx) return;
            lastX = offsetX;
            lastY = offsetY;
            ctx.strokeStyle = color;
            ctx.lineWidth = size;
            ctx.beginPath();
            ctx.moveTo(lastX, lastY);
            ctx.lineTo(offsetX, offsetY);
            ctx.stroke();

            const startData = {
                lastX: offsetX,
                lastY: offsetY,
                currentX: offsetX,
                currentY: offsetY,
                color: color,
                size: size
            };
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(startData));
            }
            break;

        case 'DRAW_MOVE':
            if (!ctx) return;
            ctx.strokeStyle = color;
            ctx.lineWidth = size;
            ctx.beginPath();
            ctx.moveTo(lastX, lastY);
            ctx.lineTo(offsetX, offsetY);
            ctx.stroke();

            const drawData = {
                lastX: lastX,
                lastY: lastY,
                currentX: offsetX,
                currentY: offsetY,
                color: color,
                size: size
            };
            lastX = offsetX;
            lastY = offsetY;
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(drawData));
            }
            break;

        case 'DRAW_END':
            break;
    }
};
