import React, { useRef, useEffect, useState } from "react";
import { startTrip, endTrip, postEvent } from "./api";
import "./Futuristic.css";
const EYE_THRESHOLD = 0.012;
const SLEEP_FRAMES = 10;
const ALARM_FRAMES = 60;

export default function App() {

  const videoRef = useRef(null);
  const faceMeshRef = useRef(null);
  const cameraRef = useRef(null);
  
  const eyeClosedFrames = useRef(0);
  const alarmRef = useRef(null);
  const tripIdRef = useRef(null);
  const alarmSentRef = useRef(false);   // taaki drowsy event 1000 baar na jaye
  const [monitoring, setMonitoring] = useState(false);

  const [sleeping, setSleeping] = useState(false);
  const [alarmOn, setAlarmOn] = useState(false);
  const [pipOn, setPipOn] = useState(false);

  /* ---------- PIP ---------- */
  const togglePiP = async () => {
    try {
      if (!document.pictureInPictureElement) {
        await videoRef.current.requestPictureInPicture();
        setPipOn(true);
      } else {
        await document.exitPictureInPicture();
        setPipOn(false);
      }
    } catch {}
  };

  const startMonitoring = async () => {
  // trip start
  const t = await startTrip("driver_01");
  tripIdRef.current = t.trip_id;
  alarmSentRef.current = false;

  // camera start (existing cameraRef use karo)
  if (cameraRef.current) {
    try { cameraRef.current.start(); } catch {}
  }

  setMonitoring(true);
  await postEvent(tripIdRef.current, "camera_started");
};

const stopMonitoring = async () => {
  // camera stop
  if (cameraRef.current) {
    try { cameraRef.current.stop(); } catch {}
  }

  setMonitoring(false);

  if (tripIdRef.current) {
    await postEvent(tripIdRef.current, "camera_stopped");
    await endTrip(tripIdRef.current);
    tripIdRef.current = null;
  }

  // alarm reset
  setAlarmOn(false);
  setSleeping(false);
  eyeClosedFrames.current = 0;
  alarmSentRef.current = false;
  if (alarmRef.current) alarmRef.current.pause();
};

  /* ---------- LOAD MEDIAPIPE ---------- */
  useEffect(() => {

    const load = async () => {
      const scripts = [
        "https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js",
        "https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"
      ];

      for (let s of scripts) {
        if (!document.querySelector(`script[src="${s}"]`)) {
          await new Promise(res => {
            const el = document.createElement("script");
            el.src = s;
            el.onload = res;
            document.head.appendChild(el);
          });
        }
      }

      init();
    };

    const init = () => {
      if (!window.FaceMesh || !window.Camera || !videoRef.current) return;

      const mesh = new window.FaceMesh({
        locateFile: f => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${f}`,
      });

      mesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.6,
        minTrackingConfidence: 0.6,
      });

      mesh.onResults(res => {
        if (!res.multiFaceLandmarks?.length) return;

        const lm = res.multiFaceLandmarks[0];
        if (!lm[159] || !lm[145]) return;

        const open = (lm[145].y - lm[159].y) > EYE_THRESHOLD;

        if (!open) eyeClosedFrames.current++;
        else {
          eyeClosedFrames.current = 0;
          setSleeping(false);
          setAlarmOn(false);
          if (alarmRef.current) alarmRef.current.pause();
          return;
        }

        if (eyeClosedFrames.current > SLEEP_FRAMES) setSleeping(true);

        if (eyeClosedFrames.current > ALARM_FRAMES && !alarmOn) {
          if (!alarmRef.current)
            alarmRef.current = new Audio("https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg");

          alarmRef.current.play().catch(()=>{});
          setAlarmOn(true);
          if (tripIdRef.current && !alarmSentRef.current) {
            alarmSentRef.current = true;
            postEvent(tripIdRef.current, "drowsy_alert", {
              closed_frames: eyeClosedFrames.current
            });
          }
        }
      });

      faceMeshRef.current = mesh;

      const cam = new window.Camera(videoRef.current, {
        onFrame: async () => await mesh.send({ image: videoRef.current }),
        width: 640,
        height: 480,
      });

      //cam.start();
      cameraRef.current = cam;
    };

    load();

    return () => cameraRef.current && cameraRef.current.stop();
  }, []);

  return (
    <div className="cyber-bg">

      <div style={hero}>
        <h1 className="hero-title">
         DriveSafe-<span>AI</span>
        </h1>
        <p>Cyber Vision For Driver Safety</p>
      </div>

      <div className="cyber-card" style={{
        ...cameraCard,
        boxShadow: sleeping
          ? "0 0 60px #ff2d2d"
          : "0 0 40px #22ffb1"
      }}>
        <div className="hud-line"></div>
        <video ref={videoRef} autoPlay muted playsInline style={video}/>
      </div>

      <div style={status(sleeping)}>
        {sleeping ? "DROWSINESS DETECTED" : "SYSTEM ACTIVE"}
      </div>

      <div style={{display:"flex",gap:16}}>
        {!monitoring ? (
          <button className="cyber-btn" onClick={startMonitoring}>START MONITORING</button>
        ) : (
          <button className="cyber-btn" onClick={stopMonitoring}>STOP MONITORING</button>
        )}

        <button className="cyber-btn" onClick={togglePiP}>
          {pipOn ? "EXIT FLOAT" : "FLOAT MODE"}
        </button>
      </div>

      {alarmOn && (
        <div className="alert-overlay">
          ⚠ WAKE UP DRIVER ⚠
        </div>
      )}

    </div>
  );
}

/* ---------- CYBER STYLES ---------- */

const app = {
  minHeight:"100vh",
  background:"radial-gradient(circle at top,#071420,#02040f)",
  color:"white",
  display:"flex",
  flexDirection:"column",
  alignItems:"center",
  justifyContent:"center",
  gap:22,
  textAlign:"center",
  fontFamily:"system-ui"
};

const hero = {
  marginBottom:12
};

const cameraCard = {
  width:"70%",
  maxWidth:800,
  padding:12,
  borderRadius:28,
  background:"rgba(10,20,40,.6)",
  backdropFilter:"blur(12px)",
  border:"1px solid rgba(255,255,255,.1)",
  transition:"0.4s"
};

const video = {
  width:"100%",
  borderRadius:20
};

const status = sleeping => ({
  padding:"10px 26px",
  borderRadius:20,
  fontWeight:"bold",
  color: sleeping ? "#ff4d4d" : "#22ffb1",
  background:"rgba(0,0,0,.5)",
  letterSpacing:1
});

const btn = {
  padding:"12px 26px",
  borderRadius:14,
  background:"#22ffb1",
  color:"#001",
  fontWeight:"bold",
  border:"none",
  cursor:"pointer",
  boxShadow:"0 0 25px #22ffb1"
};

const alertOverlay = {
  position:"fixed",
  inset:0,
  background:"rgba(255,0,0,.25)",
  display:"flex",
  alignItems:"center",
  justifyContent:"center",
  fontSize:48,
  fontWeight:"900",
  color:"#fff",
  animation:"pulse 1s infinite"
};