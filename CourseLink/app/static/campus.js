// Hand-drawn elevation composed of repeated architectural elements.
const canvas = document.querySelector('#campus');
function drawHall() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = w*dpr; canvas.height = h*dpr;
  const ctx = canvas.getContext('2d');
  const scale = Math.min(w/750,h/285);
  ctx.scale(dpr,dpr); ctx.translate((w-750*scale)/2,h-277*scale); ctx.scale(scale,scale);
  ctx.strokeStyle = '#9bbd9f'; ctx.lineWidth = 1.25;
  function line(points) {
    ctx.beginPath(); points.forEach(([x,y],i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y)); ctx.stroke();
  }
  function box(x,y,width,height) {ctx.strokeRect(x,y,width,height);}
  function arch(x,y,width,height) {
    ctx.beginPath(); ctx.moveTo(x,y+height); ctx.lineTo(x,y+width/2);
    ctx.arc(x+width/2,y+width/2,width/2,Math.PI,2*Math.PI);
    ctx.lineTo(x+width,y+height); ctx.stroke();
    line([[x+width/2,y+2],[x+width/2,y+height]]);
    line([[x,y+width/2],[x+width,y+width/2]]);
  }
  for (const x of [32,453]) {
    box(x,139,265,107); box(x-4,132,273,7); box(x,185,265,5);
    line([[x-4,132],[x+16,110],[x+250,110],[x+269,132]]);
    for(let i=0;i<9;i++){arch(x+9+i*28,151,17,29);arch(x+9+i*28,200,17,40);}
  }
  ctx.fillStyle='#174d3c';ctx.fillRect(285,92,180,155);
  box(285,99,180,147);box(278,92,194,8);
  line([[275,92],[375,51],[475,92],[275,92]]);line([[291,87],[375,57],[459,87],[291,87]]);
  for(let i=0;i<6;i++){const x=293+i*30;box(x,104,11,129);box(x-3,101,17,5);box(x-3,233,17,6);}
  for(let i=0;i<3;i++)arch(315+i*49,160,20,73);
  box(350,23,50,36);line([[344,23],[375,3],[406,23],[344,23]]);
  ctx.beginPath();ctx.arc(375,39,10,0,Math.PI*2);ctx.stroke();line([[375,31],[375,39],[381,42]]);
  for(let i=0;i<4;i++)box(277-i*5,240+i*4,196+i*10,4);
  line([[3,247],[275,247]]);line([[477,247],[746,247]]);line([[18,259],[733,259]]);
}
new ResizeObserver(drawHall).observe(canvas);
