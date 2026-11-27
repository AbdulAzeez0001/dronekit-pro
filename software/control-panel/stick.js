// A touch / mouse stick (MIT).
// x and y run -1..1 (y up = +1). Axes with spring snap back to 0 on
// release; an axis without spring stays where it's left (the throttle).

export class Stick {
  constructor(el, { springX = true, springY = true, y = 0, onChange = () => {} } = {}) {
    this.el = el;
    this.knob = el.querySelector('.knob');
    this.springX = springX;
    this.springY = springY;
    this.onChange = onChange;
    this.x = 0;
    this.y = y;
    this.pointer = null;

    el.addEventListener('pointerdown', (e) => {
      if (this.pointer !== null) return;
      this.pointer = e.pointerId;
      try { el.setPointerCapture(e.pointerId); } catch { /* still works without capture */ }
      this._move(e);
    });
    el.addEventListener('pointermove', (e) => {
      if (e.pointerId === this.pointer) this._move(e);
    });
    const end = (e) => {
      if (e.pointerId !== this.pointer) return;
      this.pointer = null;
      this.set(this.springX ? 0 : this.x, this.springY ? 0 : this.y);
    };
    el.addEventListener('pointerup', end);
    el.addEventListener('pointercancel', end);
    new ResizeObserver(() => this._draw()).observe(el);
    this._draw();
  }

  set(x, y) {
    this.x = Math.max(-1, Math.min(1, x));
    this.y = Math.max(-1, Math.min(1, y));
    this._draw();
    this.onChange(this.x, this.y);
  }

  _move(e) {
    const r = this.el.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * 2 - 1;
    const y = -(((e.clientY - r.top) / r.height) * 2 - 1);
    this.set(x, y);
  }

  _draw() {
    const r = this.el.getBoundingClientRect();
    const k = this.knob.getBoundingClientRect();
    const px = ((this.x + 1) / 2) * (r.width - k.width);
    const py = ((1 - this.y) / 2) * (r.height - k.height);
    this.knob.style.transform = `translate(${px}px, ${py}px)`;
  }
}
