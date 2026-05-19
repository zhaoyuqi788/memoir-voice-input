import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpenText,
  Check,
  Circle,
  Download,
  FileText,
  Mic,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Save,
  ScissorsLineDashed,
  Square,
  Waves
} from "lucide-react";
import { api, audioUrl, exportUrl, wsBase } from "./lib/api";
import { chapterDuration, formatDuration } from "./lib/format";
import type { Chapter, Health, Segment } from "./types";

type WsMessage =
  | { type: "status"; message: string; recognizerReady: boolean }
  | { type: "partial"; text: string }
  | { type: "segment"; segment: Segment; reason: string };

type RecorderRefs = {
  audioContext?: AudioContext;
  mediaStream?: MediaStream;
  source?: MediaStreamAudioSourceNode;
  node?: AudioWorkletNode;
  mute?: GainNode;
  socket?: WebSocket;
};

const emptyRefs: RecorderRefs = {};

function App() {
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [activeChapterId, setActiveChapterId] = useState<string>("");
  const [health, setHealth] = useState<Health | null>(null);
  const [partial, setPartial] = useState("");
  const [recording, setRecording] = useState(false);
  const [savingSegmentId, setSavingSegmentId] = useState<string>("");
  const [status, setStatus] = useState("准备就绪");
  const [audioLevel, setAudioLevel] = useState(0);
  const [exporting, setExporting] = useState(false);
  const recorderRef = useRef<RecorderRefs>(emptyRefs);

  const activeChapter = useMemo(
    () => chapters.find((chapter) => chapter.id === activeChapterId) ?? chapters[0],
    [activeChapterId, chapters]
  );

  const loadChapters = useCallback(async () => {
    const [nextHealth, nextChapters] = await Promise.all([api.health(), api.chapters()]);
    setHealth(nextHealth);
    setChapters(nextChapters);
    setActiveChapterId((current) => current || nextChapters[0]?.id || "");
    if (!nextHealth.recognizer_ready) {
      setStatus(nextHealth.recognizer_status);
    }
  }, []);

  useEffect(() => {
    void loadChapters();
  }, [loadChapters]);

  const upsertSegment = useCallback((segment: Segment) => {
    setChapters((current) =>
      current.map((chapter) =>
        chapter.id === segment.chapter_id
          ? {
              ...chapter,
              segment_count: chapter.segments.some((item) => item.id === segment.id)
                ? chapter.segment_count
                : chapter.segment_count + 1,
              duration_ms: chapter.segments.some((item) => item.id === segment.id)
                ? chapter.duration_ms
                : chapter.duration_ms + segment.duration_ms,
              segments: chapter.segments.some((item) => item.id === segment.id)
                ? chapter.segments.map((item) => (item.id === segment.id ? segment : item))
                : [...chapter.segments, segment]
            }
          : chapter
      )
    );
  }, []);

  const cleanupRecorder = useCallback(() => {
    const refs = recorderRef.current;
    refs.source?.disconnect();
    refs.node?.disconnect();
    refs.mute?.disconnect();
    refs.mediaStream?.getTracks().forEach((track) => track.stop());
    void refs.audioContext?.close();
    recorderRef.current = {};
    setAudioLevel(0);
  }, []);

  const stopRecording = useCallback(() => {
    const socket = recorderRef.current.socket;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "stop" }));
      window.setTimeout(() => socket.close(), 650);
    }
    cleanupRecorder();
    setRecording(false);
  }, [cleanupRecorder]);

  useEffect(() => () => stopRecording(), [stopRecording]);

  const createChapter = async () => {
    const title = `第 ${chapters.length + 1} 章`;
    const chapter = await api.createChapter(title);
    setChapters((current) => [...current, chapter]);
    setActiveChapterId(chapter.id);
  };

  const renameActiveChapter = async (title: string) => {
    if (!activeChapter || title.trim() === activeChapter.title) {
      return;
    }
    const updated = await api.updateChapter(activeChapter.id, { title: title.trim() });
    setChapters((current) => current.map((chapter) => (chapter.id === updated.id ? { ...chapter, ...updated } : chapter)));
  };

  const startRecording = async () => {
    if (!activeChapter || recording) {
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        channelCount: 1
      }
    });
    const audioContext = new AudioContext();
    await audioContext.audioWorklet.addModule("/pcm-worklet.js");

    const socket = new WebSocket(`${wsBase}/ws/asr`);
    socket.binaryType = "arraybuffer";
    socket.onopen = () => {
      socket.send(JSON.stringify({ type: "start", chapterId: activeChapter.id }));
      setStatus("正在收音");
    };
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as WsMessage;
      if (payload.type === "status") {
        setStatus(payload.message);
      }
      if (payload.type === "partial") {
        setPartial(payload.text);
      }
      if (payload.type === "segment") {
        upsertSegment(payload.segment);
        setPartial("");
      }
    };
    socket.onerror = () => setStatus("连接本地识别服务失败");
    socket.onclose = () => {
      setRecording(false);
      setStatus((current) => (current === "正在收音" ? "已暂停" : current));
    };

    const source = audioContext.createMediaStreamSource(stream);
    const node = new AudioWorkletNode(audioContext, "pcm-recorder");
    const mute = audioContext.createGain();
    mute.gain.value = 0;
    node.port.onmessage = (event: MessageEvent<{ type: string; buffer: ArrayBuffer; level: number }>) => {
      setAudioLevel(event.data.level);
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(event.data.buffer);
      }
    };
    source.connect(node);
    node.connect(mute);
    mute.connect(audioContext.destination);
    recorderRef.current = { audioContext, mediaStream: stream, source, node, mute, socket };
    setPartial("");
    setRecording(true);
  };

  const commitCurrentSegment = () => {
    const socket = recorderRef.current.socket;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "commit" }));
    }
  };

  const playSegment = (segmentId: string) => {
    const audio = document.getElementById(`audio-${segmentId}`) as HTMLAudioElement | null;
    if (audio) {
      void audio.play();
    }
  };

  const saveSegment = async (segment: Segment, patch: Partial<Pick<Segment, "raw_text" | "cleaned_text">>) => {
    setSavingSegmentId(segment.id);
    try {
      const updated = await api.updateSegment(segment.id, patch);
      upsertSegment(updated);
    } finally {
      setSavingSegmentId("");
    }
  };

  const completeChapter = async () => {
    if (!activeChapter) {
      return;
    }
    setExporting(true);
    try {
      const result = await api.completeChapter(activeChapter.id);
      window.open(exportUrl(result.download_url), "_blank", "noopener,noreferrer");
      await loadChapters();
    } finally {
      setExporting(false);
    }
  };

  return (
    <main className="appShell">
      <aside className="chapterRail" aria-label="章节">
        <div className="railHeader">
          <div>
            <p>章节</p>
            <h1>回忆录</h1>
          </div>
          <button className="iconButton" type="button" onClick={createChapter} aria-label="新建章节">
            <Plus size={18} />
          </button>
        </div>

        <div className="chapterList">
          {chapters.map((chapter) => (
            <button
              type="button"
              className={`chapterItem ${chapter.id === activeChapter?.id ? "active" : ""}`}
              key={chapter.id}
              onClick={() => setActiveChapterId(chapter.id)}
            >
              <span className="chapterIcon">
                <BookOpenText size={18} />
              </span>
              <span>
                <strong>{chapter.title}</strong>
                <small>
                  {chapter.segment_count} 段 · {chapterDuration(chapter)}
                </small>
              </span>
              {chapter.status === "completed" ? <Check size={16} /> : null}
            </button>
          ))}
        </div>

        <div className="localNotice">
          <Circle size={10} fill={health?.recognizer_ready ? "#237b5a" : "#b98218"} />
          <span>{health?.recognizer_ready ? "本地模型已就绪" : "本地模型未加载"}</span>
        </div>
      </aside>

      <section className="workspace">
        <header className="topBar">
          <div className="titleBlock">
            <input
              aria-label="章节标题"
              className="chapterTitleInput"
              defaultValue={activeChapter?.title ?? ""}
              key={activeChapter?.id ?? "empty"}
              onBlur={(event) => void renameActiveChapter(event.currentTarget.value)}
            />
            <p>{status}</p>
          </div>
          <div className="toolbar">
            <button className="secondaryButton" type="button" onClick={() => void loadChapters()}>
              <RefreshCw size={16} />
              刷新
            </button>
            <button className="secondaryButton" type="button" onClick={commitCurrentSegment} disabled={!recording}>
              <ScissorsLineDashed size={16} />
              新段落
            </button>
            {recording ? (
              <button className="recordButton active" type="button" onClick={stopRecording}>
                <Square size={17} fill="currentColor" />
                暂停
              </button>
            ) : (
              <button className="recordButton" type="button" onClick={() => void startRecording()} disabled={!activeChapter}>
                <Mic size={17} />
                开始录音
              </button>
            )}
            <button className="exportButton" type="button" onClick={() => void completeChapter()} disabled={!activeChapter || exporting}>
              <Download size={16} />
              {exporting ? "导出中" : "完成并导出"}
            </button>
          </div>
        </header>

        <section className="livePanel" aria-label="实时识别">
          <div className="liveHeader">
            <div>
              <span className={`recordDot ${recording ? "on" : ""}`} />
              <strong>实时识别</strong>
            </div>
            <div className="meter" aria-label="收音强度">
              {Array.from({ length: 16 }).map((_, index) => (
                <span
                  key={index}
                  style={{
                    transform: `scaleY(${Math.max(0.18, Math.min(1, audioLevel * 8 - index * 0.025))})`
                  }}
                />
              ))}
            </div>
          </div>
          <div className="partialText">
            {partial || (recording ? "正在等待说话..." : "点击开始录音后，这里会像输入法一样显示实时转写。")}
          </div>
        </section>

        <section className="contentGrid">
          <section className="segmentsPanel" aria-label="段落">
            <div className="sectionHeading">
              <div>
                <h2>段落</h2>
                <p>自动按停顿分段，每段可播放和修订。</p>
              </div>
              <Waves size={20} />
            </div>

            <div className="segmentList">
              {activeChapter?.segments.length ? (
                activeChapter.segments.map((segment) => (
                  <article className="segmentCard" key={segment.id}>
                    <div className="segmentMeta">
                      <span>第 {segment.position} 段</span>
                      <span>{formatDuration(segment.duration_ms)}</span>
                      {savingSegmentId === segment.id ? <span>保存中</span> : null}
                    </div>
                    <div className="audioRow">
                      <button
                        className="playButton"
                        type="button"
                        aria-label={`播放第 ${segment.position} 段`}
                        onClick={() => playSegment(segment.id)}
                      >
                        <Play size={16} fill="currentColor" />
                      </button>
                      <audio id={`audio-${segment.id}`} controls preload="none" src={audioUrl(segment.id)} />
                    </div>
                    <label>
                      <span>
                        <FileText size={15} />
                        原始转写
                      </span>
                      <textarea
                        defaultValue={segment.raw_text}
                        rows={3}
                        onBlur={(event) => void saveSegment(segment, { raw_text: event.currentTarget.value })}
                      />
                    </label>
                    <label>
                      <span>
                        <Save size={15} />
                        整理后
                      </span>
                      <textarea
                        defaultValue={segment.cleaned_text}
                        rows={4}
                        onBlur={(event) => void saveSegment(segment, { cleaned_text: event.currentTarget.value })}
                      />
                    </label>
                  </article>
                ))
              ) : (
                <div className="emptyState">
                  <Pause size={28} />
                  <strong>还没有段落</strong>
                  <p>开始录音后，停顿会自动生成可播放的段落。</p>
                </div>
              )}
            </div>
          </section>

          <aside className="editorPanel" aria-label="整理后文本">
            <div className="sectionHeading">
              <div>
                <h2>整理稿</h2>
                <p>章节完成前可以逐段修订。</p>
              </div>
            </div>
            <div className="cleanPreview">
              {activeChapter?.segments.length ? (
                activeChapter.segments.map((segment) => <p key={segment.id}>{segment.cleaned_text || segment.raw_text}</p>)
              ) : (
                <p>整理后的文本会汇总在这里，适合之后继续改成书稿。</p>
              )}
            </div>
          </aside>
        </section>
      </section>
    </main>
  );
}

export default App;
