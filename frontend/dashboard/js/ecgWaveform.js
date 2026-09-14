/**
 * SmartPatientCare - ECG Waveform Oscilloscope Renderer
 * Author: Gauri (Frontend & CV Lead)
 * 
 * Renders a real-time hospital-grade ECG oscilloscope waveform (Lead II P-Q-R-S-T)
 * onto an HTML5 Canvas with smooth sweeping beam and phosphor glow.
 */

class EcgWaveform {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    
    this.heartRate = 75; // Default BPM
    this.isRunning = false;
    this.animationFrameId = null;

    // Canvas buffer & sweep position
    this.sweepX = 0;
    this.sweepWidth = 14; // Erase gap ahead of beam
    this.points = [];
    
    // Waveform phase tracking
    this.phase = 0; // 0.0 to 1.0 per cardiac cycle
    this.lastTimestamp = performance.now();

    this._initCanvas();
    window.addEventListener('resize', () => this.handleResize());
  }

  _initCanvas() {
    this.handleResize();
  }

  handleResize() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    this.width = rect.width || 600;
    this.height = rect.height || 180;

    this.canvas.width = this.width * dpr;
    this.canvas.height = this.height * dpr;
    this.canvas.style.width = `${this.width}px`;
    this.canvas.style.height = `${this.height}px`;

    this.ctx.scale(dpr, dpr);
    this.points = new Array(Math.floor(this.width)).fill(this.height / 2);
    this._drawGrid();
  }

  setHeartRate(bpm) {
    if (typeof bpm === 'number' && bpm > 0) {
      this.heartRate = Math.min(220, Math.max(30, bpm));
    }
  }

  /**
   * Generates mathematical P-Q-R-S-T deflection for a given normalized phase [0..1]
   */
  _getEcgSample(p) {
    // Lead II standard morphology
    let v = 0;

    // P-wave (Atrial depolarization): ~0.15 - 0.25
    if (p >= 0.12 && p <= 0.22) {
      const pPhase = (p - 0.12) / 0.10;
      v += 0.18 * Math.sin(pPhase * Math.PI);
    }
    // PR segment baseline: 0.22 - 0.32

    // QRS Complex (Ventricular depolarization): ~0.32 - 0.40
    // Q-wave (small negative dip)
    else if (p >= 0.32 && p < 0.34) {
      const qPhase = (p - 0.32) / 0.02;
      v -= 0.15 * Math.sin(qPhase * Math.PI);
    }
    // R-wave (sharp tall spike)
    else if (p >= 0.34 && p < 0.38) {
      const rPhase = (p - 0.34) / 0.04;
      v += 1.00 * Math.sin(rPhase * Math.PI);
    }
    // S-wave (negative plunge)
    else if (p >= 0.38 && p < 0.41) {
      const sPhase = (p - 0.38) / 0.03;
      v -= 0.32 * Math.sin(sPhase * Math.PI);
    }
    // ST segment baseline: 0.41 - 0.50

    // T-wave (Ventricular repolarization): ~0.50 - 0.68
    else if (p >= 0.50 && p <= 0.68) {
      const tPhase = (p - 0.50) / 0.18;
      v += 0.28 * Math.sin(tPhase * Math.PI);
    }

    // Small subtle physiological baseline noise
    v += (Math.random() - 0.5) * 0.02;

    return v;
  }

  _drawGrid() {
    const ctx = this.ctx;
    ctx.fillStyle = '#06131c';
    ctx.fillRect(0, 0, this.width, this.height);

    // Minor grid lines
    ctx.lineWidth = 0.5;
    ctx.strokeStyle = 'rgba(0, 180, 160, 0.08)';

    const gridSize = 20;
    ctx.beginPath();
    for (let x = 0; x < this.width; x += gridSize) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.height);
    }
    for (let y = 0; y < this.height; y += gridSize) {
      ctx.moveTo(0, y);
      ctx.lineTo(this.width, y);
    }
    ctx.stroke();

    // Major grid lines
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(0, 180, 160, 0.16)';
    ctx.beginPath();
    for (let x = 0; x < this.width; x += gridSize * 5) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.height);
    }
    for (let y = 0; y < this.height; y += gridSize * 5) {
      ctx.moveTo(0, y);
      ctx.lineTo(this.width, y);
    }
    ctx.stroke();
  }

  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    this.lastTimestamp = performance.now();
    this._render();
  }

  stop() {
    this.isRunning = false;
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  _render() {
    if (!this.isRunning) return;

    const now = performance.now();
    const dt = (now - this.lastTimestamp) / 1000;
    this.lastTimestamp = now;

    // Advance cardiac cycle phase according to BPM
    // Frequency (Hz) = BPM / 60
    const freq = this.heartRate / 60;
    this.phase = (this.phase + dt * freq) % 1.0;

    // Speed of oscilloscope sweep across the screen
    const sweepSpeed = 160; // pixels per second
    const dx = sweepSpeed * dt;
    const prevSweepX = this.sweepX;
    this.sweepX = (this.sweepX + dx) % this.width;

    // Baseline amplitude scaling
    const centerY = this.height * 0.52;
    const amplitude = this.height * 0.38;
    const sampleY = centerY - this._getEcgSample(this.phase) * amplitude;

    // Record sample in buffer
    const currIndex = Math.floor(this.sweepX);
    this.points[currIndex] = sampleY;

    // Clear sweep area (erase head ahead of the beam)
    const ctx = this.ctx;
    ctx.save();

    // Erase a narrow strip ahead of sweep beam with background
    const eraseX = (this.sweepX + 2) % this.width;
    ctx.fillStyle = '#06131c';
    ctx.fillRect(eraseX, 0, this.sweepWidth, this.height);

    // Re-render faint grid in the erased strip
    ctx.lineWidth = 0.5;
    ctx.strokeStyle = 'rgba(0, 180, 160, 0.08)';
    const gridSize = 20;
    ctx.beginPath();
    const startGridX = Math.floor(eraseX / gridSize) * gridSize;
    for (let x = startGridX; x <= eraseX + this.sweepWidth; x += gridSize) {
      if (x >= eraseX && x <= eraseX + this.sweepWidth) {
        ctx.moveTo(x, 0);
        ctx.lineTo(x, this.height);
      }
    }
    for (let y = 0; y < this.height; y += gridSize) {
      ctx.moveTo(eraseX, y);
      ctx.lineTo(eraseX + this.sweepWidth, y);
    }
    ctx.stroke();

    // Draw the green phosphor ECG trace
    ctx.shadowBlur = 8;
    ctx.shadowColor = '#00ff88';
    ctx.strokeStyle = '#00ff88';
    ctx.lineWidth = 2.2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    ctx.beginPath();
    const stepX = Math.max(1, Math.floor(dx));
    const startX = Math.max(0, Math.floor(prevSweepX));
    const endX = Math.min(this.width - 1, Math.floor(this.sweepX));

    if (endX >= startX) {
      ctx.moveTo(startX, this.points[startX] || centerY);
      for (let x = startX; x <= endX; x++) {
        ctx.lineTo(x, this.points[x] || centerY);
      }
      ctx.stroke();
    }

    // Glowing beam cursor
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#ffffff';
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.arc(this.sweepX, sampleY, 2.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();

    this.animationFrameId = requestAnimationFrame(() => this._render());
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = EcgWaveform;
}
