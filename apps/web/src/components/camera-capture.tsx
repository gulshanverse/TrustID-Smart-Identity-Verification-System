"use client";

import { useEffect, useRef, useState } from "react";

export function CameraCapture({ onCapture }: { onCapture: (file: File) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<"idle" | "starting" | "ready" | "captured" | "denied" | "unsupported">("idle");
  const [message, setMessage] = useState("");

  useEffect(() => () => streamRef.current?.getTracks().forEach((track) => track.stop()), []);

  const start = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setState("unsupported");
      setMessage("Camera capture is not supported in this browser. Use the upload fallback.");
      return;
    }
    setState("starting");
    setMessage("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setState("ready");
    } catch {
      setState("denied");
      setMessage("Camera permission was not granted. Use the upload fallback instead.");
    }
  };

  const capture = () => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      onCapture(new File([blob], "camera-capture.jpg", { type: "image/jpeg" }));
      setState("captured");
      streamRef.current?.getTracks().forEach((track) => track.stop());
    }, "image/jpeg", 0.92);
  };

  const retake = () => {
    setState("idle");
    setMessage("");
  };

  return <div className="camera-capture" aria-label="Camera capture">
    <div className="console-card-heading"><div><h3>Camera capture</h3><p>Optional browser capture. No device data is stored.</p></div></div>
    {state === "idle" && <button type="button" className="button button-secondary" onClick={() => void start()}>Use camera</button>}
    {(state === "starting" || state === "ready") && <><video ref={videoRef} autoPlay playsInline muted className="camera-preview" /><div className="camera-actions"><button type="button" className="button button-primary" disabled={state !== "ready"} onClick={capture}>Capture</button><button type="button" className="button button-secondary" onClick={retake}>Cancel</button></div></>}
    {state === "captured" && <div className="upload-success" role="status"><strong>Camera capture ready.</strong><span>Review the preview above or retake before upload.</span><button type="button" className="button button-secondary" onClick={retake}>Retake</button></div>}
    {(state === "denied" || state === "unsupported") && <p className="upload-error" role="alert">{message}</p>}
  </div>;
}
