// Microphone -> mono PCM16 at the requested rate (16 kHz for our streaming, 24 kHz for the Voice Agent), 50 ms
// frames. Linear resampling is enough for speech.
class PCM16Downsampler extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const rate = (options && options.processorOptions && options.processorOptions.rate) || 16000;
    this.ratio = sampleRate / rate;
    this.pos = 0;
    this.out = new Int16Array(Math.round(rate / 20)); // 50 ms
    this.n = 0;
  }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    while (this.pos < ch.length) {
      const i = Math.floor(this.pos), f = this.pos - i;
      const s = ch[i] + ((ch[Math.min(i + 1, ch.length - 1)] - ch[i]) * f);
      this.out[this.n++] = Math.max(-1, Math.min(1, s)) * 0x7fff;
      if (this.n === this.out.length) {
        this.port.postMessage(this.out.buffer.slice(0));
        this.n = 0;
      }
      this.pos += this.ratio;
    }
    this.pos -= ch.length;
    return true;
  }
}
registerProcessor("pcm16-downsampler", PCM16Downsampler);
