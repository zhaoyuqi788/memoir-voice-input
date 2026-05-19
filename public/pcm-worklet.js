class PcmRecorderProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.sampleDebt = 0;
    this.levelFrames = 0;
    this.levelSum = 0;
  }

  process(inputs) {
    const input = inputs[0]?.[0];
    if (!input) {
      return true;
    }

    const ratio = 16000 / sampleRate;
    const output = [];
    for (let index = 0; index < input.length; index += 1) {
      const sample = input[index] || 0;
      this.sampleDebt += ratio;
      this.levelSum += sample * sample;
      this.levelFrames += 1;
      if (this.sampleDebt >= 1) {
        const clamped = Math.max(-1, Math.min(1, sample));
        output.push(clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff);
        this.sampleDebt -= 1;
      }
    }

    if (output.length > 0) {
      const pcm = new Int16Array(output.length);
      for (let index = 0; index < output.length; index += 1) {
        pcm[index] = output[index];
      }
      const level = Math.sqrt(this.levelSum / Math.max(1, this.levelFrames));
      this.port.postMessage({ type: "audio", buffer: pcm.buffer, level }, [pcm.buffer]);
      this.levelSum = 0;
      this.levelFrames = 0;
    }

    return true;
  }
}

registerProcessor("pcm-recorder", PcmRecorderProcessor);
